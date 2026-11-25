# ABOUTME: Checks what code enforces on a reply before the person receives it: each of the client's rules that code can
# ABOUTME: read, the event it records, and that a guarded turn's safety words are never cut.

import pytest

from mani.chat import crisis, enforce


def sent(text: str, ask: str = "", *, fixed: bool = False, guarded: bool = False, open_chat: bool = True,
         latest: str = "answer") -> enforce.Sent:
    return enforce.sent(text, ask, fixed=fixed, guarded=guarded, open_chat=open_chat, latest=latest)


def test_a_guarded_reply_whose_text_already_asks_its_question_asks_it_once():
    """TC-13 (2026-11-25): a guarded turn joined the text and the chosen question, and both held the same question."""
    reply = sent("Okay. That's clear.\n\nHow long has it been like this for you?",
                 "How long has it been like this for you?", guarded=True, open_chat=False)
    assert reply.text == "Okay. That's clear.\n\nHow long has it been like this for you?"
    assert reply.asked == "How long has it been like this for you?"
    assert reply.enforced == [enforce.REPEATED_QUESTION]


def test_a_nearly_identical_question_counts_as_the_same_and_a_different_one_is_kept():
    assert enforce.repeats("Numb is a lot. How long has it been like this?", "How long has it been like this for you?")
    assert not enforce.repeats("How are you?", "How are you feeling about your sister now?")
    reply = sent("That sounds frightening. Are you hurt?", "Is anyone with you right now?", guarded=True,
                 open_chat=False, latest="other")
    assert reply.text == "That sounds frightening. Are you hurt?\n\nIs anyone with you right now?"
    assert reply.enforced == []


@pytest.mark.parametrize(("written", "received"), [
    # The words the eval and suite runs caught (2026-11-25).
    ("Two words, and they land hard.", "Two words, and they hit hard."),
    ("When was the last time someone noticed you were struggling?",
     "When was the last time someone noticed you were finding it hard?"),
    ("Broken nights add up. Give yourself some space.", "Hurt nights add up. Give yourself some room."),
    # An article before the word still fits the plain word; "landed" and "spaces" are other words.
    ("That's an unhealthy loop, and a flawed plan.", "That's an unhelpful loop, and an imperfect plan."),
    ("It landed on her.", "It landed on her."),
])
def test_a_forbidden_word_reaches_them_as_a_plain_word(written, received):
    """Behavioral Framework: the forbidden words never appear in a Mani response; the prompt alone let 7 of 158 eval
    replies through."""
    reply = sent(written)
    assert reply.text == received and not enforce.forbidden_words(reply.text)


def test_each_swap_is_recorded_with_its_word_and_the_chosen_question_is_swapped_too():
    reply = sent("They land hard.", "What does stability look like for you?")
    assert reply.text == "They hit hard.\n\nWhat does steadiness look like for you?"
    assert reply.enforced == ["forbidden_word:land", "forbidden_word:stability"]


def test_a_banned_line_is_taken_out_unless_it_is_all_the_reply_says_or_the_turn_is_guarded():
    """Safety Guardrails section 6: lines Mani never says."""
    reply = sent("I'm here for you. That week sounds long.", "What happened on Friday?")
    assert reply.text == "That week sounds long.\n\nWhat happened on Friday?"
    assert reply.enforced == [enforce.BANNED_LINE_REMOVED]
    alone = sent("You’re not alone.")
    assert alone.text == "You’re not alone." and alone.enforced == [enforce.BANNED_LINE_KEPT]
    guarded = sent("You're not alone. Please call 988 now.", guarded=True, open_chat=False)
    assert guarded.text == "You're not alone. Please call 988 now."
    assert guarded.enforced == [enforce.BANNED_LINE_KEPT]


def test_codes_fixed_safety_words_go_out_untouched():
    reply = sent(f"Your chat is on hold. There's space.\n\n{crisis.END_CHECK}", fixed=True, guarded=True,
                 open_chat=False)
    assert "space" in reply.text and reply.enforced == []


@pytest.mark.parametrize(("message", "stop"), [
    ("I'm done", True), ("Yes, I'm done for now.", True), ("that’s all, thanks", True), ("ok bye!", True),
    ("enough for today", True), ("I have to go", True), ("let's stop here. thank you", True), ("im good for now", True),
    # A stop phrase inside something else they are telling Mani is not a wish to stop.
    ("I'm done with my job", False), ("bye, she said, and left", False), ("I have to go to work tomorrow", False),
    ("thanks", False),
])
def test_a_typed_stop_is_only_a_message_that_says_nothing_but_stop(message, stop):
    assert enforce.typed_stop(message) is stop


def test_a_typed_stop_the_model_missed_is_read_as_one_but_never_on_a_guarded_turn():
    """Eval rule-typed-done 3/3 and TC-17 asked "what do you mean by done?" (R95)."""
    from mani.chat.reply import Question, Safety, TurnReply

    reply = TurnReply(text="Okay.", safety=Safety(level="none"), notes="",
                      question=Question(latest="other", ask="What do you mean by done?"))
    read, events = enforce.read_stop(reply, "I'm done", guarded=False)
    assert read.question.latest == "wants_to_stop" and events == [enforce.TYPED_STOP]
    assert reply.question.latest == "other"
    kept, events = enforce.read_stop(reply, "I'm done", guarded=True)
    assert kept is reply and events == []
