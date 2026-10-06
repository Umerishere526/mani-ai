# ABOUTME: The technique phase machine - which framework, which step, and what may follow.
# ABOUTME: Unlike the implementation it replaces, an unrecognised value fails closed.

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from mani.models.rows import Framework

# Every framework opens by offering itself. The schema enforces it; the machine relies
# on it to tell "nothing started" apart from "started at the beginning".
OFFERING = "offering"

# The two stages every framework ends on. The body check owns the turns from the first of them.
SOMATIC_STAGES = frozenset({"somatic_checkin", "somatic_practice"})


def moves_on_after(framework: Framework | None, phase: str | None) -> bool:
    """Whether a reply to `phase` is answered by asking the stage after it.

    True from the first stage after the offering up to the stage before the body check. The
    offering's own turn (accepting it), the body check and a phase the framework does not know
    are left to the turn rules that apply there.
    """
    if framework is None or not framework.knows_phase(phase) or phase in SOMATIC_STAGES:
        return False
    offering = framework.phase_index(OFFERING)
    return 0 <= offering < framework.phase_index(phase) < len(framework.phases) - 1


def covered_stages(framework: Framework | None, known: dict[str, str]) -> list[str]:
    """The stages right after the offering that what the person said before accepting answers.

    A stage names the fact that answers it in `answered_by`. Only an unbroken run from the first
    stage counts, and the last stage before the body check is never covered, so there is always
    a question left to ask.
    """
    if framework is None or OFFERING not in framework.phases:
        return []
    covered: list[str] = []
    for phase in framework.phases[framework.phase_index(OFFERING) + 1 : -1]:
        if phase in SOMATIC_STAGES or (framework.stages.get(phase) or {}).get("answered_by") not in known:
            break
        covered.append(phase)
    return covered


def _phase_after(framework: Framework, phase: str | None) -> str | None:
    index = framework.phase_index(phase)
    return framework.phases[index + 1] if 0 <= index < len(framework.phases) - 1 else None


class Verdict(StrEnum):
    OK = "ok"
    UNKNOWN_FRAMEWORK = "unknown_framework"
    UNKNOWN_PHASE = "unknown_phase"
    SKIPPED_PHASES = "skipped_phases"
    MISSING_OFFERING = "missing_offering"
    STEPPED_BACK = "stepped_back"


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

    def get(self, framework_id: str | None) -> Framework | None:
        return self._by_id.get(framework_id) if framework_id else None

    def is_final(self, framework_id: str | None, phase: str | None) -> bool:
        """Whether this phase is the last one in the framework's sequence.

        Completion is a position, not a name. Comparing against a literal phase id can
        only ever recognise the frameworks that happen to end on it, and makes any phase
        appended after it unreachable.
        """
        framework = self.get(framework_id)
        if framework is None or phase is None:
            return False
        return bool(framework.phases) and framework.phases[-1] == phase

    def validate_transition(
        self,
        framework_id: str | None,
        current_phase: str | None,
        next_phase: str | None,
        *,
        moving_on: bool = False,
    ) -> Transition:
        """Whether a technique may move from current_phase to next_phase.

        Staying on a phase is always allowed. Stepping back is allowed too, except on a turn
        that moves on (`moves_on_after`): the person has answered current_phase, so going back
        to it or earlier asks it again. There a step back, and a phase the framework does not
        have, are corrected to the phase after current_phase, never to current_phase itself:
        only an explicit hold, which the caller decides, keeps the stage.

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
            return Transition(
                Verdict.UNKNOWN_PHASE,
                expected_next=_phase_after(framework, current_phase) if moving_on else None,
            )

        # A phase we do not recognise is treated as nothing having started, which makes
        # the only legal move the opening one.
        current_index = framework.phase_index(current_phase)
        next_index = framework.phase_index(next_phase)

        if moving_on and next_index < current_index:
            return Transition(
                Verdict.STEPPED_BACK, expected_next=_phase_after(framework, current_phase)
            )

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
        *,
        moving_on: bool = False,
    ) -> str | None:
        """The phase to actually record, correcting a bad one instead of regenerating.

        Phase tracking is observability, not enforcement - the reference says so in its
        own header - so a skip is worth correcting in code rather than paying for
        another model call, which is what it cost before.
        """
        transition = self.validate_transition(
            framework_id, current_phase, next_phase, moving_on=moving_on
        )
        if transition.ok:
            return next_phase
        # Unknown framework or phase leaves nothing trustworthy to record.
        return transition.expected_next
