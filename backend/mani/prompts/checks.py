# ABOUTME: Decides whether a prompt row's content is one the application can run on.
# ABOUTME: Shared by the seed, the admin writes and the cache load, so all three refuse the same things.

from __future__ import annotations

import yaml

from mani.prompts.replies import parse_replies
from mani.prompts.tuning import parse_tuning

# The rows a turn cannot run without. The implementation this replaces pushed each layer only
# `if (prompt)`, so a prompt renamed or deactivated in the portal simply vanished from the system
# prompt and Mani quietly changed personality. The framework catalogue between the two authored
# layers is generated from the registry rather than stored as a prompt, so it is not listed here.
# `replies` and `tuning` are never sent to a model; they are what the code sends and counts by.
REQUIRED_PROMPTS = ("mani_base", "response_format", "replies", "tuning")


def parse_reply_shapes(content: str) -> frozenset[str]:
    """The reply shapes the mani_base prompt teaches: the keys of its `reply_shapes` map,
    trimmed and lowercased. Raises ValueError when the content has no such map, or none to read."""
    try:
        shapes = (yaml.safe_load(content) or {}).get("reply_shapes")
    except (yaml.YAMLError, AttributeError) as exc:
        raise ValueError("mani_base does not parse as a YAML map") from exc
    if not isinstance(shapes, dict) or not shapes:
        raise ValueError("mani_base has no non empty reply_shapes map")
    return frozenset(str(name).strip().lower() for name in shapes)


_PARSERS = {"mani_base": parse_reply_shapes, "replies": parse_replies, "tuning": parse_tuning}


def content_problem(name: str, content: str) -> str | None:
    """Why this row's content cannot be used, or None. Never raises.

    The problem names the key and the rule, never the value written. A name nothing reads the
    content of returns None.
    """
    parser = _PARSERS.get(name)
    if parser is None:
        return None
    try:
        parser(content)
    except ValueError as problem:
        return str(problem)
    return None
