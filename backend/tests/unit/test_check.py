# ABOUTME: Checks the reply check's guard rails: which replies it may touch, and which rewrites it may send, so a
# ABOUTME: rewrite that adds a question, loses a number or a drafted message, or grows is never sent.
from __future__ import annotations

from mani.chat import check

REPLY = "You expected her to back you, and she didn't. That's not much to ask of a friend."


def test_a_rewrite_that_only_takes_out_or_rewords_is_sent():
    assert check.acceptable(REPLY, "You expected her to back you, and she didn't.")


def test_a_rewrite_that_asks_grows_or_loses_help_or_a_draft_is_not():
    assert not check.acceptable(REPLY, "You expected her to back you. What did she say?")
    assert not check.acceptable(REPLY, REPLY + " " + REPLY)
    assert not check.acceptable("Please call 988 now. That must sting.", "That must hurt.")
    drafted = 'Send this: "Hi Sam, I need the heating repaired by Friday."'
    assert not check.acceptable(drafted, 'Send this: "Hi Sam, please repair the heating."')
    assert not check.acceptable(REPLY, "   ")
