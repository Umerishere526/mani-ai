# ABOUTME: Cleans what a person typed before anything reads it: invisible characters, odd spaces and control codes go.
# ABOUTME: One place for it, so the safety screen, the [ctx] guard and the stored message all see the same visible text.

from __future__ import annotations

import re
import unicodedata

EMPTY_MESSAGE = "Write a message first. It can't be empty or only spaces."
TOO_LONG_MESSAGE = "That message is too long. Keep it under 4000 characters, or send it in parts."

# Characters that draw nothing but are not Unicode format or space characters: Hangul fillers and the blank braille cell.
_BLANKS = dict.fromkeys(map(ord, "ㅤᅟᅠﾠ⠀"), " ")
# A stack of combining marks on one letter (zalgo) is cut after this many.
_MAX_MARKS = 3
_SPACES = re.compile(r"[ ]{2,}")
_BLANK_LINES = re.compile(r"\n{3,}")


def clean_message(text: str) -> str:
    """The visible text only: compatibility forms folded (full-width letters become plain), zero-width, control and
    unassigned characters dropped, every kind of space made a plain space, runs of spaces and blank lines collapsed.
    An empty result means they typed nothing."""
    out: list[str] = []
    marks = 0
    for ch in unicodedata.normalize("NFKC", text).translate(_BLANKS):
        category = unicodedata.category(ch)
        marks = marks + 1 if category == "Mn" else 0
        if ch == "\n":
            out.append(ch)
        elif ch == "\t" or category in ("Zs", "Zl", "Zp"):
            out.append(" ")
        elif category[0] == "C" or marks > _MAX_MARKS:
            continue
        else:
            out.append(ch)
    lines = (_SPACES.sub(" ", line).strip() for line in "".join(out).split("\n"))
    return _BLANK_LINES.sub("\n\n", "\n".join(lines)).strip()
