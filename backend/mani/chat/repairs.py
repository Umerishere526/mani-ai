# ABOUTME: Fixes what a model reply gets wrong, in code, without calling the model again.
# ABOUTME: Each check the reference answered with a regeneration is a rewrite here.

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

from mani.chat.greeting import (
    CLARIFICATION_QUESTIONS,
    KEEP_CHATTING_LABEL,
    TELL_ME_MORE_LABEL,
    TRY_IT_LABEL,
)
from mani.chat.techniques import OFFERING, Registry
from mani.llm.schema import SHAPES, Moment, Offer, Reply, Slots, SmartPrompt, Style
from mani.models.rows import Framework

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

# The permission question an offer asks. The client's ABCDE document asks it the same way in all
# three styles (2026-10-09).
PERMISSION_QUESTION = "Would you like to try it?"

# A slot in one of the client's templates: `<what goes here, in the client's words>`.
_SLOT = re.compile(r"<([^<>]+)>")
_QUOTES = "\"'“”‘’"
_TRAILING = ".,;:!?"

# The question a reply ends on, if it ends on one.
_LAST_QUESTION = re.compile(r"(?:^|(?<=[.!?])[ \t]+|(?<=\n))([^.!?\n]*\?)\s*$")



# The system's own words, which a person must never read.
_INTERNAL_WORDS = re.compile(
    r"\bframework[_ ]id\b|\boffer_window\b|\bheading_toward\b"
    r"|\bframework index\b|\bcooldown\b|\[/?ctx\]",
    re.IGNORECASE,
)
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+")


def _without_sentences(text: str, drop: Callable[[str], bool]) -> str:
    """The text with every sentence `drop` picks removed, paragraph by paragraph. Unchanged,
    spacing included, when it picks none."""
    paragraphs = []
    dropped = False
    for paragraph in text.split("\n\n"):
        sentences = _SENTENCE_BREAK.split(paragraph)
        kept = [s for s in sentences if not drop(s)]
        dropped = dropped or len(kept) < len(sentences)
        if kept:
            paragraphs.append(" ".join(kept))
    return "\n\n".join(paragraphs) if dropped else text


def without_internal_words(text: str) -> str:
    """The text with every sentence that carries the system's own words dropped."""
    return _without_sentences(text, lambda s: bool(_INTERNAL_WORDS.search(s)))


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
    # Why the reply's offer could not be made, when it carried one; the model's text went instead.
    offer_dropped: str | None = None


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


# The client's place buttons under the "where" question, each with the body branch it answers.
PLACE_LABELS = {"Chest": "chest", "Head": "head", "Stomach": "stomach", "Somewhere else": "elsewhere"}
_PLACES = frozenset(PLACE_LABELS.values())
BODY_STAGES = ("somatic_checkin", "somatic_practice")

# Where in the body route each answer may come (spec 0003's transition table): the stored phase,
# the framework's closing, or `retiring`, the turn after the practice. Anywhere else it is ignored.
_ANSWERED_AT = {
    **{place: {"closing", "somatic_checkin", "somatic_practice"} for place in _PLACES},
    "no_place": {"somatic_checkin", "somatic_practice"},
    "agreed": {"somatic_checkin"},
    "declined": {"somatic_checkin", "somatic_practice"},
    "acting": {"closing", "somatic_checkin"},
    "pain": {"closing", "somatic_checkin", "somatic_practice"},
    "returned": {"retiring"},
}


def reply_for(branch: dict, style: str) -> str:
    """A stage branch's reply: one text for every style, or the client's text for this one."""
    reply = branch["reply"]
    return reply[style] if isinstance(reply, dict) else reply


def first_sentence(text: str) -> str:
    """The reply's opening sentence: what Mani acknowledges before it asks."""
    match = re.match(r"\s*(.+?[.!?])(?:\s|$)", text, re.DOTALL)
    return match.group(1) if match else text


def body_branch(stages: dict, branch_id: str) -> dict | None:
    """The body route branch with this id, from either of its two stages."""
    return next(
        (b for stage in BODY_STAGES for b in (stages.get(stage) or {}).get("if_unclear") or []
         if b.get("id") == branch_id),
        None,
    )


def body_answer_fits(body: str, at: str, style: str) -> bool:
    """Whether the reply's body value can come where the route is. Agreeing to notice answers only
    the supportive check-in, the one that asks whether they would like to."""
    return at in _ANSWERED_AT.get(body, ()) and (body != "agreed" or style == "supportive")


@dataclass(frozen=True)
class BodyReply:
    text: str
    labels: list[str]
    phase: str
    handoff: bool = False


def body_reply(body: str, at: str, stages: dict, style: str, text: str) -> BodyReply:
    """The client's reply for an answer that fits where the body route is: the branch's own text,
    or Mani's first sentence then the client's question. A decline after the place question has
    no client line, so the model's text goes."""
    branch = body_branch(stages, body)
    client = reply_for(branch, style) if branch else text
    practice = "somatic_practice"
    if body == "no_place":
        ask = ((stages.get(practice) or {}).get("ask") or {}).get(style) or client
        return BodyReply(with_the_check_in(first_sentence(text), ask), list(PLACE_LABELS), practice)
    if body == "agreed":
        return BodyReply(with_the_check_in(first_sentence(text), client), [], "somatic_checkin")
    if body == "declined":
        return BodyReply(client if at == "somatic_checkin" else text, [], practice, handoff=True)
    return BodyReply(client, [], practice, handoff=body in ("acting", "returned"))


def _offering(framework: Framework | None, key: str, style: str) -> str | None:
    """One of the client's offering texts for a framework, in one style, when it has one."""
    if framework is None:
        return None
    return (((framework.stages or {}).get(OFFERING) or {}).get(key) or {}).get(style)


def offer_template(framework: Framework | None, style: str) -> str | None:
    """The client's whole offer for a framework in one style, slots still open: the style's
    template, the permission question, then the framework's steps when it lists them."""
    template = _offering(framework, "offer", style)
    if template is None:
        return None
    steps = ((framework.stages or {}).get(OFFERING) or {}).get("steps")
    return "\n\n".join(part for part in (template, PERMISSION_QUESTION, steps) if part)


def template_slots(template: str) -> tuple[str | None, str | None]:
    """What a client template's slots ask for: a whole first line that is one slot, and the
    first slot inside a sentence. Either is None when the template has no such slot."""
    first, _, rest = template.partition("\n")
    whole = _SLOT.fullmatch(first.strip())
    inline = _SLOT.search(rest if whole else template)
    return (whole.group(1) if whole else None), (inline.group(1) if inline else None)


def _slot_value(value: str | None, *, sentence: bool = False) -> str:
    """A slot value as it goes into the template: one line, its own case, without the quotes
    around it, and without trailing punctuation unless it is a whole sentence."""
    cleaned = " ".join((value or "").split())
    for _ in range(2):
        if not sentence:
            cleaned = cleaned.rstrip(_TRAILING).rstrip()
        if len(cleaned) >= 2 and cleaned[0] in _QUOTES and cleaned[-1] in _QUOTES:
            cleaned = cleaned[1:-1].strip()
    return cleaned


def render_template(template: str, *, lead_line: str | None, slot: str | None) -> str | None:
    """The client's template word for word with its slots filled, or None when a slot it needs
    is empty. A whole first line slot takes `lead_line`; every slot inside a sentence takes
    `slot`, the same value each time."""
    whole, inline = template_slots(template)
    head, rest = (None, template)
    if whole is not None:
        head = _slot_value(lead_line, sentence=True)
        if not head:
            return None
        rest = template.partition("\n")[2]
    if inline is not None:
        value = _slot_value(slot)
        if not value:
            return None
        rest = _SLOT.sub(lambda _: value, rest)
    return f"{head}\n{rest}" if head is not None else rest


def slots_for(registry: Registry, style: str, offered_id: str | None) -> Slots:
    """What the slots ask for in this style: an offer's from the first set with an offer template,
    and Keep chatting's from the set on the open offer."""
    offer = next(
        (t for fid in registry.ids if (t := _offering(registry.get(fid), "offer", style))), None
    )
    lead_line, going_through = template_slots(offer) if offer else (None, None)
    keep = _offering(registry.get(offered_id), "keep_chatting", style)
    return Slots(
        going_through=going_through,
        lead_line=lead_line,
        their_words=template_slots(keep)[1] if keep else None,
    )


def _offer_text(
    offer: Offer, framework_id: str | None, registry: Registry, style: str, *,
    may_offer: bool, finished_framework_id: str | None,
) -> tuple[str | None, str | None]:
    """The client's offer for the set the reply heads toward, with its slots filled. Otherwise
    None and why it could not be made."""
    framework = registry.get(framework_id)
    template = offer_template(framework, style)
    whole, _ = template_slots(template) if template else (None, None)
    if not may_offer:
        reason = "the window is closed"
    elif framework is None:
        reason = "unknown framework" if framework_id else "no framework"
    elif framework.id == finished_framework_id:
        reason = "they just finished it"
    elif template is None:
        reason = "no template"
    elif not _slot_value(offer.going_through):
        reason = "no going_through"
    elif whole and not _slot_value(offer.lead_line, sentence=True):
        reason = "no lead_line"
    else:
        return render_template(template, lead_line=offer.lead_line, slot=offer.going_through), None
    return None, reason


def keep_chatting(framework: Framework | None, style: str, their_words: str | None) -> str | None:
    """The client's Keep chatting question with their words in its slot, or None without them."""
    template = _offering(framework, "keep_chatting", style)
    return render_template(template, lead_line=None, slot=their_words) if template else None


def explanation(framework: Framework, style: str) -> str:
    """The client's answer to Tell me more in this style, then the permission question."""
    explained = _offering(framework, "explain", style) or " ".join(framework.summary.split())
    return f"{explained}\n\n{PERMISSION_QUESTION}"


def offer_buttons(framework_id: str, *, explained: bool) -> list[SmartPrompt]:
    """The client's buttons under an offer. Once they have tapped Tell me more they have been
    told, so the offer comes back with the other two."""
    buttons = [SmartPrompt(label=TRY_IT_LABEL, technique=framework_id)]
    if not explained:
        buttons.append(SmartPrompt(label=TELL_ME_MORE_LABEL))
    buttons.append(SmartPrompt(label=KEEP_CHATTING_LABEL, decline=True))
    return buttons


def apply(
    reply: Reply,
    registry: Registry,
    *,
    moment: Moment,
    may_offer: bool,
    finished_framework_id: str | None,
    current_framework_id: str | None,
    current_phase: str | None,
    accepted_this_turn: bool,
    framework_running: bool,
    conversation_style: str,
    wants_title: bool,
    guarded: bool = False,
    nickname: str | None = None,
    name_said_before: bool = False,
    clarification_already_used: bool = False,
) -> Repaired:
    """Everything wrong with a reply that can be fixed without asking again, and the client's
    offer when the reply makes one.

    The implementation this replaces answered each of these by re-calling the provider,
    up to six extra generations for one user message. They are all deterministic checks
    on text the model already produced, so they are corrections, not retries. `guarded` is a
    safety concern this turn: no client text is rendered from the reply's fields.
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

    # The offer is the client's template with the model's slots in it, for the set the reply
    # heads toward; the model's own text is what goes when it cannot be made (AC-3).
    prompts: list[SmartPrompt] = []
    offer_dropped: str | None = None
    if moment is Moment.CHATTING and reply.offer is not None and not guarded:
        offer, offer_dropped = _offer_text(
            reply.offer, reply.heading_toward, registry, conversation_style,
            may_offer=may_offer, finished_framework_id=finished_framework_id,
        )
        if offer is not None:
            text = offer
            prompts = offer_buttons(reply.heading_toward, explained=False)

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
        prompts=prompts,
        title=title,
        framework_id=framework_id,
        phase=phase,
        style=style,
        notes=notes,
        offer_dropped=offer_dropped,
    )
