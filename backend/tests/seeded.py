# ABOUTME: The seeded `replies` and `tuning` rows parsed from content/prompts, for tests to build from.
# ABOUTME: A test that needs another value overrides one key, and the rest stay what is seeded.

from __future__ import annotations

from scripts.seed import load_replies, load_tuning

from mani.prompts.replies import Replies
from mani.prompts.tuning import Tuning


def seeded_replies(**changes) -> Replies:
    return load_replies().model_copy(update=changes)


def seeded_tuning(**groups: dict) -> Tuning:
    """The seeded numbers, with the named keys of each group replaced:
    `seeded_tuning(offers={"cooldown_after_complete": 3})`."""
    tuning = load_tuning()
    return tuning.model_copy(update={
        group: getattr(tuning, group).model_copy(update=changes)
        for group, changes in groups.items()
    })
