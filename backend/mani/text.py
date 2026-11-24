# ABOUTME: Cleans what a person typed before anything reads it: invisible characters, odd spaces and control codes go.
# ABOUTME: Also strips a stored context block from old messages and catches Mani's last reply sent back.

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

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


_CTX_BLOCK = re.compile(r"^\[ctx\].*?\[/ctx\]\s*", re.DOTALL)
# A message this close to Mani's last reply is that reply sent back, not an answer to it. Long enough that "yes",
# "okay" or a short phrase of Mani's they repeat is never caught (the friend chat, 2026-11-04).
COPY_SHARE = 0.9
COPY_MIN_CHARS = 40
# Words of their own beyond this many make it an answer however much of Mani's reply came with them, so it is read
# like any message: a pasted reply with "I took all my pills" added was answered with the fixed line (2026-11-20).
COPY_ADDED_WORDS = 2


def strip(content: str) -> str:
    """Remove a context block from stored text: some stored messages were saved with one prefixed, and nothing written
    now contains one."""
    return _CTX_BLOCK.sub("", content, count=1)


def _plain(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9']+", text.casefold().replace("\u2019", "'")))


def copies_last_reply(content: str, last_reply: str | None) -> bool:
    """Whether their message is Mani's last reply sent back, as a copy and paste would."""
    theirs = _plain(content)
    if last_reply is None or len(theirs) < COPY_MIN_CHARS:
        return False
    said = _plain(last_reply)
    if SequenceMatcher(None, theirs, said).ratio() < COPY_SHARE:
        return False
    words = theirs.split()
    shared = sum(block.size for block in SequenceMatcher(None, words, said.split()).get_matching_blocks())
    return len(words) - shared <= COPY_ADDED_WORDS
