# ABOUTME: Fixes what a model reply gets wrong, in code, without calling the model again.
# ABOUTME: Each check the reference answered with a regeneration is a rewrite here.

from __future__ import annotations

import re
from difflib import SequenceMatcher
from dataclasses import dataclass, field

from mani.chat import safety
from mani.chat.greeting import CLARIFICATION_QUESTIONS, EXPLAIN_LABELS
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
        "empty", "heartbroken", "heavy", "numb", "painful", "scary",
        # The adjectival forms, which describe the situation rather than the person and are
        # the shape a capsule label usually takes: "It's frustrating", "It's exhausting".
        "depressing", "devastating", "draining", "embarrassing", "exhausting",
        "frustrating", "humiliating", "isolating", "overwhelming", "terrifying",
        "upsetting", "worrying",
        # Forms and neighbours that slipped through when the list was a fixed few dozen:
        # "That sounds incredibly stressful" named a feeling the person never did.
        "anxiety", "nervous", "nervousness", "tense", "tension", "worry", "worries",
        "stress", "stressful", "stressing", "dread", "dreading", "dreaded", "fear", "fears",
        "frightened", "frightening", "panic", "panicking", "overwhelm", "sadness", "unhappy",
        "anger", "annoyed", "annoying", "irritated", "irritating", "bitter", "jealous",
        "envious", "guilt", "shame", "shameful", "embarrassment", "humiliation", "loneliness",
        "isolation", "hopelessness", "despair", "despairing", "depression", "misery",
        "devastation", "grief", "grieving", "sorrow", "discouraged", "disheartened",
        "drained", "burnout", "burnt", "hollow", "confused", "confusing", "distress",
        "relieved", "relief", "calm", "happy", "happiness", "joy", "joyful", "excited",
        "proud", "grateful", "ecstatic", "thrilled", "terrible", "awful", "dreadful",
    }
)

# Scale and weight a reply may use only if the person put it there first: "if they did not
# describe the scale, neither do you".
SIZE_PHRASES = (
    "a lot", "so much", "weighing on you", "that is tough", "that's tough",
    "that is hard", "that's hard", "so exhausting", "must be so", "such a big",
    "really significant", "so heavy", "overwhelming", "burden", "carrying",
    "the weight of",
)

# Phrases that make Mani sound scripted. Mani never says them, whatever the person said.
STOCK_PHRASES = (
    "it sounds like", "it seems like", "i hear you", "that makes sense", "that makes total sense",
    "i am here with you", "i'm here with you", "i am here for you", "i'm here for you",
)

# Judgments a person may hold about themselves but must never be handed as a button to press.
# Observed live: a reply offered "I'm overthinking it" as a capsule.
SELF_JUDGMENTS = (
    "overthinking", "over thinking", "being dramatic", "too sensitive", "overreacting",
    "over reacting", "being silly", "being stupid", "my fault", "i'm weak", "i am weak",
    "i'm broken", "i am broken", "not enough", "being needy", "being difficult",
)

# Five: room for a choice in the person's own voice. Past that a label is becoming a sentence.
MAX_CAPSULE_WORDS = 5

# Where a reply may carry buttons besides an offer: the body check-in and the practice that ends
# a framework. Everywhere else a button reads as a menu instead of a conversation (client,
# 2026-09-24). The greeting's style buttons and Chat More / Go to Library are written by the
# orchestrator after this runs, so they are not affected.
ENDING_STAGES = frozenset({"somatic_checkin", "somatic_practice", "grounding"})

# Keyed lowercase so a model's casing does not matter; valued at the canonical casing so
# whatever reaches the client to navigate on is always exactly what LibrarySection defines.
_LIBRARY_SECTIONS = {section.value.lower(): section.value for section in LibrarySection}

# The permission question an offer asks, in each style - the client's own wording
# (docs/specs/conversational-styles.md), shortened only where it named one scenario.
PERMISSION_QUESTIONS = {
    "direct": "Would you like to try it with me?",
    "supportive": "Would it help to work through it together?",
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

WORD = re.compile(r"[a-z']+")


def words(text: str) -> set[str]:
    return set(WORD.findall(text.lower()))


_SUFFIXES = ("iness", "ness", "ment", "ied", "ful", "ing", "ed", "ion", "ly", "y")


def _stem(word: str) -> str:
    """A rough root, so a feeling word and its plain forms count as one: lonely and loneliness,
    stressed and stress, overwhelmed and overwhelming. Never merges two different feelings."""
    for _ in range(2):
        for suffix in _SUFFIXES:
            if word.endswith(suffix) and len(word) - len(suffix) >= 3:
                word = word[: -len(suffix)] + ("y" if suffix in ("iness", "ied") else "")
                break
    return word


def introduced_feelings(text: str, said: str) -> list[str]:
    """Feeling words in `text` that the person has not used. "MANI never introduces a feeling
    word the user did not use": their own word, or a plain form of it, may come back; a
    different feeling may not."""
    theirs = {_stem(w) for w in words(said)}
    return sorted(
        w for w in words(text) & FEELING_WORDS
        if _stem(w) not in theirs and not _misspelt_by_them(w, theirs)
    )


def introduced_size(text: str, said: str) -> list[str]:
    """Size and weight phrases in `text` that the person has not used."""
    lowered, theirs = text.lower(), said.lower()
    return [p for p in SIZE_PHRASES if re.search(rf"\b{re.escape(p)}\b", lowered) and p not in theirs]


def used_stock_phrases(text: str) -> list[str]:
    """Scripted phrases in `text`, in the order STOCK_PHRASES lists them."""
    lowered = text.lower().replace("\u2019", "'")
    return [p for p in STOCK_PHRASES if re.search(rf"\b{re.escape(p)}\b", lowered)]


def _skeleton(stem: str) -> str:
    """The consonants of a root with repeats collapsed: "emberess" and "embarrass" are both "mbrs"."""
    return re.sub(r"(.)\1+", r"\1", re.sub(r"[aeiou]", "", stem))


def _misspelt_by_them(word: str, theirs: set[str]) -> bool:
    """Whether they wrote this feeling word badly ("emberessed" for "embarrassed"): a reply that
    spells it right has not introduced it. Long words only, and close, so one feeling is never
    taken for another (sad and mad, lonely and lovely stay different; across the word list only
    burnout and burnt share a skeleton, and they are one feeling)."""
    stem = _stem(word)
    if len(stem) < 5:
        return False
    skeleton = _skeleton(stem)
    return any(
        len(other) >= 5
        and (
            SequenceMatcher(None, stem, other).ratio() >= 0.8
            or (len(skeleton) >= 4 and other[0] == stem[0] and _skeleton(other) == skeleton)
        )
        for other in theirs
    )


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


def reply_for(branch: dict, style: str) -> str:
    """A stage branch's reply: one text for every style, or the client's text for this one."""
    reply = branch["reply"]
    return reply[style] if isinstance(reply, dict) else reply


# The client's three lines for a person who brings another issue, corrects Mani or wants to stop.
# mani_base.md gives the model the same words.
CLIENT_LINES = (
    "Another issue is coming into this. Do you want to stay with the one we selected?",
    "I misunderstood what you meant. What would be more accurate?",
    "You want to stop here. Would you like to continue chatting?",
)

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


def _compose_offer(
    part: str, registry: Registry, framework_id: str, style: str, last_mani_text: str | None
) -> str:
    """Mani's part, the client's description, the client's question: one paragraph each.

    The description is left out when the last reply already showed it, which is the offer
    made again after they asked what it involves, or when the model wrote it itself.
    """
    framework = registry.get(framework_id)
    description = " ".join(framework.summary.split()) if framework and framework.summary else ""
    # Exactly once: not again when the last reply showed it, nor when the model wrote it anyway.
    already = " ".join(f"{last_mani_text or ''} {part}".split())
    if description and description in already:
        description = ""
    return "\n\n".join(p for p in (part, description, PERMISSION_QUESTIONS[style]) if p)


def _stage_after_a_reply(
    registry: Registry,
    framework_id: str,
    stored: str,
    state: TechniqueState | None,
    stored_holds: int,
    notes: list[str],
    *,
    redirects: bool,
    redirected_before: bool,
    rephrase: bool = False,
) -> tuple[str, int]:
    """The stage and hold count to record once the person has replied to `stored`.

    The stage after it, unless the reply holds. A reply that uses a redirect of the stage
    (`redirects`) holds whatever it reported, and so does a reported hold right after Mani's
    own redirect (`redirected_before`, because the follow up to one is worded afresh). A redirect
    is not counted. Any other hold is counted, allowed once per stage: a second records the
    next stage, the model having been told its extra turn was used.
    """
    framework = registry.get(framework_id)
    following = framework.phases[framework.phase_index(stored) + 1]
    if redirects:
        notes.append(f"redirect held at {stored}")
        return stored, stored_holds
    if rephrase:
        notes.append(f"held at {stored}")
        return stored, 1
    if state is None:
        notes.append(f"no state, recorded {following}")
        return following, 0
    transition = registry.validate_transition(framework_id, stored, state.step, moving_on=True)
    recorded = registry.clamp(framework_id, stored, state.step, moving_on=True)
    if not transition.ok:
        notes.append(f"corrected phase {state.step!r} to {recorded!r} ({transition.reason})")
        return recorded, 0
    if recorded != stored:
        return recorded, 0
    if redirected_before:
        notes.append(f"redirect held at {stored}")
        return stored, stored_holds
    if stored_holds == 0:
        notes.append(f"held at {stored}")
        return stored, 1
    notes.append(f"hold limit at {stored}")
    return following, 0


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
    cooldown_passed: bool,
    conversation_style: str,
    wants_title: bool,
    last_mani_text: str | None = None,
    nickname: str | None = None,
    name_said_before: bool = False,
    clarification_already_used: bool = False,
    current_holds: int = 0,
    asked_again: bool = False,
    skipped_stages: int = 0,
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


    theirs = words(said)
    introduced_in_text = introduced_feelings(text, said)
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
        if key in EXPLAIN_LABELS and any(p.technique for p in reply.prompts or []):
            # An offer has two buttons, Try it and Keep chatting (muhammad, 2026-09-24): the
            # offer's own words already say how the questions would help.
            notes.append(f"dropped an explain button from an offer: {label}")
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

    # An offer is built here, not by the model (muhammad, 2026-09-24): Mani's own part, then
    # the client's description of the questions word for word, so the person sees what they
    # would come away with, then the client's permission question for the style. A question
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
            text = _compose_offer(part, registry, offered_id, conversation_style, last_mani_text)

    framework_id: str | None = None
    phase: str | None = None
    holds = 0
    state = reply.state
    if state is not None and state.technique not in registry:
        notes.append(f"ignored state for unknown technique: {state.technique}")
        state = None
    elif state is not None and framework_running and state.technique != current_framework_id:
        # Every framework shares stage ids like somatic and closing, so the transition
        # check alone would let a reply record a framework the person never accepted.
        notes.append(
            f"ignored state for {state.technique}, not the running one "
            f"({current_framework_id})"
        )
        state = None

    # The person answered the stage they were on, so the reply is the next stage's question
    # or a hold on this one, never an earlier stage. Whatever the reply reports, a stage is
    # recorded: a lost or garbled state must never keep a stage on screen.
    moving_on = (
        framework_running
        and not accepted_this_turn
        and moves_on_after(registry.get(current_framework_id), current_phase)
    )
    if moving_on:
        framework_id = current_framework_id
        stage = registry.get(framework_id).stages.get(current_phase) or {}
        # They asked to hear the question again with the extra turn unused: the model was shown
        # only that question, so the hold is recorded here, and a client line is no redirect.
        rephrase = asked_again and current_holds == 0
        phase, holds = _stage_after_a_reply(
            registry, framework_id, current_phase, state, current_holds, notes,
            redirects=carries_redirect(stage, text, conversation_style, client_lines=not rephrase),
            redirected_before=carries_redirect(
                stage, last_mani_text, conversation_style, client_lines=False
            ),
            rephrase=rephrase,
        )
    elif state is not None:
        framework_id = state.technique
        # Accepting an offer this turn means the phase being left is the offering one,
        # whatever the stored row still says. What they told Mani before accepting
        # answers the first stage, so the reply may already be asking the second.
        previous = current_phase
        first = -1
        phases: list[str] = []
        if accepted_this_turn:
            known = registry.get(framework_id)
            phases = known.phases if known else []
            # Stages their earlier words answered are not asked, so the first open stage is
            # the one the reply is on, whatever it reports.
            first = phases.index("offering") + 1 + skipped_stages if "offering" in phases else -1
            previous = phases[first] if 0 < first < len(phases) else "offering"
        transition = registry.validate_transition(framework_id, previous, state.step)
        phase = registry.clamp(framework_id, previous, state.step)
        if skipped_stages and phase is not None and 0 < first < len(phases) and phases.index(phase) < first:
            phase = phases[first]
        if not transition.ok:
            notes.append(
                f"corrected phase {state.step!r} to {phase!r} ({transition.reason})"
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
        holds=holds,
    )
