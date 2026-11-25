# ABOUTME: Checks the reply repair's detection and guard rails: which broken rules code finds, and which repairs may be
# ABOUTME: sent, so a repair that adds a question, loses a number or a draft, grows, or leaves the question closed is not.
from __future__ import annotations

import pytest

from mani.chat import check
from mani.chat.reply import Question, Safety, TurnReply


def reply(text: str, ask: str = "", level: str = "none") -> TurnReply:
    return TurnReply(text=text, safety=Safety(level=level, about="themselves" if level != "none" else None), notes="",
                     question=Question(ask=ask))


@pytest.mark.parametrize(("text", "ask", "found"), [
    # muhammad's tester, 2026-11-25.
    ("Lost her.", "What does losing her mean: that she died, or that you aren't together anymore?", "a choice"),
    ("You told me about the trip.", "Is that something you've wondered about yourself too?", "yes or no"),
    ("Understanding and being upset can sit in the same person.", "What comes up for you?", "figure of speech"),
    ("That's the part with the weight in it.", "", "figure of speech"),
    ("You're not stuck on information.", "What matters most to you?", "reading said as fact"),
    ("She hasn't reached out.", "When a stretch goes by and she hasn't reached out, what happens in you?", "odd"),
])
def test_a_broken_rule_code_can_find_is_named_with_its_exact_words(text, ask, found):
    named = check.problems(reply(text, ask))
    assert len(named) == 1 and found in named[0]


def test_a_clean_reply_and_a_drafted_message_are_left_alone():
    assert check.problems(reply("You told me about the trip and her birthday.", "What comes up for you?")) == []
    draft = 'Send this: "Hi Sam, is the heating fixed yet, or should I call someone?"'
    assert check.problems(reply(draft, "How does that sound to you?")) == []


def test_a_safety_turn_is_never_repaired():
    assert not check.due(reply("Please call 988 now.", "Are you safe right now?", level="danger"),
                         settings=type("S", (), {"reply_check_enabled": True})())


def test_only_a_repair_that_changes_what_it_was_asked_to_is_sent():
    before = reply("Lost her. That's hard.", "Did she die, or did you break up?")
    assert check.acceptable(before, check.Repaired(text="Lost her. That's hard.", ask="What happened with her?"))
    assert not check.acceptable(before, check.Repaired(text="Lost her. That's hard.", ask="Did she leave?"))
    assert not check.acceptable(before, check.Repaired(text="Lost her. What happened?", ask="Who is she?"))
    assert not check.acceptable(before, check.Repaired(text="Lost her. " * 20, ask="Who is she?"))
    help_line = reply("Please call 988 if it gets worse. That stings.", "")
    assert not check.acceptable(help_line, check.Repaired(text="That hurts.", ask=""))


def test_a_repair_that_also_writes_its_question_into_the_text_keeps_it_only_as_the_question():
    """The tester's family chat (2026-11-25): the repair fixed the either/or question and also put it in the text, and
    the whole repair was discarded."""
    text = "It happens again and again.\n\nWhen you find out after everyone else, what hits you first?"
    assert check._without_question(text, "When you find out after everyone else, what hits you first?") == \
        "It happens again and again."
