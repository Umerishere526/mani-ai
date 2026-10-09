# ABOUTME: Stops a model supplied id or value from reaching the database or the app unchecked.
# ABOUTME: The reply's words are never edited here; each guard that fires leaves a note naming the guard and the field.

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from mani.chat.techniques import Registry, last_own_phase
from mani.llm.schema import LibrarySection, Reply, SmartPrompt, Style
from mani.models.rows import StageStatus

MAX_TITLE_LENGTH = 100


class Ending(StrEnum):
    """How a reply ends a framework, as response_format.md's `fields.ending` names them."""

    CHOICE = "choice"
    KEEP_TALKING = "keep_talking"

# The statuses a reply may report. `passed` is the code's alone, written when a stage is left behind.
_REPORTABLE_STATUSES = frozenset({StageStatus.MISSING, StageStatus.PARTIAL, StageStatus.KNOWN})

# Keyed lowercase so a model's casing does not matter; valued at the canonical casing so
# whatever reaches the client to navigate on is always exactly what LibrarySection defines.
_LIBRARY_SECTIONS = {section.value.lower(): section.value for section in LibrarySection}


def clean_title(title: str | None) -> str | None:
    """Tidy a title rather than refusing one that is slightly too long.

    The schema capped it at 50 characters, which failed the whole generation - title and
    reply together - over a title nobody would have minded being trimmed.
    """
    if not title:
        return None
    cleaned = title.strip().strip("\"'").rstrip(".")
    return cleaned[:MAX_TITLE_LENGTH].strip() or None


@dataclass(frozen=True)
class Checked:
    text: str
    prompts: list[SmartPrompt]
    title: str | None
    framework_id: str | None
    phase: str | None
    style: Style | None = None
    ending: Ending | None = None
    # What the reply reports of each stage of the running framework, kept to the stages it has and
    # the statuses a reply may write. None when the reply reported none, or its state was ignored.
    stages: dict[str, StageStatus] | None = None
    # Which guards fired, for the log and for a measure of how often the model slips on structure.
    notes: list[str] = field(default_factory=list)


def _is_offer_button(prompt: SmartPrompt) -> bool:
    return bool(prompt.technique or prompt.decline)


def without_offer(prompts: list[SmartPrompt]) -> list[SmartPrompt]:
    """The buttons with the offer taken out: its yes, and the decline that only answers it."""
    return [p for p in prompts if not _is_offer_button(p)]


def _recorded_phase(
    registry: Registry, framework_id: str, current_phase: str | None, reported_step: str,
    notes: list[str],
) -> str | None:
    """The phase to record from the framework's last own phase on, where the reported step moves
    through the ending in the order the framework runs. A step before it, or one the framework does
    not have, holds the stored phase.

    Before that phase the stored phase is the code's, read from the ledger, so none is recorded here.
    """
    framework = registry.get(framework_id)
    closing = framework.phase_index(last_own_phase(framework))
    if framework.phase_index(reported_step) < closing:
        if not framework.knows_phase(reported_step):
            notes.append("corrected the reported stage: unknown_phase")
        return current_phase
    transition = registry.validate_transition(framework_id, current_phase, reported_step)
    if not transition.ok:
        notes.append(f"corrected the reported stage: {transition.reason}")
    return registry.clamp(framework_id, current_phase, reported_step)


def _checked_stages(
    registry: Registry, framework_id: str, reported, notes: list[str]
) -> dict[str, StageStatus] | None:
    """The reported stages that name a stage of the framework with a status a reply may write.
    A stage listed twice takes its last entry. A dropped entry leaves a note with the reason only."""
    if reported is None:
        return None
    wanted = registry.ledger_stages(framework_id)
    kept: dict[str, StageStatus] = {}
    for entry in reported:
        status = entry.status.strip().lower()
        if entry.stage not in wanted:
            notes.append("dropped a stage report: not a stage of the framework")
        elif status not in _REPORTABLE_STATUSES:
            notes.append("dropped a stage report: status not on the list")
        else:
            kept[entry.stage] = StageStatus(status)
    return kept


def check(
    reply: Reply,
    registry: Registry,
    *,
    current_framework_id: str | None,
    current_phase: str | None,
    accepted_this_turn: bool,
    framework_running: bool,
    declined: bool,
    retiring: bool,
    wants_title: bool,
    shapes: frozenset[str],
    ending_open: bool = False,
) -> Checked:
    """The reply as the model wrote it, with only what cannot be stored or shown taken out.

    Text is the model's own, trimmed. A button is dropped when it has no label, offers a
    framework the registry does not hold, or would open an offer where one cannot stand: while
    a framework runs, on the turn they said no, or on the turn a framework retires, where the
    offer's row would overwrite the decline or the retirement. An offer left without its yes
    takes its decline with it. A reported step counts only from the framework's last own phase
    on, where it is clamped to the order the framework runs in; before that the ledger decides the
    stage. Reported stages are kept to the ones the running framework has and the statuses a reply
    may write. A reported shape is kept only when it is one of `shapes`,
    the ones the mani_base prompt teaches. A reported ending is kept only while `ending_open`,
    when it is one of Ending, and when the reply does not also move the stage forward, since a
    reply that offers the body check or starts its steps is not the end.
    """
    notes: list[str] = []

    framework_id: str | None = None
    phase: str | None = None
    stages: dict[str, StageStatus] | None = None
    if reply.state is not None:
        if reply.state.technique not in registry:
            notes.append("ignored state: technique not in the registry")
        elif framework_running and reply.state.technique != current_framework_id:
            # Every framework shares stage ids like somatic_checkin and closing, so the
            # transition check alone would let a reply record a framework the person never
            # accepted.
            notes.append("ignored state: not the running framework")
        else:
            framework_id = reply.state.technique
            stages = _checked_stages(registry, framework_id, reply.state.stages, notes)
            # Before the last own phase the ledger decides the stage, so only from there on does the
            # reported step record anything. The turn that accepts an offer is never past it.
            if not accepted_this_turn and registry.ending_open(framework_id, current_phase):
                phase = _recorded_phase(
                    registry, framework_id, current_phase, reply.state.step, notes
                )

    ending: Ending | None = None
    if reply.ending is not None:
        reported = reply.ending.strip().lower()
        running = registry.get(current_framework_id)
        if not ending_open or running is None:
            notes.append("ignored ending: the ending is not open")
        elif reported not in Ending:
            notes.append("ignored ending: not one of the endings")
        elif phase is not None and running.phase_index(phase) > running.phase_index(current_phase):
            notes.append("ignored ending: the reply moves the stage forward")
        else:
            ending = Ending(reported)
    retiring = retiring or ending is not None

    kept: list[SmartPrompt] = []
    for prompt in reply.prompts or []:
        if not prompt.label.strip():
            notes.append("dropped a button: empty label")
            continue
        if prompt.technique is not None:
            # A model-supplied identifier is untrusted until it matches the registry.
            if prompt.technique not in registry:
                notes.append("dropped a technique button: not in the registry")
                continue
            # A framework in progress is the whole conversation until it completes or the
            # person stops it: a technique button then is a framework offered inside one.
            if framework_running:
                notes.append("dropped a technique button: a framework is running")
                continue
            # What the offer would store overwrites the decline or the retirement this turn
            # is recording.
            if declined or retiring:
                notes.append("dropped a technique button: this turn declines or retires an offer")
                continue
        if prompt.library is not None:
            # A button pointing nowhere is worse than no button: it navigates the person out of
            # the conversation and into a section that does not exist. Case is normalized the
            # same way the shape is - checked loosely, stored exactly, so a client navigating on
            # this string always gets the canonical spelling. An unknown value still meant the
            # library, so it opens the front page rather than losing the button.
            canonical_library = _LIBRARY_SECTIONS.get(prompt.library.strip().lower())
            if canonical_library is None:
                notes.append("sent a button to the library home: unknown library section")
                canonical_library = LibrarySection.HOME.value
            if canonical_library != prompt.library:
                prompt = prompt.model_copy(update={"library": canonical_library})
        kept.append(prompt)

    # Keep Chatting answers an offer. Once the offer's own button is gone it answers
    # nothing, so it goes with it.
    if any(p.technique for p in reply.prompts or []) and not any(p.technique for p in kept):
        remaining = without_offer(kept)
        if len(remaining) != len(kept):
            notes.append("dropped the offer's other buttons: its technique button was dropped")
            kept = remaining

    title = clean_title(reply.title) if wants_title else None

    # Case and spacing are normalized before the check because a model reading a table of
    # names returns "Mirror and ask" far more often than it returns something off-list, and
    # dropping those would starve the anti-repetition loop this check exists to protect.
    style = reply.style
    if style is not None:
        shape = style.shape.strip().lower()
        if shape not in shapes:
            notes.append("dropped the response shape: not on the list")
            style = None
        else:
            style = Style(shape=shape)

    return Checked(
        text=reply.text.strip(),
        prompts=kept,
        title=title,
        framework_id=framework_id,
        phase=phase,
        style=style,
        ending=ending,
        stages=stages,
        notes=notes,
    )
