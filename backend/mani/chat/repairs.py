# ABOUTME: Fixes what a model reply gets wrong, in code, without calling the model again.
# ABOUTME: Each check the reference answered with a regeneration is a rewrite here.

from __future__ import annotations

import re
from dataclasses import dataclass, field

from mani.chat.techniques import Registry
from mani.llm.schema import Reply, SmartPrompt

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
    # What was corrected, for the log and for a metric on how often the model needs it.
    notes: list[str] = field(default_factory=list)


def _normalize(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def apply(
    reply: Reply,
    registry: Registry,
    *,
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

    return Repaired(
        text=text,
        prompts=kept,
        title=title,
        framework_id=framework_id,
        phase=phase,
        notes=notes,
    )
