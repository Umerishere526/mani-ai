# ABOUTME: Fixes what a model reply gets wrong, in code, without calling the model again.
# ABOUTME: Each check the reference answered with a regeneration is a rewrite here.

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

from mani.chat.greeting import (
    KEEP_CHATTING_LABEL,
    TELL_ME_MORE_LABEL,
    TRY_IT_LABEL,
)
from mani.chat.techniques import OFFERING, Registry
from mani.llm.schema import Moment, Offer, Reply, Slots, SmartPrompt
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
    r"\bframework[_ ]id\b|\bmay_check\b|\bcheck_answer\b|\bheading_toward\b"
    r"|\bframework index\b|\bcooldown\b|\[/?ctx\]",
    re.IGNORECASE,
)
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+")


# A dash used as punctuation: an em dash, or an en dash with a space on either side (an en dash between two digits is a
# range and is left alone). The client asked for none in what Mani says (2026-10-30 and 2026-11-03: they kept coming
# back however the prompt asked), so code takes them out of every reply the model writes, and reply_checks still counts
# them in the draft.
_DASH = re.compile(r"\s*\u2014\s*|\s+\u2013\s+|\s+\u2013(?=\S)|(?<=\S)\u2013\s+")
# The words that open a new sentence after a dash: "You weren't asked—you were told" reads best as two sentences.
_STARTS_A_SENTENCE = frozenset({
    "i", "i'm", "it", "it's", "that", "that's", "this", "there", "there's", "you", "you're", "you've", "they",
    "they're", "we", "we're", "she", "he", "what", "maybe",
})
_WORD = re.compile(r"[A-Za-z']+")


def _sentence_after(rest: str) -> bool:
    """Whether the words after a dash are a full sentence of their own: they open as one, and run on for at least four
    words before the next stop or the end, with no other dash in between."""
    words = _WORD.findall(re.split(r"[.!?\u2014\u2013]", rest, maxsplit=1)[0])
    return len(words) >= 4 and words[0].lower() in _STARTS_A_SENTENCE


def without_dashes(text: str) -> str:
    """The reply with each dash used as punctuation replaced: a full stop when what follows is a sentence of its own,
    otherwise a comma. A dash at the very end becomes a full stop; one right before other punctuation is dropped."""
    out: list[str] = []
    rest = text
    while (found := _DASH.search(rest)) is not None:
        before, rest = rest[: found.start()], rest[found.end():]
        if not rest.strip() and before and before[-1] not in ".!?\n":
            out.append(f"{before}.")
            continue
        if not rest or rest[0] in ".,;:!?)\n" or not before or before[-1] in "\n.!?(":
            out.append(before)
            continue
        before = before.rstrip(",;:")
        if _sentence_after(rest) and not before.endswith(","):
            out.append(f"{before}. ")
            rest = rest[0].upper() + rest[1:]
        else:
            out.append(f"{before}, ")
    return "".join(out) + rest


def without_sentences(text: str, drop: Callable[[str], bool]) -> str:
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
    return without_sentences(text, lambda s: bool(_INTERNAL_WORDS.search(s)))


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
    # The framework and phase to record, set by the walk and the body route; never by the reply.
    framework_id: str | None = None
    phase: str | None = None
    # What was corrected, for the log and for a metric on how often the model needs it.
    notes: list[str] = field(default_factory=list)
    # Why the reply's offer could not be made, when it carried one; the model's text went instead.
    offer_dropped: str | None = None


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


def under(text: str, options: str | None) -> str:
    """The model's own question with its possibilities on the line under it, as a question that ends in ?.
    Text that asks nothing is left as it is."""
    cleaned = " ".join((options or "").split())
    if not cleaned or "?" not in text:
        return text
    return f"{text}\n\n{cleaned if cleaned[-1] in '.!?' else cleaned + '?'}"


def reply_for(branch: dict, style: str) -> str:
    """A stage branch's reply: one text for every style, or the client's text for this one."""
    reply = branch["reply"]
    return reply[style] if isinstance(reply, dict) else reply


def _offering(framework: Framework | None, key: str, style: str) -> str | None:
    """One of the client's offering texts for a framework, in one style, when it has one."""
    if framework is None:
        return None
    return (((framework.stages or {}).get(OFFERING) or {}).get(key) or {}).get(style)


def offer_template(framework: Framework | None, style: str) -> str | None:
    """The client's whole offer for a framework in one style, slots still open: the style's
    template, then the permission question."""
    template = _offering(framework, "offer", style)
    if template is None:
        return None
    return f"{template}\n\n{PERMISSION_QUESTION}"


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


def offer_framework(heading_toward: str | None, registry: Registry) -> str | None:
    """The set an offer is for: the one the reply heads toward when it is active, otherwise the
    only active set when there is just one, otherwise none (spec 0006, AC-8)."""
    if heading_toward in registry:
        return heading_toward
    return registry.ids[0] if len(registry) == 1 else None


def _offer_text(
    offer: Offer, framework_id: str | None, registry: Registry, style: str, *,
    confirmed: bool, feeling: str | None,
) -> tuple[str | None, str | None]:
    """The client's offer for the set, with its slots filled, the feeling they named standing in
    for an empty going_through. Otherwise None and why it could not be made."""
    framework = registry.get(framework_id)
    template = offer_template(framework, style)
    whole, _ = template_slots(template) if template else (None, None)
    going_through = offer.going_through if _slot_value(offer.going_through) else feeling
    if not confirmed:
        reason = "no yes to the check"
    elif framework is None:
        reason = "no framework"
    elif template is None:
        reason = "no template"
    elif not _slot_value(going_through):
        reason = "no going_through"
    elif whole and not _slot_value(offer.lead_line, sentence=True):
        reason = "no lead_line"
    else:
        return render_template(template, lead_line=offer.lead_line, slot=going_through), None
    return None, reason


# A body check-in the model offers on its own, in its own words (the career chat, 2026-11-03: "Would you like to do a
# brief body check-in now, or skip it?" inside E, then the client's own question once E ended).
# Only a check-in: a stage may still ask what they notice in their body.
_BODY_OFFER = re.compile(
    r"\b(?:body|physical(?:ly)?)\b[^?]*\bcheck(?:[- ]?in|ing in)\b"
    r"|\bcheck(?:[- ]?in|ing in)\b[^?]*\b(?:body|physical(?:ly)?)\b",
    re.IGNORECASE,
)


def without_body_offer(text: str) -> str:
    """The text without a question that offers a body check-in. Only code sends the check-in, when the questions
    end."""
    return without_sentences(text, lambda s: "?" in s and bool(_BODY_OFFER.search(s)))


def without_last_question(text: str) -> str:
    """The text without its closing question, or as it is when it ends on none."""
    match = _LAST_QUESTION.search(text)
    return text[: match.start(1)].rstrip() if match else text.rstrip()


def transition_offer(
    text: str, offer, heading_toward: str | None, registry: Registry, style: str, *,
    feeling: str | None,
) -> tuple[str | None, list[SmartPrompt], str | None, str | None]:
    """The chat's move to the set of questions, with no check before it (the client meeting, 2026-11-03): the
    client's offer, its slots filled, and its buttons. A style whose template opens with a line of the model's own
    sends that line in place of the text; otherwise the text's acknowledgment, its question dropped, goes first.
    Returns the text, the buttons, the set, and why no offer could be made, when none could."""
    framework_id = offer_framework(heading_toward, registry)
    # The style's own offer shape, read into the full one: a style without a lead line has no such field.
    filled = Offer.model_validate(offer.model_dump()) if offer is not None else Offer()
    said, dropped = _offer_text(filled, framework_id, registry, style, confirmed=True, feeling=feeling)
    if said is None:
        return None, [], None, dropped
    whole, _ = template_slots(offer_template(registry.get(framework_id), style) or "")
    if whole is None and (lead := without_last_question(text)):
        said = f"{lead}\n\n{said}"
    return said, offer_buttons(framework_id, explained=False), framework_id, None


def _sentence(value: str | None, end: str = ".") -> str:
    """A line of the model's own as a sentence: on one line, ending in punctuation. One that ends on a comma or a
    semicolon is left as it is."""
    cleaned = " ".join((value or "").split())
    return cleaned if not cleaned or cleaned[-1] in ".!?,;" else cleaned + end


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
    confirmed: bool,
    conversation_style: str,
    wants_title: bool,
    guarded: bool = False,
    nickname: str | None = None,
    name_said_before: bool = False,
    feeling: str | None = None,
    chat_text: bool = False,
) -> Repaired:
    """Everything wrong with a reply that can be fixed without asking again, and the client's
    offer when they said yes to Mani's check (`confirmed`). `chat_text` is Mani's own text before a
    framework, which goes out with the model's own line breaks and none added (muhammad, 2026-10-26).

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

    if nickname:
        # Their name at most once in a conversation, never as the first word: observed in two
        # replies out of three. Only the name said to them is removed, never the sentence.
        named = _without_their_name(text, nickname, keep_one=not name_said_before)
        if named != text:
            notes.append("removed their name, already used or said first")
            text = named

    # The offer is the client's template with the model's slots in it, made only on a yes to the
    # check; the model's own text is what goes when it cannot be made (spec 0006, AC-1, AC-8).
    prompts: list[SmartPrompt] = []
    offer_dropped: str | None = None
    if moment is Moment.CHECK_OPEN and (confirmed or reply.offer is not None) and not guarded:
        framework_id = offer_framework(reply.heading_toward, registry)
        offer, offer_dropped = _offer_text(
            reply.offer or Offer(), framework_id, registry, conversation_style,
            confirmed=confirmed, feeling=feeling,
        )
        if offer is not None:
            text = offer
            prompts = offer_buttons(framework_id, explained=False)

    # The options for answering the question go on a line of their own under it. They are the model's
    # words in a field of their own, so the model has to write them, and code owns where they go. An
    # offer is the client's order and carries none.
    options = _sentence(reply.options, "?")
    if options and chat_text and not prompts:
        text = f"{text}\n\n{options}"

    title = clean_title(reply.title) if wants_title else None

    return Repaired(
        text=text,
        prompts=prompts,
        title=title,
        notes=notes,
        offer_dropped=offer_dropped,
    )
