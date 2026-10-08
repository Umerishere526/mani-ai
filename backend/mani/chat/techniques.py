# ABOUTME: The technique phase machine - which framework, which step, and what may follow.
# ABOUTME: Unlike the implementation it replaces, an unrecognised value fails closed.

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum

from mani.chat.router import Rule, distinction_rules
from mani.models.rows import Framework

logger = logging.getLogger(__name__)

# Every framework opens by offering itself. The schema enforces it; the machine relies
# on it to tell "nothing started" apart from "started at the beginning".
OFFERING = "offering"

# The body ending every framework closes with: the offer of the body check, then its steps.
# The seed appends them after each framework's own phases; what Mani says in them is the
# mani_base prompt's `ending` section.
ENDING_PHASES = ("somatic_checkin", "somatic_practice")


class Verdict(StrEnum):
    OK = "ok"
    UNKNOWN_FRAMEWORK = "unknown_framework"
    UNKNOWN_PHASE = "unknown_phase"
    SKIPPED_PHASES = "skipped_phases"
    MISSING_OFFERING = "missing_offering"


@dataclass(frozen=True)
class Transition:
    verdict: Verdict
    skipped: list[str] = field(default_factory=list)
    expected_next: str | None = None

    @property
    def ok(self) -> bool:
        return self.verdict is Verdict.OK

    @property
    def reason(self) -> str:
        if self.verdict is Verdict.SKIPPED_PHASES:
            return f"skipped {', '.join(self.skipped)}"
        return self.verdict.value


class Registry:
    """The active frameworks, keyed by id.

    Loaded from admin.frameworks rather than hardcoded, so adding a framework is a
    content change. Membership of this registry is the closed set that model-supplied
    technique ids are checked against.
    """

    def __init__(self, frameworks: list[Framework]) -> None:
        self._by_id = {f.id: f for f in frameworks}
        # Built once per load. The seed refuses a broken rule, but a portal edit skips the seed,
        # so a rule that breaks one here is logged and dropped and the rest still route.
        self._distinctions, problems = distinction_rules(
            {f.id: (f.activation or {}).get("distinctions", []) for f in frameworks}
        )
        for problem in problems:
            logger.error("framework distinction dropped: %s", problem)

    def __contains__(self, framework_id: object) -> bool:
        return framework_id in self._by_id

    def __len__(self) -> int:
        return len(self._by_id)

    @property
    def ids(self) -> list[str]:
        return list(self._by_id)

    @property
    def activations(self) -> dict[str, dict]:
        """Every framework's routing data, keyed by id - the router's whole input."""
        return {fid: f.activation for fid, f in self._by_id.items()}

    @property
    def distinctions(self) -> list[Rule]:
        """The routing rules every framework's distinctions make, ordered by priority."""
        return self._distinctions

    def get(self, framework_id: str | None) -> Framework | None:
        return self._by_id.get(framework_id) if framework_id else None

    def ending_open(self, framework_id: str | None, phase: str | None) -> bool:
        """Whether the framework is far enough along that a reply may end it: on its last own
        phase, where Mani asks how they feel, or on one of the ending phases after it.

        False for a framework whose phases carry no ending, such as one seeded before the
        ending was appended, so nothing can end it early.
        """
        framework = self.get(framework_id)
        if framework is None or phase is None or ENDING_PHASES[0] not in framework.phases:
            return False
        return framework.phase_index(phase) >= framework.phases.index(ENDING_PHASES[0]) - 1

    def validate_transition(
        self,
        framework_id: str | None,
        current_phase: str | None,
        next_phase: str | None,
    ) -> Transition:
        """Whether a technique may move from current_phase to next_phase.

        The implementation this replaces returned *valid* for an unrecognised framework
        or an unrecognised phase, so one hallucinated identifier silently switched the
        whole guard off - and the bad value was then written to the database. Here both
        are refusals, and the caller's remedy is to drop the state field, never to fail
        the turn.
        """
        framework = self.get(framework_id)
        if framework is None:
            return Transition(Verdict.UNKNOWN_FRAMEWORK)

        if not framework.knows_phase(next_phase):
            return Transition(Verdict.UNKNOWN_PHASE)

        # A phase we do not recognise is treated as nothing having started, which makes
        # the only legal move the opening one.
        current_index = framework.phase_index(current_phase)
        next_index = framework.phase_index(next_phase)

        if next_index <= current_index:
            # Holding on a phase, or stepping back, is a legitimate conversational move.
            return Transition(Verdict.OK)

        if current_index < 0 and next_phase != OFFERING:
            return Transition(
                Verdict.MISSING_OFFERING,
                skipped=framework.phases[:next_index],
                expected_next=OFFERING,
            )

        if next_index - current_index > 1:
            return Transition(
                Verdict.SKIPPED_PHASES,
                skipped=framework.phases[current_index + 1 : next_index],
                expected_next=framework.phases[current_index + 1],
            )

        return Transition(Verdict.OK)

    def clamp(
        self,
        framework_id: str | None,
        current_phase: str | None,
        next_phase: str | None,
    ) -> str | None:
        """The phase to actually record, correcting a bad one instead of regenerating.

        Phase tracking is observability, not enforcement - the reference says so in its
        own header - so a skip is worth correcting in code rather than paying for
        another model call, which is what it cost before.
        """
        transition = self.validate_transition(framework_id, current_phase, next_phase)
        if transition.ok:
            return next_phase
        # Unknown framework or phase leaves nothing trustworthy to record.
        return transition.expected_next
