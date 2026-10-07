# ABOUTME: Fixes what a model reply gets wrong, in code, without calling the model again.
# ABOUTME: Each check the reference answered with a regeneration is a rewrite here.

from __future__ import annotations

import re
from dataclasses import dataclass, field

from mani.chat import router, safety
from mani.chat.greeting import ACCEPT_LABEL, EXPLAIN_LABEL, KEEP_TALKING_LABEL
from mani.chat.techniques import Registry, moves_on_after
from mani.llm.schema import SHAPES, LibrarySection, Reply, SmartPrompt, Style, TechniqueState

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
# a framework. Everywhere else a button reads as a menu instead of a conversation (client,
# 2026-09-24). The greeting's style buttons and Chat More / Go to Library are written by the
# orchestrator after this runs, so they are not affected.
ENDING_STAGES = frozenset({"somatic_checkin", "somatic_practice", "grounding"})

# Keyed lowercase so a model's casing does not matter; valued at the canonical casing so
# whatever reaches the client to navigate on is always exactly what LibrarySection defines.
_LIBRARY_SECTIONS = {section.value.lower(): section.value for section in LibrarySection}

# The permission question an offer asks, in each style - the client's own wording
# (docs/specs/conversational-styles.md, the panic examples).
PERMISSION_QUESTIONS = {
    "direct": "Would you like to try it with me?",
    "supportive": "Would you like to try it together?",
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
    r"(?:(?:sequence|set|series) of questions|\b(?:a few|some) questions\b|structured approach"
    r"|would (?:you like|it help) to (?:try|work through|look at|go through)"
    r"|shall we (?:try|go through|look at))"
    r"[^.!?\n]*[.!?]?",
    re.IGNORECASE,
)

# The question a reply ends on, if it ends on one.
_LAST_QUESTION = re.compile(r"(?:^|(?<=[.!?])[ \t]+|(?<=\n))([^.!?\n]*\?)\s*$")

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
    # Extra turns the recorded stage has used: 1 after a counted hold, 0 after any move.
    holds: int = 0
    # How the framework ended, on the turn it moves into the body check in.
    ending: str | None = None


def _is_offer_button(prompt: SmartPrompt) -> bool:
    return bool(
        prompt.technique or prompt.decline or prompt.label.strip().lower() == EXPLAIN_LABEL.lower()
    )


def offered(reply: Reply, registry: Registry) -> str | None:
    """The framework a reply offers, if it carries an offer button for one that exists. An id the
    registry does not know is refused in apply, not here."""
    return next(
        (p.technique for p in reply.prompts or [] if p.technique and registry.get(p.technique)),
        None,
    )


def ruled_out(reply: Reply, user_texts: list[str], registry: Registry) -> str | None:
    """The framework a reply offers when what the person has said rules it out: the phrases a
    framework file lists under `never_offer_when_said` (early grief for Behavioral Activation).
    A prompt rule alone did not hold, so this is checked in code."""
    technique = offered(reply, registry)
    activation = registry.activations.get(technique) if technique else None
    if activation and router.vetoes(activation, user_texts):
        return technique
    return None


def offer_buttons(framework_id: str, *, explaining: bool) -> list[SmartPrompt]:
    """The client's choices under an offer, or the two that follow "Tell me more"."""
    accept = SmartPrompt(label=ACCEPT_LABEL, technique=framework_id)
    keep_talking = SmartPrompt(label=KEEP_TALKING_LABEL, decline=True)
    return [accept, keep_talking] if explaining else [accept, SmartPrompt(label=EXPLAIN_LABEL), keep_talking]


def names_framework(text: str, name: str) -> bool:
    """Whether the text says the framework's full name, ignoring case, a space and a hyphen being
    the same ("structured problem-solving" names Structured Problem Solving; "ACT" alone does not
    name ACT Choice Point)."""
    words = [re.escape(word) for word in re.split(r"[\s-]+", name.strip()) if word]
    return bool(words) and re.search(
        r"\b" + r"[\s-]+".join(words) + r"\b", text, re.IGNORECASE
    ) is not None


def _with_the_name(part: str, name: str | None, *, explaining: bool, notes: list[str]) -> str:
    """An offer and its explanation always say what the framework is called (spec 0011, AC-1,
    AC-2). Left out by the model, the name goes after an offer's sentence, before the client's
    permission question, and at the start of an explanation."""
    if not name or names_framework(part, name):
        return part
    notes.append(f"added the framework's name: {name}")
    sentence = f"It's called {name}."
    if not part:
        return sentence
    return f"{sentence} {part}" if explaining else f"{part} {sentence}"


def without_questions(text: str) -> str:
    """The text with every sentence that ends in a question mark taken out."""
    lines = [
        " ".join(s for s in _SENTENCE_END.split(line.strip()) if s and not s.endswith("?"))
        for line in text.split("\n")
    ]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def with_the_check_in(text: str, script: str) -> str:
    """The body check-in, sent word for word. The client's flow (2026-09-24) treats it as
    fixed content: Mani's reflection stays, and no question of its own does, so the check-in
    is the one question the person is asked."""
    if script in text:
        return text
    reflection = without_questions(text)
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


# An answer to "where do you feel that" is short. A longer message that happens to hold a place
# word is not one: "I can't go back to that meeting" names no place (spec 0011, AC-11).
PLACE_ANSWER_MAX_WORDS = 6


def place_answer(text: str) -> str | None:
    """The place a reply to the body question names: a tapped button sends its label, and a typed
    answer counts when it is short. A place wins over "nothing" ("nothing, just my head")."""
    if len(text.split()) > PLACE_ANSWER_MAX_WORDS:
        return None
    return named_place(text)


# Feeling nothing in the body, said as the whole answer. "Nothing helps" is not this.
_FEELS_NOTHING = re.compile(
    r"^\W*(nothing( really)?|not anything|no|i feel fine"
    r"|i (don'?t|do not|can'?t|cannot) (really )?feel anything)\W*$",
    re.IGNORECASE,
)


def feels_nothing(text: str) -> bool:
    return bool(_FEELS_NOTHING.search(text))


def decline_reply(stage: dict, style: str) -> str | None:
    """The client's line for someone who does not take up the body check in."""
    branch = next(
        (b for b in stage.get("if_unclear") or [] if "declines" in b.get("when", "")), None
    )
    return reply_for(branch, style) if branch else None


# What a person says to pass a running question over. A step nobody wants to answer is skipped
# rather than asked again (muhammad, 2026-10-06). No button offers it: under every question it made
# the framework read as a form (Lolly's review, spec 0011, AC-6).
_SKIPS_THE_STEP = re.compile(
    r"^\W*(skip|next|pass)\W*$"
    r"|\b(skip (this|that|it|this one|this question)|next question"
    r"|rather not answer|prefer not to answer|don'?t want to answer|do not want to answer"
    r"|no comment|can we skip)\b"
    # "move on" is a skip only when it is the whole message: "he said I should move on from
    # it" is them telling Mani something, not passing the question over.
    r"|^\W*(can we |let'?s |i want to )?move on\W*$",
    re.IGNORECASE,
)


def skips_the_step(text: str) -> bool:
    """Whether the person is passing over the question rather than answering it.

    Only a message that is the skip, or says it plainly: "pass" alone is a skip, "I'll pass on
    going tonight" is them answering.
    """
    return bool(_SKIPS_THE_STEP.search(text))


def reply_for(branch: dict, style: str) -> str:
    """A stage branch's reply: one text for every style, or the client's text for this one."""
    reply = branch["reply"]
    return reply[style] if isinstance(reply, dict) else reply


# The client's three lines for a person who brings another issue, corrects Mani or wants to stop.
# mani_base.md gives the model the same words.
CLIENT_LINES = (
    "Another issue is coming into this. Do you want to stay with the one we selected?",
    "I misunderstood what you meant. What would be more accurate?",
)

# How a framework may end, and how a person may say they feel after the practice (spec 0010).
ENDINGS = frozenset({"resolved", "pivoted", "stopped"})
FELT_AFTER = frozenset({"better", "mixed", "unchanged", "worse", "unsure"})

# The answers to the practice that mean it did not help. Mani says so and stops: no question, no
# further practice, no exercise (Lolly's review, spec 0011, AC-13). Her line, without the "I hear
# you" her style document lists as a formula.
NOT_HELPED = frozenset({"unchanged", "worse"})
NOT_HELPED_LINE = "This didn't help, so I'm going to stop here."


def known_value(value: str | None, allowed: frozenset[str]) -> str | None:
    """A model reported value from a closed set, normalised, or None when it is off the list."""
    cleaned = (value or "").strip().lower()
    return cleaned if cleaned in allowed else None

_PLACEHOLDER = re.compile(r"<[^>]*>")
_SENTENCE_END = re.compile(r"(?<=[.?!])\s")
MIN_KEY_CHARS = 20
MAX_KEY_CHARS = 40


def _match_key(text: str) -> str | None:
    """The words of an authored reply that show it was used: its longest fixed part, with any
    <placeholder> split out, normalised, cut to a whole word at 40 characters. None when no
    fixed part is 20 characters long, so such a reply cannot be recognised."""
    longest = max((safety.normalize(part) for part in _PLACEHOLDER.split(text)), key=len)
    if len(longest) < MIN_KEY_CHARS:
        return None
    if len(longest) <= MAX_KEY_CHARS:
        return longest
    cut = longest[:MAX_KEY_CHARS]
    return cut if longest[MAX_KEY_CHARS] == " " else cut.rsplit(" ", 1)[0]


def redirect_keys(stage: dict, style: str, *, client_lines: bool = True) -> list[str]:
    """What a reply carries when it leaves the stage question for a redirect: a branch that
    protects the person or leaves the framework (not one that asks again, nor one that uses
    the stage's extra turn), or one of the client's three lines."""
    keys = [
        _match_key(reply_for(branch, style))
        for branch in stage.get("if_unclear") or []
        if not branch.get("counted") and not branch.get("start_only")
    ]
    if client_lines:
        keys += [safety.normalize(_SENTENCE_END.split(line)[0]) for line in CLIENT_LINES]
    return [key for key in keys if key]


def carries_redirect(stage: dict, text: str | None, style: str, *, client_lines: bool = True) -> bool:
    """Whether a message uses a redirect of the stage, found anywhere in its words."""
    said = f" {safety.normalize(text or '')} "
    return any(f" {key} " in said for key in redirect_keys(stage, style, client_lines=client_lines))


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


# Where a practice was given, as the outcome table names it (spec 0010).
BODY_PLACES = {"Chest": "chest", "Head": "head", "Stomach": "stomach", "Somewhere else": "elsewhere"}


def practice_place(stage: dict, text: str | None, style: str) -> str | None:
    """The place whose practice a message gave, as the outcome table names it, or None when it
    gave no practice."""
    for label, place in BODY_PLACES.items():
        practice = practice_for(stage, label, style)
        if practice and text and practice[0][:30] in text:
            return place
    return None


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


CHECK_IN = "somatic_checkin"


def _ending_of(framework, stored: str, reported: str | None) -> str:
    """How a framework that moves to the body check in ended: what the model reported, or, when
    it reported nothing, resolved from the last question step and pivoted from an earlier one."""
    if reported:
        return reported
    last_question = framework.phases[framework.phase_index(CHECK_IN) - 1]
    return "resolved" if stored == last_question else "pivoted"


def _stage_after_a_reply(
    registry: Registry,
    framework_id: str,
    stored: str,
    state: TechniqueState | None,
    stored_holds: int,
    notes: list[str],
    *,
    ending: str | None,
    redirects: bool,
    redirected_before: bool,
    rephrase: bool = False,
    skipped: bool = False,
    asks_nothing: bool = False,
    their_question: bool = False,
) -> tuple[str, int, str | None]:
    """The step, hold count and ending to record once the person has replied to `stored`.

    The model judges when a step is done (spec 0010, AC-5): it may report a later step, never an
    earlier one, and may end the framework, which records the body check in. A reported step
    equal to `stored` is its one more attempt, counted once per step: a second records the
    next step. A reply that uses a redirect of the stage (`redirects`), or a hold right after
    Mani's own redirect (`redirected_before`), holds without counting.

    `skipped` is the person passing the question over. It moves to the next step whatever the
    reply reports, so a step is never asked again because the model did not notice the skip.

    `asks_nothing` is a reply with no question in it. At the last question step that is the
    conclusion stated (spec 0011, AC-8), so it ends the framework as resolved even when the model
    forgot to report an ending: a statement with nothing to answer would otherwise stall there.
    `their_question` is the person asking Mani something (AC-19): answering it holds the step
    without spending its one more attempt.
    """
    framework = registry.get(framework_id)
    following = framework.phases[framework.phase_index(stored) + 1]
    if ending is not None:
        notes.append(f"framework ended {ending} at {stored}")
        return CHECK_IN, 0, ending
    if skipped:
        notes.append(f"skipped {stored} at their request")
        if following == CHECK_IN:
            # The last question before the body check: skipping it ends the questions rather
            # than leaving a framework with nothing left to ask.
            return CHECK_IN, 0, _ending_of(framework, stored, None)
        return following, 0, None
    if following == CHECK_IN and asks_nothing and not redirects and not their_question:
        notes.append(f"a reply asking nothing at {stored}, recorded resolved")
        return CHECK_IN, 0, "resolved"
    if redirects:
        notes.append(f"redirect held at {stored}")
        return stored, stored_holds, None
    if rephrase:
        notes.append(f"held at {stored}")
        return stored, 1, None
    if state is None:
        notes.append(f"no state, recorded {following}")
        recorded = following
    else:
        transition = registry.validate_transition(framework_id, stored, state.step, moving_on=True)
        recorded = registry.clamp(framework_id, stored, state.step, moving_on=True)
        if not transition.ok:
            notes.append(f"corrected phase {state.step!r} to {recorded!r} ({transition.reason})")
        elif recorded == stored:
            if redirected_before:
                notes.append(f"redirect held at {stored}")
                return stored, stored_holds, None
            if their_question:
                notes.append(f"their question held at {stored}")
                return stored, stored_holds, None
            if stored_holds == 0:
                notes.append(f"held at {stored}")
                return stored, 1, None
            notes.append(f"hold limit at {stored}")
            recorded = following
    if recorded == CHECK_IN:
        return CHECK_IN, 0, _ending_of(framework, stored, None)
    return recorded, 0, None


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
    offer_allowed: bool,
    conversation_style: str,
    wants_title: bool,
    last_mani_text: str | None = None,
    explaining: bool = False,
    current_holds: int = 0,
    asked_again: bool = False,
    current_ending: str | None = None,
    skipped: bool = False,
    offer_decided: bool = False,
    required_offer: str | None = None,
    their_question: bool = False,
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
            if not offer_allowed and not pending_offer:
                notes.append(f"dropped a technique offered when no offer is allowed: {prompt.technique}")
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

    # The explain and keep talking buttons answer an offer, and so does the question asking it.
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

    # An offer is built here, not by the model: Mani's own part, then the client's permission
    # question for the style, with the client's three choices (spec 0010, AC-4). After "Tell me
    # more" the explanation stands alone with the two choices left. A question of the model's own
    # asking permission gives way to the client's. Any other question means the offer shares a
    # reply with something else, so it is dropped: the offer can come next turn, and a reply is
    # never left asking two things at once.
    offered_id = next((p.technique for p in kept if p.technique), None)

    if offer_decided:
        # Code decided whether a framework is offered (mani/chat/offer.py), so the model's own
        # choice is not consulted: an offer it failed to carry is added, one it invented goes.
        if required_offer is not None and offered_id != required_offer and registry.get(required_offer):
            kept = [p for p in kept if not p.technique and not _is_offer_button(p)]
            kept = kept + offer_buttons(required_offer, explaining=explaining)
            notes.append(f"added the offer this turn decided on: {required_offer}")
            offered_id = required_offer
        elif required_offer is None and offered_id is not None:
            dropped = [p.label for p in kept if _is_offer_button(p) or p.technique]
            kept = [p for p in kept if not p.technique and not _is_offer_button(p)]
            notes.append(f"dropped an offer this turn did not decide on: {dropped}")
            text = _BLANK_RUN.sub("\n\n", _OFFER_SENTENCE.sub("", text)).strip() or text
            offered_id = None

    if offered_id is not None:
        part = _without_permission_question(text)
        if part != text:
            notes.append("replaced the model's permission question with the client's")
        if explaining and "?" in part:
            # "Tell me more" is answered with no question, and keeps its two choices.
            part = without_questions(part)
            notes.append("removed a question from the explanation of an offer")
        name = registry.get(offered_id).name if registry.get(offered_id) else None
        if "?" in part and offer_decided and required_offer == offered_id:
            # The offer is this turn's decision, so the model's extra question gives way to it
            # rather than the other way round: trim the question, keep the offer.
            trimmed = _LAST_QUESTION.sub("", part).strip()
            if trimmed:
                notes.append("trimmed a question from the reply that carries the offer")
                part = trimmed
            part = _with_the_name(part, name, explaining=explaining, notes=notes)
            text = "\n\n".join(
                p for p in (part, PERMISSION_QUESTIONS[conversation_style]) if p
            )
            kept = offer_buttons(offered_id, explaining=explaining)
        elif "?" in part:
            dropped = [p.label for p in kept if _is_offer_button(p)]
            kept = [p for p in kept if not _is_offer_button(p)]
            notes.append(f"dropped offer buttons under a question that is not the offer: {dropped}")
            # Its words go too, or the person reads an offer with nothing to answer it.
            without = _BLANK_RUN.sub("\n\n", _OFFER_SENTENCE.sub("", part)).strip()
            text = without or part
        else:
            part = _with_the_name(part, name, explaining=explaining, notes=notes)
            text = part if explaining else "\n\n".join(
                p for p in (part, PERMISSION_QUESTIONS[conversation_style]) if p
            )
            kept = offer_buttons(offered_id, explaining=explaining)

    framework_id: str | None = None
    phase: str | None = None
    holds = 0
    ending = current_ending
    reported_ending = known_value(reply.ending, ENDINGS)
    state = reply.state
    if state is not None and state.technique not in registry:
        notes.append(f"ignored state for unknown technique: {state.technique}")
        state = None
    elif state is not None and framework_running and state.technique != current_framework_id:
        # Every framework shares stage ids like the body check, so the transition check alone
        # would let a reply record a framework the person never accepted.
        notes.append(
            f"ignored state for {state.technique}, not the running one "
            f"({current_framework_id})"
        )
        state = None

    # The person answered the step they were on, so the reply asks a later step or makes its one
    # more attempt, never an earlier step. Whatever the reply reports, a step is recorded: a lost
    # or garbled state must never keep a step on screen.
    moving_on = (
        framework_running
        and not accepted_this_turn
        and moves_on_after(registry.get(current_framework_id), current_phase)
    )
    if moving_on:
        framework_id = current_framework_id
        stage = registry.get(framework_id).stages.get(current_phase) or {}
        # They asked to hear the question again with the extra turn unused: the hold is recorded
        # here, and a client line is no redirect.
        rephrase = asked_again and current_holds == 0 and not skipped
        phase, holds, ending = _stage_after_a_reply(
            registry, framework_id, current_phase, state, current_holds, notes,
            ending=reported_ending,
            redirects=(
                not skipped
                and carries_redirect(stage, text, conversation_style, client_lines=not rephrase)
            ),
            redirected_before=carries_redirect(
                stage, last_mani_text, conversation_style, client_lines=False
            ),
            rephrase=rephrase,
            skipped=skipped,
            asks_nothing="?" not in text,
            their_question=their_question,
        )
    elif state is not None:
        framework_id = state.technique
        # Accepting an offer this turn means the phase being left is the offering one,
        # whatever the stored row still says. The reply asks the first step their words do not
        # already meet, which may be past the first.
        previous = "offering" if accepted_this_turn else current_phase
        transition = registry.validate_transition(framework_id, previous, state.step)
        phase = registry.clamp(framework_id, previous, state.step)
        if not transition.ok:
            notes.append(
                f"corrected phase {state.step!r} to {phase!r} ({transition.reason})"
            )
        if phase is None:
            framework_id = None
        elif phase == CHECK_IN and previous != CHECK_IN and framework_running:
            ending = reported_ending or "pivoted"

    at_the_end = framework_running and (phase or current_phase) in ENDING_STAGES
    if kept and not at_the_end and not any(p.technique for p in kept):
        notes.append(f"dropped buttons outside an offer or a framework's end: {[p.label for p in kept]}")
        kept = []

    if framework_running and (phase or current_phase) not in ENDING_STAGES and not kept:
        # A running question always carries a way past it, so nobody is held on a step they do
        # not want to answer. Not on the body stages: those already end the framework.
        kept = [SmartPrompt(label=SKIP_LABEL)]

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
        holds=holds,
        ending=ending,
    )
