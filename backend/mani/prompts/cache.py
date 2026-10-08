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
from mani.prompts.calls import CALL_PROMPTS
from mani.prompts.checks import REQUIRED_PROMPTS, parse_reply_shapes
from mani.prompts.replies import Replies, parse_replies
from mani.prompts.tuning import Tuning, parse_tuning

logger = logging.getLogger(__name__)

# Used by particular paths rather than every turn, but still misconfiguration if absent: every
# model call's own row, and the title layer.
EXPECTED_PROMPTS = tuple(
    dict.fromkeys(REQUIRED_PROMPTS + ("title_generation",) + tuple(sorted(CALL_PROMPTS)))
)


def _reply_shapes(content: str) -> frozenset[str]:
    """The shapes, or none when the row is broken: every shape is then dropped and turns still run.

    The portal skips the seed's check, so a bad edit is logged here rather than failing turns.
    """
    try:
        return parse_reply_shapes(content)
    except ValueError as exc:
        logger.error("reply shapes unreadable, every shape will be dropped: %s", exc)
        return frozenset()


def _parsed(by_name: dict[str, Prompt], name: str, parse):
    """A required row parsed, or CONFIG_ERROR: a broken row fails the turn the way a missing one
    does, and is never taken for a transient failure that keeps the previous snapshot."""
    try:
        return parse(by_name[name].content)
    except ValueError as problem:
        raise ServiceError(
            f"prompt {name!r} is unusable: {problem}",
            ErrorCategory.CONFIG_ERROR,
            user_message="Mani is not available right now.",
        ) from problem


@dataclass(frozen=True)
class Config:
    """An immutable snapshot of everything configurable a turn reads."""

    prompts: dict[str, Prompt]
    registry: Registry
    loaded_at: float
    # What the code sends without the model and the numbers it counts by: required rows,
    # parsed once per load, with no default here.
    replies: Replies
    tuning: Tuning
    # The shapes a reply may report, parsed once per load from the mani_base row.
    reply_shapes: frozenset[str] = frozenset()

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
        prompts=by_name,
        registry=Registry(frameworks),
        loaded_at=time.monotonic(),
        replies=_parsed(by_name, "replies", parse_replies),
        tuning=_parsed(by_name, "tuning", parse_tuning),
        reply_shapes=_reply_shapes(by_name["mani_base"].content),
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
