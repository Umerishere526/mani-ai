# ABOUTME: The two checks code owns on a person's words: an imminent action, and what rules a framework out.
# ABOUTME: Veto phrases come from a framework's own activation data, so they are tested on the data's shape.

import pytest

from mani.chat.eligibility import urgent, vetoes


@pytest.mark.parametrize(
    "message",
    [
        "I am furious. I am about to send a message I will regret",
        "I already wrote the email",
        "I want to call her right now",
        "I am about to post everything publicly",
        "I keep typing and deleting",
        "I am about to lose it",
        "I need to confront her right now",
        "I am quitting today",
        "I am ending the relationship right now",
        "I am about to make this purchase even though I know I should wait",
        "I need help stopping myself",
    ],
)
def test_the_specifications_imminent_actions_are_urgent(message):
    assert urgent([message])


@pytest.mark.parametrize(
    "message",
    [
        "I want to tell him exactly what I think",
        "I want to say something that will hurt him",
        "I know I will regret it",
        "that is what I was about to say",
    ],
)
def test_planning_or_an_idiom_is_not_an_imminent_action(message):
    """Planning to say something is not about to say it; the model asks before offering a pause."""
    assert not urgent([message])


def test_only_the_two_most_recent_messages_can_make_it_urgent():
    messages = ["I am about to send it", "I sent nothing", "I am calmer now", "work was fine"]
    assert not urgent(messages)
    assert urgent(messages[:2])


def test_a_framework_lists_what_said_anywhere_rules_it_out():
    activation = {"never_offer_when_said": ["died"]}
    assert vetoes(activation, ["I'm sad that my dog died", "it feels empty"]) == ["died"]
    assert vetoes(activation, ["I have been in bed all day"]) == []
    # whole words: a phrase is not found inside a longer word
    assert vetoes({"never_offer_when_said": ["grief"]}, ["a grievance at work"]) == []
