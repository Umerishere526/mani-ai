# ABOUTME: Checks the two phrase rules the router keeps: an action about to happen, and words that rule a framework out.
# ABOUTME: Driven by the shipped framework content; the choice from facts is tested in test_framework_fit.py.

import pytest

from mani.chat.router import kept_facts, urgent, vetoes
from scripts.seed import FRAMEWORKS_DIR, parse_framework

# The shipped activation data, parsed by the seeder itself - the same structures that reach
# admin.frameworks and then Registry.activations at runtime.
ACTIVATIONS: dict[str, dict] = {
    f["id"]: f["activation"]
    for f in (parse_framework(path) for path in sorted(FRAMEWORKS_DIR.glob("*.md")))
}


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
def test_the_imminent_action_examples_are_urgent(message):
    """The specification's own imminent actions: time critical, so one mention is enough."""
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
def test_an_urge_or_an_idiom_with_no_action_about_to_happen_is_not_urgent(message):
    """Planning to say something is not about to say it; the facts decide those."""
    assert not urgent([message])


def test_only_the_two_most_recent_messages_make_it_urgent():
    assert urgent(["I am about to send it", "okay"])
    assert not urgent(["I am about to send it", "okay", "it is done now"])


def test_a_framework_lists_what_said_anywhere_rules_it_out():
    activation = ACTIVATIONS["behavioral_activation"]
    assert vetoes(activation, ["I'm sad that my dog died", "it feels empty"]) == ["died"]
    assert vetoes(activation, ["I have been in bed all day"]) == []
    # whole words: a phrase is not found inside a longer word
    assert vetoes({"never_offer_when_said": ["grief"]}, ["a grievance at work"]) == []


def test_a_kept_fact_carries_the_words_the_person_typed():
    kept = kept_facts(
        [("event", "the very next day i had an exam"), ("meaning", "idiot")],
        ["I went to a concert and the very next day I had an exam"],
    )
    assert kept.present == frozenset({"event"})
    assert kept.words == {"event": "the very next day i had an exam"}
