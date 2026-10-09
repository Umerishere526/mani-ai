# ABOUTME: Fixes what a model reply gets wrong, in code, without calling the model again.
# ABOUTME: Each check the reference answered with a regeneration is a rewrite here.

from __future__ import annotations

import re
from difflib import SequenceMatcher
from dataclasses import dataclass, field

from mani.chat.greeting import (
    CLARIFICATION_QUESTIONS,
    EXPLAIN_LABELS,
    KEEP_CHATTING_LABEL,
    TELL_ME_MORE_LABEL,
    TRY_IT_LABEL,
)
from mani.chat.techniques import OFFERING, Registry
from mani.llm.schema import SHAPES, LibrarySection, Reply, SmartPrompt, Style
from mani.models.rows import ENDING_STAGES

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

# Where a reply may carry buttons besides an offer: the body check-in and the practice that ends
# a framework. Everywhere else a button reads as a menu instead of a conversation (client, 2026-09-24). The greeting's style buttons and Chat More /
# Go to Library are written by the orchestrator after this runs, so they are not affected.

# Keyed lowercase so a model's casing does not matter; valued at the canonical casing so
# whatever reaches the client to navigate on is always exactly what LibrarySection defines.
_LIBRARY_SECTIONS = {section.value.lower(): section.value for section in LibrarySection}

# The permission question an offer asks, in each style. The client's ABCDE document asks it the
# same way in all three (2026-10-09).
PERMISSION_QUESTIONS = {
    "direct": "Would you like to try it?",
    "supportive": "Would you like to try it?",
    "reflective": "Would you like to try it?",
}

# Words that mark a reply's question as the offer itself rather than some other question.
_OFFER_WORDS = re.compile(
    r"\btry\b|structured|work through|would it help|one step at a time|look at it together"
    r"|questions\b|go through|shall we",
    re.IGNORECASE,
)

# A sentence that makes an offer: the questions it offers ("a set of questions", "a few
# questions"), or the permission question after them. Offers are worded fresh each time.
_OFFER_SENTENCE = re.compile(
    r"(?:^|(?<=[.!?])|(?<=\n))[ \t]*[^.!?\n]*"
    r"(?:(?:sequence|set|series) of questions|\b(?:a few|some) questions\b"
    r"|would (?:you like|it help) to (?:try|work through|look at|go through)"
    r"|shall we (?:try|go through|look at))"
    r"[^.!?\n]*[.!?]?",
    re.IGNORECASE,
)

# The question a reply ends on, if it ends on one.
_LAST_QUESTION = re.compile(r"(?:^|(?<=[.!?])[ \t]+|(?<=\n))([^.!?\n]*\?)\s*$")



# The system's own words, which a person must never read (Loli's test, 2026-10-09: "the nearest
# fit I have" reached the person in all three styles).
_INTERNAL_WORDS = re.compile(
    r"\b(nearest|closest)\s+fit\b|\bframework[_ ]id\b|\boffer_fit\b|\bheading_toward\b"
    r"|\bframework index\b|\bcooldown\b|\[/?ctx\]",
    re.IGNORECASE,
)
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+")


def without_internal_words(text: str) -> str:
    """The text with every sentence that carries the system's own words dropped."""
    if not _INTERNAL_WORDS.search(text):
        return text
    paragraphs = []
    for paragraph in text.split("\n\n"):
        kept = [s for s in _SENTENCE_BREAK.split(paragraph) if not _INTERNAL_WORDS.search(s)]
        if kept:
            paragraphs.append(" ".join(kept))
    return "\n\n".join(paragraphs)


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


def _is_offer_button(prompt: SmartPrompt) -> bool:
    return bool(prompt.technique or prompt.decline or prompt.label.strip().lower() in EXPLAIN_LABELS)


def _without_clarification(text: str) -> str:
    """The reply without a repeated ask of the client's fixed clarifying question."""
    match = _LAST_QUESTION.search(text)
    if match and match.group(1).strip().lower().rstrip("?") + "?" in CLARIFICATION_QUESTIONS:
        return text[: match.start(1)].rstrip()
    return text


def _without_their_name(text: str, name: str, *, keep_one: bool) -> str:
    """The reply with their name said to them removed: always as the first word, and every
    time when it has been used already. With `keep_one`, the first later use stays."""
    first = re.compile(rf"^{re.escape(name)},\s*(\w)")
    text = first.sub(lambda m: m.group(1).upper(), text)
    vocative = re.compile(rf",\s*{re.escape(name)}(?=\s*[.!?,])")
    matches = list(vocative.finditer(text))
    for match in reversed(matches[1:] if keep_one else matches):
        text = text[: match.start()] + text[match.end():]
    return text


def with_the_check_in(text: str, script: str) -> str:
    """The body check-in, sent word for word. The client's flow (2026-09-24) treats it as
    fixed content: Mani's reflection stays, its own version of the question does not."""
    if script in text:
        return text
    match = _LAST_QUESTION.search(text)
    reflection = text[: match.start(1)].rstrip() if match else text.rstrip()
    return f"{reflection}\n\n{script}" if reflection else script


PLACE_LABELS = ("Chest", "Head", "Stomach", "Somewhere else")

# The place a person names for what they feel, in their own words. Anything else on the body
# is "somewhere else"; "idk" and its kind name no place at all.
_PLACE_WORDS = (
    ("Chest", re.compile(r"\bchest\b", re.IGNORECASE)),
    ("Head", re.compile(r"\bhead\b", re.IGNORECASE)),
    ("Stomach", re.compile(r"\b(stomach|belly|tummy|gut)\b", re.IGNORECASE)),
    ("Somewhere else", re.compile(
        r"\b(somewhere else|shoulders?|neck|throat|jaw|back|hands?|arms?|legs?|face)\b", re.IGNORECASE
    )),
)

# Saying no to the body check, or already knowing what they will do: either ends the route
# without a practice.
_DECLINES_OR_ACTS = re.compile(
    r"^\W*(no|nope|nah)\W*$|\b(no thanks|not now|maybe later|skip|rather not|don'?t want to"
    r"|i'?m going to|i am going to|i need to|i'?ll go|i will go)\b",
    re.IGNORECASE,
)


def named_place(text: str) -> str | None:
    """The place on the body a person's message names, as the label of its button."""
    return next((label for label, words in _PLACE_WORDS if words.search(text)), None)


def declines_or_acts(text: str) -> bool:
    return bool(_DECLINES_OR_ACTS.search(text))


def reply_for(branch: dict, style: str) -> str:
    """A stage branch's reply: one text for every style, or the client's text for this one."""
    reply = branch["reply"]
    return reply[style] if isinstance(reply, dict) else reply


def practice_for(stage: dict, place: str, style: str) -> tuple[str, list[str]] | None:
    """The client's practice for a place in this style, word for word, and its button labels."""
    for branch in stage.get("if_unclear") or []:
        if place.lower() in branch.get("when", ""):
            return reply_for(branch, style), list(branch.get("prompts") or [])
    return None


# The person says what they were told to expect: it eased, and then it came back.
_COMES_BACK = re.compile(r"\b(comes?|came|coming|returns?|returned) back\b|\bback again\b", re.IGNORECASE)


def comes_back(text: str) -> bool:
    return bool(_COMES_BACK.search(text))


def returning_reply(stage: dict, style: str) -> str | None:
    """The client's words for a feeling that returns after the practice."""
    branch = next((b for b in stage.get("if_unclear") or [] if "returns" in b.get("when", "")), None)
    return reply_for(branch, style) if branch else None


def first_sentence(text: str) -> str:
    """The reply's opening sentence: what Mani acknowledges before it asks."""
    match = re.match(r"\s*(.+?[.!?])(?:\s|$)", text, re.DOTALL)
    return match.group(1) if match else text


def practice_in(stage: dict, text: str, style: str) -> bool:
    """Whether a reply already gives one of the client's practices, found by its opening words."""
    return any(
        reply_for(branch, style)[:30] in text
        for branch in stage.get("if_unclear") or []
        if branch.get("when", "").startswith("they feel it in") or "somewhere else" in branch.get("when", "")
    )


def _without_permission_question(text: str) -> str:
    """The reply without a closing question that asks whether they want to try."""
    match = _LAST_QUESTION.search(text)
    if match and _OFFER_WORDS.search(match.group(1)):
        return text[: match.start(1)].rstrip()
    return text


def _says_name(text: str, name: str) -> bool:
    """Whether the set's name is in the text, however it is spelt or spaced."""
    letters = re.compile(r"[^a-z0-9]")
    return letters.sub("", name.lower()) in letters.sub("", text.lower())


def _compose_offer(
    part: str,
    registry: Registry,
    framework_id: str,
    style: str,
    last_mani_text: str | None,
    *,
    describe: bool,
) -> str:
    """Mani's part, which names the set, then the client's question: one paragraph each.

    The offer is short, as in the client's own examples (muhammad, 2026-10-09). The client's
    description goes between the two only when they asked to hear more, and never twice: not
    when the last reply showed it, nor when the model wrote it itself.
    """
    framework = registry.get(framework_id)
    # A framework may carry its own explanation of itself in each style (ABCDE's five steps). It is
    # the whole answer to Tell me more, so Mani's part is not added to it.
    explained = ((framework.stages.get("offering") or {}).get("explain") or {}).get(style) if framework else None
    if describe and explained:
        return "\n\n".join((explained, PERMISSION_QUESTIONS[style]))
    shown = " ".join(f"{last_mani_text or ''} {part}".split())
    if framework and not _says_name(shown, framework.name):
        part = f"{part} It's called {framework.name}.".strip()
    description = ""
    if describe and framework and framework.summary:
        description = " ".join(framework.summary.split())
        if description in shown:
            description = ""
    return "\n\n".join(p for p in (part, description, PERMISSION_QUESTIONS[style]) if p)


def _offer_buttons(framework_id: str, *, explained: bool) -> list[SmartPrompt]:
    """The client's buttons under an offer, in their words whatever the model wrote. Once they have
    tapped Tell me more they have been told, so the offer comes back with the other two."""
    buttons = [SmartPrompt(label=TRY_IT_LABEL, technique=framework_id)]
    if not explained:
        buttons.append(SmartPrompt(label=TELL_ME_MORE_LABEL))
    buttons.append(SmartPrompt(label=KEEP_CHATTING_LABEL, decline=True))
    return buttons


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
    cooldown_passed: bool,
    conversation_style: str,
    wants_title: bool,
    last_mani_text: str | None = None,
    nickname: str | None = None,
    name_said_before: bool = False,
    clarification_already_used: bool = False,
    offer_asked_about: bool = False,
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
    spoken = without_internal_words(text)
    if spoken != text:
        notes.append("dropped a sentence with internal words")
        text = spoken

    if clarification_already_used:
        # The client's one-time check, backstopped in code: [ctx] already told the model not
        # to ask again, this is what makes "never twice" true regardless.
        stripped = _without_clarification(text)
        if stripped != text:
            notes.append("removed a repeated one-time clarification")
            text = stripped

    if nickname:
        # Their name at most once in a conversation, never as the first word: observed in two
        # replies out of three. Only the name said to them is removed, never the sentence.
        named = _without_their_name(text, nickname, keep_one=not name_said_before)
        if named != text:
            notes.append("removed their name, already used or said first")
            text = named


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
        if prompt.library is not None:
            # A button pointing nowhere is worse than no button: it navigates the person
            # out of the conversation and into a section that does not exist. Case is
            # normalized the same way the shape is - checked loosely, stored exactly,
            # so a client navigating on this string always gets the canonical spelling.
            # An unknown value still meant the library - observed: "library", "default", a
            # topic phrase - so it opens the front page rather than losing the button.
            canonical_library = _LIBRARY_SECTIONS.get(prompt.library.strip().lower())
            if canonical_library is None:
                notes.append(
                    f"sent a button naming an unknown library section to home: {prompt.library}"
                )
                canonical_library = LibrarySection.HOME.value
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
            # The pending offer is exempt for the same reason it is exempt from the
            # already-offered check: re-showing it is not a new offer.
            pending_offer = (
                not framework_running
                and current_framework_id is not None
                and _normalize(prompt.technique) == _normalize(current_framework_id)
            )
            if not cooldown_passed and not pending_offer:
                notes.append(
                    f"dropped a technique offered before the cooldown passed: {prompt.technique}"
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

    # Tell me about this and Keep chatting answer an offer, and so does the question asking it.
    # Once the offer's own button is gone they answer nothing, so they go with it - the words
    # only when something is left to send.
    if any(p.technique for p in reply.prompts or []) and not any(p.technique for p in kept):
        orphaned = [p.label for p in kept if _is_offer_button(p)]
        if orphaned:
            kept = [p for p in kept if not _is_offer_button(p)]
            notes.append(f"dropped offer buttons left without their offer: {orphaned}")
        without = _BLANK_RUN.sub("\n\n", _OFFER_SENTENCE.sub("", text)).strip()
        if without and without != text:
            notes.append("removed the words of an offer whose button was dropped")
            text = without

    if len(kept) > MAX_PROMPTS:
        notes.append(f"trimmed {len(kept)} buttons to {MAX_PROMPTS}")
        kept = kept[:MAX_PROMPTS]

    # An offer is built here, not by the model: Mani's own part, which names the set, then the
    # client's permission question for the style. When they asked to hear more, the client's
    # description goes between the two, word for word (muhammad, 2026-10-09). A question
    # of the model's own asking that permission gives way to the client's. Any other question
    # means the offer shares a reply with something else, so its buttons are dropped: the
    # offer can come next turn, and a reply is never left asking two things at once.
    offered_id = next((p.technique for p in kept if p.technique), None)
    if offered_id is not None:
        part = _without_permission_question(text)
        if part != text:
            notes.append("replaced the model's permission question with the client's")
        if "?" in part:
            dropped = [p.label for p in kept if _is_offer_button(p)]
            kept = [p for p in kept if not _is_offer_button(p)]
            notes.append(f"dropped offer buttons under a question that is not the offer: {dropped}")
            # Its words go too, or the person reads an offer with nothing to answer it.
            without = _BLANK_RUN.sub("\n\n", _OFFER_SENTENCE.sub("", part)).strip()
            text = without or part
        else:
            # They asked about it, by Tell me more or a typed question: the answer carries the
            # client's description, and the offer comes back without Tell me more.
            asked = offer_asked_about or selected in EXPLAIN_LABELS
            text = _compose_offer(
                part, registry, offered_id, conversation_style, last_mani_text, describe=asked
            )
            kept = _offer_buttons(offered_id, explained=asked)

    framework_id: str | None = None
    phase: str | None = None
    if reply.state is not None:
        if reply.state.technique not in registry:
            notes.append(f"ignored state for unknown technique: {reply.state.technique}")
        elif framework_running and reply.state.technique != current_framework_id:
            # Every framework shares stage ids like somatic and closing, so the transition
            # check alone would let a reply record a framework the person never accepted.
            notes.append(
                f"ignored state for {reply.state.technique}, not the running one "
                f"({current_framework_id})"
            )
        else:
            framework_id = reply.state.technique
            # Accepting an offer this turn means the phase being left is the offering one,
            # whatever the stored row still says. What they told Mani before accepting may
            # answer the first stages too, so the reply may be asking one several stages in.
            previous = OFFERING if accepted_this_turn else current_phase
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

    at_the_end = framework_running and (phase or current_phase) in ENDING_STAGES
    if kept and not at_the_end and not any(p.technique for p in kept):
        notes.append(f"dropped buttons outside an offer or a framework's end: {[p.label for p in kept]}")
        kept = []

    title = clean_title(reply.title) if wants_title else None

    # Case and spacing are normalized before the check because a model reading a table of
    # names returns "Mirror and ask" far more often than it returns something off-list, and
    # dropping those would starve the anti-repetition loop this check exists to protect.
    style = reply.style
    if style is not None:
        shape = style.shape.strip().lower()
        if shape not in SHAPES:
            notes.append(f"dropped an off-list response shape: {style.shape}")
            style = None
        else:
            style = Style(shape=shape)

    return Repaired(
        text=text,
        prompts=kept,
        title=title,
        framework_id=framework_id,
        phase=phase,
        style=style,
        notes=notes,
    )
