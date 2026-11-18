# ABOUTME: The few things code does to a reply's words: dashes replaced, a title tidied, and the client's buttons at
# ABOUTME: each step of an offer. Everything else the model writes goes out as written.

from __future__ import annotations

import re

from mani.chat.greeting import (
    CODE_LABELS, EXAMPLE_LABEL, FEELINGS_LABELS, LEAD_IN_LABELS, TALK_MORE_FIRST_LABEL, start_label,
)
from mani.llm.schema import SmartPrompt
from mani.models.rows import Framework

MAX_TITLE_LENGTH = 100

# A dash used as punctuation: an em dash, or an en dash with a space on either side (an en dash between two digits is a
# range and is left alone). The client asked for none in what Mani says (2026-10-30 and 2026-11-03: they kept coming
# back however the prompt asked), so code takes them out of every reply the model writes.
_DASH = re.compile(r"\s*—\s*|\s+–\s+|\s+–(?=\S)|(?<=\S)–\s+")
# The words that open a new sentence after a dash: "You weren't asked—you were told" reads best as two sentences.
_STARTS_A_SENTENCE = frozenset({
    "i", "i'm", "it", "it's", "that", "that's", "this", "there", "there's", "you", "you're", "you've", "they",
    "they're", "we", "we're", "she", "he", "what", "maybe",
})
_WORD = re.compile(r"[A-Za-z']+")


def _sentence_after(rest: str) -> bool:
    """Whether the words after a dash are a full sentence of their own: they open as one, and run on for at least four
    words before the next stop or the end, with no other dash in between."""
    words = _WORD.findall(re.split(r"[.!?—–]", rest, maxsplit=1)[0])
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


def clean_title(title: str | None) -> str | None:
    """Tidy a title rather than refusing one that is slightly too long: quotes and a final full stop go, and it is cut
    at MAX_TITLE_LENGTH."""
    if not title:
        return None
    cleaned = title.strip().strip("\"'").rstrip(".")
    return cleaned[:MAX_TITLE_LENGTH].strip() or None


def lead_in_buttons() -> list[SmartPrompt]:
    """The client's three buttons under the lead-in; any of them shows the five steps."""
    return [SmartPrompt(label=label) for label in LEAD_IN_LABELS]


# A suggestion longer than this does not fit on a button.
MAX_SUGGESTION_LENGTH = 40


def suggestion_buttons(options: list[str]) -> list[SmartPrompt]:
    """The model's suggested answers as buttons: trimmed; blanks, repeats, ones too long for a button and ones named like
    a button of code's own dropped; at most three."""
    seen: set[str] = set()
    buttons = []
    for option in options:
        label = option.strip()
        key = label.lower()
        if (not label or len(label) > MAX_SUGGESTION_LENGTH or key in seen or key in CODE_LABELS
                or key.startswith("start ")):
            continue
        seen.add(key)
        buttons.append(SmartPrompt(label=label))
    return buttons[:3]


def feelings_buttons() -> list[SmartPrompt]:
    """The client's three answers to how they feel after the last stage."""
    return [SmartPrompt(label=label) for label in FEELINGS_LABELS]


def start_buttons(framework: Framework, *, with_example: bool) -> list[SmartPrompt]:
    """The buttons under the five steps, and under the example without its own button. Start carries the framework's
    id, so it starts only the offer still open."""
    buttons = [SmartPrompt(label=start_label(framework.name), technique=framework.id)]
    if with_example:
        buttons.append(SmartPrompt(label=EXAMPLE_LABEL))
    return [*buttons, SmartPrompt(label=TALK_MORE_FIRST_LABEL)]
