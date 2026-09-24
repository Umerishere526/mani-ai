# ABOUTME: Checks Mani's opening line and the style choice it offers, against the client spec.
# ABOUTME: docs/specs/conversational-styles.md "Conversation opening" is the wording source.

from mani.chat import greeting


def test_a_new_person_is_greeted_and_asked_how_to_be_spoken_to():
    assert greeting.greeting("Sam", returning=False) == (
        "Hi Sam. It's MANI. How would you like me to speak with you today?"
    )


def test_a_returning_person_is_welcomed_back():
    assert greeting.greeting("Sam", returning=True) == (
        "Hi Sam, good to see you again. How would you like me to speak with you today?"
    )


def test_the_greeting_offers_exactly_the_three_styles():
    assert [o["label"] for o in greeting.STYLE_OPTIONS] == ["Direct", "Supportive", "Reflective"]
    assert [o["style"] for o in greeting.STYLE_OPTIONS] == ["direct", "supportive", "reflective"]


def test_each_style_opens_with_its_own_question():
    assert greeting.OPENERS == {
        "direct": "How can I help you today?",
        "supportive": "How can I support you today?",
        "reflective": "What's on your mind today?",
    }
