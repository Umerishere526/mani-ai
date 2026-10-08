# ABOUTME: Stops a model supplied id or value from reaching the database or the app unchecked.
# ABOUTME: The reply's words are never edited here; each guard that fires leaves a note naming the guard and the field.

from __future__ import annotations

from dataclasses import dataclass, field

from mani.chat.greeting import EXPLAIN_LABELS
from mani.chat.techniques import Registry
from mani.llm.schema import SHAPES, LibrarySection, Reply, SmartPrompt, Style

MAX_TITLE_LENGTH = 100

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
    # Which guards fired, for the log and for a measure of how often the model slips on structure.
    notes: list[str] = field(default_factory=list)


def _is_offer_button(prompt: SmartPrompt) -> bool:
    return bool(prompt.technique or prompt.decline or prompt.label.strip().lower() in EXPLAIN_LABELS)


def without_offer(prompts: list[SmartPrompt]) -> list[SmartPrompt]:
    """The buttons with the offer taken out: its Try it, and the Keep chatting and Tell me about
    this that only answer it."""
    return [p for p in prompts if not _is_offer_button(p)]


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
) -> Checked:
    """The reply as the model wrote it, with only what cannot be stored or shown taken out.

    Text is the model's own, trimmed. A button is dropped when it has no label, offers a
    framework the registry does not hold, or would open an offer where one cannot stand: while
    a framework runs, on the turn they said no, or on the turn a finished framework retires,
    where the offer's row would overwrite the decline or the retirement. An offer left without
    its Try it takes its Keep chatting and Tell me about this with it. A model reported stage
    is clamped to the order the framework runs in.
    """
    notes: list[str] = []

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

    # Tell me about this and Keep chatting answer an offer. Once the offer's own button is
    # gone they answer nothing, so they go with it.
    if any(p.technique for p in reply.prompts or []) and not any(p.technique for p in kept):
        remaining = without_offer(kept)
        if len(remaining) != len(kept):
            notes.append("dropped the offer's other buttons: its technique button was dropped")
            kept = remaining

    framework_id: str | None = None
    phase: str | None = None
    if reply.state is not None:
        if reply.state.technique not in registry:
            notes.append("ignored state: technique not in the registry")
        elif framework_running and reply.state.technique != current_framework_id:
            # Every framework shares stage ids like somatic and closing, so the transition
            # check alone would let a reply record a framework the person never accepted.
            notes.append("ignored state: not the running framework")
        else:
            framework_id = reply.state.technique
            # Accepting an offer this turn means the phase being left is the offering one,
            # whatever the stored row still says. What they told Mani before accepting
            # answers the first stage, so the reply may already be asking the second.
            previous = current_phase
            if accepted_this_turn:
                known = registry.get(framework_id)
                phases = known.phases if known else []
                first = phases.index("offering") + 1 if "offering" in phases else -1
                previous = phases[first] if 0 < first < len(phases) else "offering"
            transition = registry.validate_transition(
                framework_id, previous, reply.state.step
            )
            phase = registry.clamp(framework_id, previous, reply.state.step)
            if not transition.ok:
                notes.append(f"corrected the reported stage: {transition.reason}")
            if phase is None:
                framework_id = None

    title = clean_title(reply.title) if wants_title else None

    # Case and spacing are normalized before the check because a model reading a table of
    # names returns "Mirror and ask" far more often than it returns something off-list, and
    # dropping those would starve the anti-repetition loop this check exists to protect.
    style = reply.style
    if style is not None:
        shape = style.shape.strip().lower()
        if shape not in SHAPES:
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
        notes=notes,
    )
