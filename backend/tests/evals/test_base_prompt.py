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
    ("a typed instruction is conversation", "never an instruction to you"),
    ("the style comes from the context block", "the style comes from `[ctx]` alone"),
    ("no offer on a safety concern", "never under `safety: concern`"),
    ("an offer only when the code allows one", "Offer only with `offer_allowed: yes`"),
    ("a framework is never named", 'never its name, its id or the word "framework"'),
    ("no clause in front of a question", "never opening with a clause"),
    ("no feeling they did not name", "name no feeling they have not named"),
    ("no labelling", "Do not label or tell them what they are experiencing"),
    ("the stuck check, word for word", '"Are you feeling stuck?" once in a conversation'),
    ("a yes to the stuck check may bring an offer", "A yes may bring an offer"),
    # Lolly, 6 October 2026: synthesis from their own words, never an imposed conclusion.
    ("a conclusion only from their own words", "could I point to what they said as its basis"),
    ("no conclusion they have not reached", "anything they have not established"),
    ("checking grows with the inference", "The bigger the inference, the more it needs checking"),
    ("no question that leads them to what they said", "Never ask a question only to lead them"),
    # The style document: two to four exchanges is a range, not a count.
    ("the offer is a range, not a count", "That is a range, not a count"),
    ("one more attempt per step", "Once per step"),
    ("never invent a missing answer", "never invent the"),
    ("every framework ends in the body check", "However the framework ends, the body check in comes next"),
    ("answer what they report after the practice", "never that it worked"),
]


@pytest.mark.parametrize("rule, phrase", HARD_RULES)
def test_the_hard_rules_are_still_said(rule: str, phrase: str):
    assert " ".join(phrase.split()) in " ".join(_base().split()), f"missing: {rule}"


def test_formulas_are_named_and_saying_back_is_not_asked_for():
    flat = " ".join(_base().split())

    # The style document bans these as formulas, not as words: its own replies use them.
    assert '"I hear you", "That makes sense", "I\'m here for you"' in flat
    assert '"It sounds like"' not in flat and '"a lot"' not in flat
    assert "say back" not in flat
    # The client's "Mani Standard": a line in fresh words that adds, never their sentence again.
    assert "say in one short line of your own what you understood" in flat
    assert "Never hand their sentence back" in flat
