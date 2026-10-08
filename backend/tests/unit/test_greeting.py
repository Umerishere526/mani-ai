# ABOUTME: Checks Mani's opening line and the style choice it offers, built from the seeded `replies` row.
# ABOUTME: docs/specs/conversational-styles.md "Conversation opening" is the wording source.

from mani.chat import greeting
from tests.seeded import seeded_replies

REPLIES = seeded_replies()


def test_a_new_person_is_greeted_and_asked_how_to_be_spoken_to():
    assert greeting.greeting(REPLIES, "Sam", returning=False) == (
        "Hi Sam. It's MANI. How would you like me to speak with you today?"
    )


def test_a_returning_person_is_welcomed_back():
    assert greeting.greeting(REPLIES, "Sam", returning=True) == (
        "Hi Sam, good to see you again. How would you like me to speak with you today?"
    )


def test_a_person_with_no_nickname_is_greeted_as_there():
    assert greeting.greeting(REPLIES, None, returning=False).startswith("Hi there. It's MANI.")


def test_the_greeting_offers_exactly_the_three_styles_in_the_order_the_file_lists_them():
    options = greeting.style_options(REPLIES)
    assert [o["label"] for o in options] == ["Direct", "Supportive", "Reflective"]
    assert [o["style"] for o in options] == ["direct", "supportive", "reflective"]


def test_each_style_opens_with_its_own_question():
    assert REPLIES.openers == {
        "direct": "How can I help you today?",
        "supportive": "How can I support you today?",
        "reflective": "What's on your mind today?",
    }


def test_a_renamed_label_is_what_the_greeting_shows():
    renamed = seeded_replies(style_labels={**REPLIES.style_labels, "direct": "Straight"})
    assert [o["label"] for o in greeting.style_options(renamed)][0] == "Straight"
