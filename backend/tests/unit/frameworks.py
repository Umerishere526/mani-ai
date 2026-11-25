# ABOUTME: The active frameworks as the turn sees them, built from the real content files the seed loads, for tests
# ABOUTME: that need a registry; never hand-written dictionaries, so a content change shows up here too.

from __future__ import annotations

import uuid

from mani.chat.techniques import Registry
from mani.models.rows import Framework, TechniqueOutcome, TechniqueState
from scripts.seed import FRAMEWORKS_DIR, parse_framework

THREAD = uuid.UUID("00000000-0000-4000-8000-0000000000a1")


def framework(file_id: str) -> Framework:
    parsed = parse_framework(FRAMEWORKS_DIR / f"{file_id}.md")
    return Framework(**{key: parsed[key] for key in (
        "id", "name", "summary", "body", "activation_conditions", "phases", "display_order", "activation", "stages",
    )})


REGISTRY = Registry([framework("abcde"), framework("thought_reframe"), framework("structured_problem_solving")])


def offered(framework_id: str = "abcde", phase: str = "offering") -> TechniqueState:
    return TechniqueState(thread_id=THREAD, framework_id=framework_id, outcome=TechniqueOutcome.OFFERED,
                          phase=phase, at_message_count=4)


def running(framework_id: str, phase: str) -> TechniqueState:
    return TechniqueState(thread_id=THREAD, framework_id=framework_id, outcome=TechniqueOutcome.ACCEPTED,
                          phase=phase, at_message_count=6)
