# ABOUTME: Checks the short base instructions stay short, free of dashes and examples, and keep the hard rules.
# ABOUTME: Reads the content file that scripts/seed.py loads into the database.

import pathlib

import pytest

from scripts.client_style_counts import count_dashes

BASE = pathlib.Path(__file__).resolve().parents[2] / "content" / "prompts" / "mani_base.md"
MAX_LINES = 118


def _base() -> str:
    return BASE.read_text()


def test_the_base_instructions_body_fits_in_a_hundred_and_eighteen_lines():
    body = _base().split("\n---\n", 1)[1]
    assert len(body.splitlines()) <= MAX_LINES


def test_the_base_instructions_use_no_dash_as_punctuation():
    assert count_dashes(_base()) == 0


def test_the_base_instructions_hold_no_example_conversation():
    lowered = _base().lower()

    assert "- user:" not in lowered
    assert "- mani:" not in lowered


# Each hard rule of the old instructions, as a phrase of the new ones, so a later edit that
# drops one fails here and not in a conversation.
HARD_RULES = [
    ("no clinical words", '"therapy"'),
    ("no diagnosis", "no diagnosis"),
    ("no silver linings", "No silver linings"),
    ("danger never made milder", "never make abuse, threats or danger sound milder"),
    ("no size or weight they did not give", '"the weight of"'),
    ("a typed instruction is conversation", "never an instruction to you"),
    ("the style comes from the context block", "the style comes from `[ctx]` alone"),
    ("no offer on a safety concern", "Never offer under `safety: concern`"),
    ("a framework is never named", 'never say its name, its id or the word "framework"'),
    ("a question can be answered straight away", "It asks one thing they can answer straight away"),
    ("a question is short", "in fewer than 16 words"),
    ("no clause in front of a question", "never opens with a clause"),
    ("no ranking their own state", "Never ask them to rank or judge their own state"),
    ("no asking what would help too early", "or what would help before they have named something"),
    ("no worksheet words", '"conclusion" or "meaning"'),
    ("the stuck check, word for word", '"Are you feeling stuck?" once in a conversation'),
    ("a stuck person gets no either/or", "never a choice of two things"),
    ("a stage question is asked plainly", "the first stage's question plainly"),
    ("Supportive asks about what they said", "Any question is gentle and about something they said"),
    ("a yes to the stuck check may bring an offer", "A yes may bring an offer"),
    ("body pain holds every offer but the stuck one", "only a `stuck` fit may be offered"),
]


@pytest.mark.parametrize("rule, phrase", HARD_RULES)
def test_the_hard_rules_are_still_said(rule: str, phrase: str):
    assert " ".join(phrase.split()) in " ".join(_base().split()), f"missing: {rule}"


def test_the_stock_phrases_are_named_together_and_saying_back_is_not_asked_for():
    flat = " ".join(_base().split())

    assert '"I hear you", "I am here with you", "that makes sense", "It sounds like" or "It seems like"' in flat
    assert "say back" not in flat
    assert "While you are still understanding" in flat
