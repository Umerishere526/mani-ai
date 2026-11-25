# ABOUTME: Checks what code enforces on a reply before the person receives it: each of the client's rules that code can
# ABOUTME: read, the event it records, and that a guarded turn's safety words are never cut.

from mani.chat import enforce


def test_a_guarded_reply_whose_text_already_asks_its_question_asks_it_once():
    """TC-13 (2026-11-25): a guarded turn joined the text and the chosen question, and both held the same question."""
    sent = enforce.sent("Okay. That's clear.\n\nHow long has it been like this for you?",
                        "How long has it been like this for you?", guarded=True, open_chat=False, latest="answer")
    assert sent.text == "Okay. That's clear.\n\nHow long has it been like this for you?"
    assert sent.asked == "How long has it been like this for you?"
    assert sent.enforced == [enforce.REPEATED_QUESTION]


def test_a_nearly_identical_question_counts_as_the_same_and_a_different_one_is_kept():
    assert enforce.repeats("Numb is a lot. How long has it been like this?", "How long has it been like this for you?")
    assert enforce.repeats("When you wake up, what actually happens?", "When you wake up, what actually happens?")
    sent = enforce.sent("That sounds frightening. Are you hurt?", "Is anyone with you right now?", guarded=True,
                        open_chat=False, latest="other")
    assert sent.text == "That sounds frightening. Are you hurt?\n\nIs anyone with you right now?"
    assert sent.enforced == []
    assert not enforce.repeats("How are you?", "How are you feeling about your sister now?")
