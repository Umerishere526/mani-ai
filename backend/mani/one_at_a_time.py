# ABOUTME: One holder at a time per key within this process, for work that must not run twice at once.
# ABOUTME: Used where a database lock can no longer span a model call: a send, a summary, a memory fold.

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Hashable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field


@dataclass
class _Entry:
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    holders: int = 0


_entries: dict[Hashable, _Entry] = {}


@asynccontextmanager
async def one_at_a_time(key: Hashable) -> AsyncIterator[None]:
    """Wait for anyone else in this process holding `key`, then hold it. Another instance does not wait, so the
    work it guards must still check at its write that nobody got there first."""
    entry = _entries.setdefault(key, _Entry())
    entry.holders += 1
    try:
        async with entry.lock:
            yield
    finally:
        entry.holders -= 1
        if entry.holders == 0:
            del _entries[key]
