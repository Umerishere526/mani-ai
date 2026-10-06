# ABOUTME: Turns text into vectors through OpenRouter, cached per message, swappable in tests.
# ABOUTME: A failure here costs routing, never the turn: the caller falls back to no match.

from __future__ import annotations

import hashlib
import logging
import math
from functools import lru_cache
from typing import Protocol

from openai import OpenAI

from mani.config import Settings, get_settings

logger = logging.getLogger(__name__)

# Small, cheap and good enough: one batch of six framework exemplar sets cost 82 tokens.
# Changing this invalidates content/framework_vectors.json, which is why the model name is
# stored in that file and checked on load.
DEFAULT_MODEL = "openai/text-embedding-3-small"
DIMENSIONS = 1536


class Embedder(Protocol):
    """What routing needs. Tests substitute a recorded one, so no network and no flake."""

    def __call__(self, texts: list[str]) -> list[list[float]]: ...


def _key(text: str) -> str:
    return hashlib.sha256(" ".join(text.lower().split()).encode()).hexdigest()


class OpenRouterEmbedder:
    """The real one. One HTTP request per batch, on the same key and base url as chat."""

    def __init__(self, settings: Settings | None = None, model: str = DEFAULT_MODEL) -> None:
        self._settings = settings or get_settings()
        self._model = model
        self._client: OpenAI | None = None

    def __call__(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self._settings.openrouter_api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set")
        if self._client is None:
            self._client = OpenAI(
                api_key=self._settings.openrouter_api_key,
                base_url=self._settings.openrouter_base_url,
            )
        response = self._client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in response.data]


# The one the application uses. Tests and scripts replace it rather than monkeypatching a
# module function, so the substitution is visible at the call site that made it.
_embedder: Embedder | None = None


def set_embedder(embedder: Embedder | None) -> None:
    """Install the embedder routing uses. None restores the real one."""
    global _embedder
    _embedder = embedder
    cached.cache_clear()


def embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = OpenRouterEmbedder()
    return _embedder


@lru_cache(maxsize=4096)
def _cached_one(key: str, text: str) -> tuple[float, ...]:
    return tuple(embedder()([text])[0])


def cached(texts: list[str]) -> list[list[float]]:
    """Embed each text once per process. A person's message never changes, and coverage
    scoring reads every message of the conversation on every turn, so without this the
    same sentences would be re-embedded on each turn of a long chat."""
    return [list(_cached_one(_key(t), t)) for t in texts]


cached.cache_clear = _cached_one.cache_clear  # type: ignore[attr-defined]


def cosine(a: list[float] | tuple[float, ...], b: list[float] | tuple[float, ...]) -> float:
    """Cosine similarity. Returns 0.0 rather than raising when either side has no magnitude."""
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if not na or not nb:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / (na * nb)
