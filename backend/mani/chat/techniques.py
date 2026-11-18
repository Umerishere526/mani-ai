# ABOUTME: The registry of active frameworks, keyed by id, and where each one's phases end.
# ABOUTME: Membership here is the closed set a model supplied technique id is checked against.

from __future__ import annotations

from mani.models.rows import Framework

# Every framework opens by offering itself. The schema enforces it; the machine relies
# on it to tell "nothing started" apart from "started at the beginning".
OFFERING = "offering"
# An offer whose five steps have been shown: the next answer starts the set, sets it aside, or lets it lapse.
STEPS = "steps"
# A framework whose last stage is answered, while Mani asks how they feel now; the next answer closes it.
FEELINGS = "feelings_check"
# How the reply that starts a set opens, so the jump from the chat into the first stage is not abrupt.
FIRST_STAGE_OPENING = ("one short sentence that takes them from the whole story to one moment, then its line and that "
                       "stage's question")


def stages_of(framework: Framework) -> list[str]:
    """The stages the person answers, in order: every phase after the offer."""
    return [phase for phase in framework.phases if phase != OFFERING]


def line_of(framework: Framework, stage: str) -> str:
    """What opens a stage when it is reached, such as "A is for Activating Event."."""
    return (framework.stages.get(stage) or {}).get("intro", "")


def steps_text(framework: Framework, style: str) -> str:
    """The client's five steps for this style, with the ready question that closes them."""
    return ((framework.stages.get(OFFERING) or {}).get("explain") or {}).get(style) or framework.summary


def example_text(framework: Framework) -> str:
    """The worked example shown when they tap I need an example."""
    return (framework.stages.get(OFFERING) or {}).get("example") or framework.summary


class Registry:
    """The active frameworks, keyed by id.

    Loaded from admin.frameworks rather than hardcoded, so adding a framework is a
    content change. Membership of this registry is the closed set that model-supplied
    technique ids are checked against.
    """

    def __init__(self, frameworks: list[Framework]) -> None:
        self._by_id = {f.id: f for f in frameworks}

    def __contains__(self, framework_id: object) -> bool:
        return framework_id in self._by_id

    def __len__(self) -> int:
        return len(self._by_id)

    @property
    def ids(self) -> list[str]:
        return list(self._by_id)

    def get(self, framework_id: str | None) -> Framework | None:
        return self._by_id.get(framework_id) if framework_id else None
