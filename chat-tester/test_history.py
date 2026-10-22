# ABOUTME: Checks that a thread's history is paged in from its newest message back to its first.
# ABOUTME: Serves pages from a fake backend that is as paged as the real one; needs no services.

from __future__ import annotations

import client as mani


class PagedBackend(mani.ManiClient):
    """Serves a thread's messages newest first, `limit` at a time, with a cursor to the next page."""

    def __init__(self, total: int) -> None:
        super().__init__(session=mani.Session("user", "token", "refresh"))
        self.stored = [{"content": f"m{i}"} for i in range(total)]
        self.cursors_seen: list[str | None] = []

    def _call(self, method, path, **kwargs):
        params = kwargs["params"]
        self.cursors_seen.append(params.get("cursor"))
        end = int(params["cursor"]) if params.get("cursor") else len(self.stored)
        start = max(0, end - params["limit"])
        return {
            "messages": self.stored[start:end][::-1],
            "next_cursor": str(start) if start > 0 else None,
        }


def test_full_history_follows_the_cursor_to_the_first_message():
    backend = PagedBackend(total=250)

    history = backend.full_history("thread")

    assert [m["content"] for m in history] == [f"m{i}" for i in range(250)]
    assert backend.cursors_seen == [None, "150", "50"]
