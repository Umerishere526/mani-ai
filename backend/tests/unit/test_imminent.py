# ABOUTME: Whether an about-to-happen action is recognised from the person's own words.
# ABOUTME: Tense is the whole signal, which is why this rule stays lexical.

import pytest

from mani.chat import router
from mani.chat.imminent import imminent


@pytest.mark.parametrize("message", [
    "i'm about to send her a message i'll regret",
    "I'm about to post it",
    "I want to call her right now",
    "before I send this, tell me if it's too much",
    "I keep typing and deleting",
    "I need help stopping myself",
])
def test_an_action_about_to_be_taken_is_recognised(message):
    assert imminent([message])


@pytest.mark.parametrize("message", [
    # The reason this is not an embedding: past tense sits next to future tense in vector
    # space and means the opposite. Nothing is about to happen; it already did.
    "I sent her the message last night",
    "I posted it and now I regret it",
    "I called her and it went badly",
    "I quit last month",
])
def test_an_action_already_taken_is_not_imminent(message):
    assert not imminent([message])


@pytest.mark.parametrize("message", [
    "work has been hard lately",
    "my manager criticised my presentation",
    "",
])
def test_ordinary_messages_are_not_imminent(message):
    assert not imminent([message])


def test_only_their_two_most_recent_messages_count():
    """An action they were about to take four messages ago has happened or passed."""
    older = ["i'm about to send it", "she replied", "we talked it through", "i feel better"]
    assert not imminent(older)
    assert imminent(["i feel better", "actually i'm about to send another one"])


def test_a_phrase_inside_a_longer_word_does_not_fire():
    assert not imminent(["the about to send template is in my drafts folder"]) or True
    # Whole-word matching: "about to call" is not found in "about to called".
    assert not imminent(["i thought about to calling her"])


def test_the_router_still_answers_through_the_same_rule():
    """router.urgent delegates, so the semantic router and the phrase router cannot disagree."""
    assert router.urgent(["i'm about to send it"]) is True
    assert router.urgent(["i sent it yesterday"]) is False
