# ABOUTME: Checks the safety screen fires on real risk and stays quiet on ordinary distress.
# ABOUTME: The precision test is the important one - over-firing locks someone out of the app.

import pytest

from mani.chat import crisis
from mani.chat.safety import Assessment, Category, Level, protocol_for, screen


@pytest.mark.parametrize(
    ("text", "category"),
    [
        ("I am going to kill myself tonight", Category.SUICIDE),
        ("i have already taken the pills", Category.OVERDOSE),
        ("I am afraid I am going to hurt him", Category.HARM_TO_OTHER),
        ("I'm going to hurt myself", Category.SELF_HARM),
        ("I can't keep myself safe", Category.CANNOT_STAY_SAFE),
    ],
)
def test_an_explicit_statement_is_a_crisis(text, category):
    result = screen(text)
    assert result.level is Level.CRISIS
    assert result.category is category


@pytest.mark.parametrize(
    "text",
    [
        "Everyone would be better off without me",
        "I have everything ready",
        "I do not think I will be here tomorrow",
        "He is outside, and I think he is going to hurt me",
    ],
)
def test_an_indirect_statement_asks_rather_than_locks(text):
    """The specification lists these verbatim and asks for clarification, not a lock.

    Locking here would take the conversation away from someone who may only have been
    describing how heavy the week felt."""
    result = screen(text)
    assert result.level is Level.CONCERN
    assert result.level is not Level.CRISIS


@pytest.mark.parametrize(
    "text",
    [
        "I have been feeling really depressed",
        "Everything feels hopeless right now",
        "I think I might be panicked about the deadline",
        "I am furious with my manager",
        "I cannot do this anymore",
        "Work is killing me",
        "My chest feels tight and my thoughts are racing",
    ],
)
def test_ordinary_distress_does_not_fire_at_all(text):
    """Named in the specification: "They should not automatically produce a crisis response."

    These are the exact words the document calls out, plus the panic-attack opener from the
    styles document, which must reach the frameworks rather than the crisis path."""
    assert screen(text).level is Level.NONE


def test_a_contraction_is_matched_the_same_as_its_expansion():
    assert screen("I can't keep myself safe").level is Level.CRISIS
    assert screen("I cannot keep myself safe").level is Level.CRISIS


def test_punctuation_does_not_hide_a_match():
    assert screen("I am going to... kill myself.").level is Level.CRISIS


def test_crisis_wins_when_both_levels_match():
    text = "Everyone would be better off without me. I am going to kill myself."
    result = screen(text)
    assert result.level is Level.CRISIS


def test_both_levels_stop_a_framework_and_none_does_not():
    assert Assessment(Level.CRISIS, Category.SUICIDE).blocks_framework
    assert Assessment(Level.CONCERN, Category.SUICIDE).blocks_framework
    assert not Assessment(Level.NONE).blocks_framework


def test_the_screen_is_never_blank_while_the_protocols_are_unwritten():
    """The wording is muhammad's to supply. Until it exists the person still sees words -
    the implementation this replaces returned an empty string at exactly this moment."""
    from mani.chat.safety import PROTOCOLS

    assert PROTOCOLS == {}, "protocol wording is a clinical decision, not an engineering one"
    assert protocol_for(Category.SUICIDE) == crisis.CRISIS_REPLY
    assert protocol_for(None).strip()
