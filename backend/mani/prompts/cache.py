# ABOUTME: Holds the prompts and framework registry in memory behind a TTL.
# ABOUTME: A missing required prompt is refused at load, not discovered mid-conversation.

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

from mani.chat.techniques import Registry
from mani.config import get_settings
from mani.db import config_tables, pool
from mani.errors import ErrorCategory, ServiceError
from mani.models.rows import Prompt

logger = logging.getLogger(__name__)

# The layers a turn cannot be composed without. The implementation this replaces pushed
# each layer only `if (prompt)`, so a prompt renamed or deactivated in the portal simply
# vanished from the system prompt and Mani quietly changed personality.
REQUIRED_PROMPTS = ("mani_base", "framework_index", "post_framework", "response_format")

# Used by particular paths rather than every turn, but still misconfiguration if absent.
EXPECTED_PROMPTS = REQUIRED_PROMPTS + ("title_generation", "summarization")


@dataclass(frozen=True)
class Config:
    """An immutable snapshot of everything configurable a turn reads."""

    prompts: dict[str, Prompt]
    registry: Registry
    loaded_at: float

    def prompt(self, name: str) -> Prompt | None:
        return self.prompts.get(name)

    def require(self, name: str) -> Prompt:
        found = self.prompts.get(name)
        if found is None:
            raise ServiceError(
                f"prompt {name!r} is missing or inactive",
                ErrorCategory.CONFIG_ERROR,
                user_message="Mani is not available right now.",
            )
        return found


_config: Config | None = None
# One loader at a time, so a cold start under load does not fan out into N identical
# reads of the same three tables.
_lock = asyncio.Lock()


async def _read() -> Config:
    async with pool.as_admin() as conn:
        prompts = await config_tables.list_active_prompts(conn)
        frameworks = await config_tables.list_active_frameworks(conn)

    by_name = {p.name: p for p in prompts}
    missing = [name for name in REQUIRED_PROMPTS if name not in by_name]
    if missing:
        raise ServiceError(
            f"required prompts are missing or inactive: {', '.join(missing)}",
            ErrorCategory.CONFIG_ERROR,
            user_message="Mani is not available right now.",
        )
    absent = [name for name in EXPECTED_PROMPTS if name not in by_name]
    if absent:
        logger.warning("prompts missing or inactive: %s", ", ".join(absent))
    if not frameworks:
        logger.warning("no active frameworks; technique offers will be refused")

    return Config(
        prompts=by_name, registry=Registry(frameworks), loaded_at=time.monotonic()
    )


def _stale(config: Config) -> bool:
    return time.monotonic() - config.loaded_at > get_settings().prompt_cache_ttl


async def load() -> Config:
    """The current configuration, reloading it when the TTL has passed.

    Reloads synchronously when stale rather than serving a stale snapshot and refreshing
    in the background, so an edit in the portal takes effect on the next turn instead of
    the one after it.
    """
    global _config
    if _config is not None and not _stale(_config):
        return _config

    async with _lock:
        if _config is not None and not _stale(_config):
            return _config
        try:
            _config = await _read()
        except ServiceError:
            raise
        except Exception:
            if _config is None:
                raise
            # A transient database failure should not take the chat down when a usable
            # snapshot is already in hand.
            logger.exception("prompt reload failed; keeping the previous snapshot")
        return _config


def invalidate() -> None:
    """Drop the snapshot so the next turn reads fresh.

    Called by the admin endpoints after an edit. Previously the only way to see a change
    was to wait out the TTL.
    """
    global _config
    _config = None
