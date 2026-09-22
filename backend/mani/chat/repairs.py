# ABOUTME: Fixes what a model reply gets wrong, in code, without calling the model again.
# ABOUTME: Each check the reference answered with a regeneration is a rewrite here.

from __future__ import annotations

import re
from dataclasses import dataclass, field

from mani.chat.techniques import Registry
from mani.llm.schema import SHAPES, VOICES, LibrarySection, Reply, SmartPrompt, Style

MAX_PROMPTS = 3
MAX_TITLE_LENGTH = 100

# Instructions meant for the model that it sometimes copies out of the technique library
# and into the user's face.
SCRIPT_LEAKAGE = [
    re.compile(r"\(Include prompts?:[^)]*\)", re.IGNORECASE),
    re.compile(r"\*\*User:\*\*"),
    re.compile(r"\*\*Mani:\*\*"),
    re.compile(r"<!-- ?(step|technique):[^>]*-->", re.IGNORECASE),
    re.compile(r"^Prompts:\s*\[.*\]\s*$", re.MULTILINE),
    re.compile(r"^State:\s*\{.*\}\s*$", re.MULTILINE),
    re.compile(r"```\s*\n?\s*Prompts:", re.MULTILINE),
]

_BLANK_RUN = re.compile(r"\n{3,}")

# The reference also refused the words "broken", "weak" and "heavy" anywhere in a reply.
# That is dropped: the same prompt instructs Mani to mirror the user's own words back, so
# a person saying "I feel broken" made a correct, caring reply unsendable - and the cost
# of the collision was an entire extra generation.
#
# The lists below are the corrected version of that idea, and they apply to capsule labels
# rather than to prose. A label is the one thing in a reply the person may send back as
# their own words, so dropping a bad one is a safe correction where rewriting a sentence
# would not be. The mirroring collision is handled by exempting anything the person said.

# The feeling words the specifications are strict about: a reply may use one only if the
# person used it first. "MANI never introduces a feeling word the user did not use."
FEELING_WORDS = frozenset(
    {
        "abandoned", "afraid", "angry", "anxious", "ashamed", "betrayed", "broken",
        "crushed", "defeated", "dejected", "depressed", "desperate", "devastated",
        "disappointed", "distressed", "embarrassed", "exhausted", "fearful", "frustrated",
        "furious", "guilty", "helpless", "hopeless", "humiliated", "hurt", "insecure",
        "isolated", "lonely", "lost", "miserable", "overwhelmed", "panicked", "rejected",
        "resentful", "sad", "scared", "stressed", "terrified", "trapped", "unloved",
        "unwanted", "upset", "worried", "worthless",
        # The adjectival forms, which describe the situation rather than the person and are
        # the shape a capsule label usually takes: "It's frustrating", "It's exhausting".
        "depressing", "devastating", "draining", "embarrassing", "exhausting",
        "frustrating", "humiliating", "isolating", "overwhelming", "terrifying",
        "upsetting", "worrying",
    }
)

# Judgments a person may hold about themselves but must never be handed as a button to press.
# Observed live: a reply offered "I'm overthinking it" as a capsule.
SELF_JUDGMENTS = (
    "overthinking", "over thinking", "being dramatic", "too sensitive", "overreacting",
    "over reacting", "being silly", "being stupid", "my fault", "i'm weak", "i am weak",
    "i'm broken", "i am broken", "not enough", "being needy", "being difficult",
)

MAX_CAPSULE_WORDS = 4

# Keyed lowercase so a model's casing does not matter; valued at the canonical casing so
# whatever reaches the client to navigate on is always exactly what LibrarySection defines.
_LIBRARY_SECTIONS = {section.value.lower(): section.value for section in LibrarySection}

WORD = re.compile(r"[a-z']+")


def words(text: str) -> set[str]:
    return set(WORD.findall(text.lower()))


def strip_script_leakage(text: str) -> tuple[str, list[str]]:
    """Remove leaked script metadata. Returns the cleaned text and what was removed."""
    found: list[str] = []
    cleaned = text
    for pattern in SCRIPT_LEAKAGE:
        matches = pattern.findall(cleaned)
        if matches:
            found.extend(m if isinstance(m, str) else str(m) for m in matches)
            cleaned = pattern.sub("", cleaned)
    if found:
        cleaned = _BLANK_RUN.sub("\n\n", cleaned).strip()
    return cleaned, found


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
class Repaired:
    text: str
    prompts: list[SmartPrompt]
    title: str | None
    framework_id: str | None
    phase: str | None
    style: Style | None = None
    # What was corrected, for the log and for a metric on how often the model needs it.
    notes: list[str] = field(default_factory=list)


def _normalize(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def apply(
    reply: Reply,
    registry: Registry,
    *,
    said: str,
    already_offered: list[str],
    current_framework_id: str | None,
    current_phase: str | None,
    selected_label: str | None,
    accepted_this_turn: bool,
    framework_running: bool,
    wants_title: bool,
) -> Repaired:
    """Everything wrong with a reply that can be fixed without asking again.

    The implementation this replaces answered each of these by re-calling the provider,
    up to six extra generations for one user message. They are all deterministic checks
    on text the model already produced, so they are corrections, not retries.
    """
    notes: list[str] = []

    text, leaked = strip_script_leakage(reply.text.strip())
    if leaked:
        notes.append(f"stripped script metadata: {', '.join(leaked)}")

    theirs = words(said)
    # Observational only, for now: the capsule check below can safely drop a bad button,
    # but dropping a sentence out of the reply itself is a different, riskier correction -
    # it can leave the reply answering nothing. This logs what the prompt's own "feeling
    # audit" self-check is missing, so a fix can be sized against real frequency instead
    # of guessed at.
    introduced_in_text = sorted(words(text) & FEELING_WORDS - theirs)
    if introduced_in_text:
        notes.append(
            f"reply text introduced a feeling word the user did not establish: "
            f"{', '.join(introduced_in_text)}"
        )

    offered = {_normalize(name) for name in already_offered}
    # While a framework is only being *offered*, the capsule naming it is the offer itself,
    # not a duplicate of one - so it survives the already-offered check. Once the person has
    # accepted and the framework is running, that exemption would do the opposite of its job:
    # it is what lets the running framework be offered again from inside itself.
    if current_framework_id and not framework_running:
        offered.discard(_normalize(current_framework_id))

    selected = selected_label.strip().lower() if selected_label else None
    seen_labels: set[str] = set()
    kept: list[SmartPrompt] = []

    for prompt in reply.prompts or []:
        label = prompt.label.strip()
        key = label.lower()

        if not label:
            continue
        if key in seen_labels:
            notes.append(f"dropped a repeated label: {label}")
            continue
        if selected and key == selected:
            # Offering back the button the user just pressed reads as not listening.
            notes.append(f"dropped the button the user just tapped: {label}")
            continue
        # A label may not name a feeling they did not name, judge them, or run long enough
        # to be a sentence. Dropping the button is the whole correction: rewriting one would
        # put different words in their mouth rather than none.
        introduced = sorted(words(label) & FEELING_WORDS - theirs)
        if introduced:
            notes.append(f"dropped a button naming a feeling they did not use: {label}")
            continue
        if any(phrase in key for phrase in SELF_JUDGMENTS):
            notes.append(f"dropped a button that judges them: {label}")
            continue
        if len(label.split()) > MAX_CAPSULE_WORDS:
            notes.append(f"dropped a button that runs long: {label}")
            continue
        if prompt.library is not None:
            # A button pointing nowhere is worse than no button: it navigates the person
            # out of the conversation and into a section that does not exist. Case is
            # normalized the same way shape and voice are - checked loosely, stored exactly,
            # so a client navigating on this string always gets the canonical spelling.
            canonical_library = _LIBRARY_SECTIONS.get(prompt.library.strip().lower())
            if canonical_library is None:
                notes.append(
                    f"dropped a button naming an unknown library section: {prompt.library}"
                )
                continue
            if canonical_library != prompt.library:
                prompt = prompt.model_copy(update={"library": canonical_library})
        if prompt.technique is not None:
            # A framework in progress is the whole conversation until it completes or the
            # person stops it. Any technique button while one is running is a framework
            # offered inside a framework - the same one restarting itself, or a second one
            # opening underneath the first - and the person is the one left holding both.
            if framework_running:
                notes.append(
                    f"dropped a technique offered inside a running framework: {prompt.technique}"
                )
                continue
            # A model-supplied identifier is untrusted until it matches the registry.
            if prompt.technique not in registry:
                notes.append(f"dropped an unknown technique: {prompt.technique}")
                continue
            if _normalize(prompt.technique) in offered:
                notes.append(f"dropped an already-offered technique: {prompt.technique}")
                continue

        seen_labels.add(key)
        kept.append(prompt)

    if len(kept) > MAX_PROMPTS:
        notes.append(f"trimmed {len(kept)} buttons to {MAX_PROMPTS}")
        kept = kept[:MAX_PROMPTS]

    framework_id: str | None = None
    phase: str | None = None
    if reply.state is not None:
        if reply.state.technique not in registry:
            notes.append(f"ignored state for unknown technique: {reply.state.technique}")
        else:
            framework_id = reply.state.technique
            # Accepting an offer this turn means the phase being left is the offering one,
            # whatever the stored row still says.
            previous = "offering" if accepted_this_turn else current_phase
            transition = registry.validate_transition(
                framework_id, previous, reply.state.step
            )
            phase = registry.clamp(framework_id, previous, reply.state.step)
            if not transition.ok:
                notes.append(
                    f"corrected phase {reply.state.step!r} to {phase!r} "
                    f"({transition.reason})"
                )
            if phase is None:
                framework_id = None

    title = clean_title(reply.title) if wants_title else None

    # Case and spacing are normalized before the check because a model reading a table of
    # names returns "Mirror and ask" far more often than it returns something off-list, and
    # dropping those would starve the anti-repetition loop this check exists to protect.
    style = reply.style
    if style is not None:
        shape = style.shape.strip().lower()
        voice = style.voice.strip().lower() if style.voice else None
        if shape not in SHAPES:
            notes.append(f"dropped an off-list response shape: {style.shape}")
            style = None
        else:
            if voice is not None and voice not in VOICES:
                notes.append(f"dropped an off-list mirroring voice: {style.voice}")
                voice = None
            style = Style(shape=shape, voice=voice)

    return Repaired(
        text=text,
        prompts=kept,
        title=title,
        framework_id=framework_id,
        phase=phase,
        style=style,
        notes=notes,
    )
