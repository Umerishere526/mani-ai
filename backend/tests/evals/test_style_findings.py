# ABOUTME: Checks the style validator used by the live eval against known replies.
# ABOUTME: The eval can only measure style separation if this check itself is right.

from tests.evals.validators import style_findings, unasked_before_offer


def test_direct_may_open_on_i_as_the_clients_own_lines_do_but_never_on_presence():
    assert style_findings("I'm here with you. What happened next?", "direct")
    for client_line in (
        "I'm sorry you're feeling this way. Tell me what is happening right now.",
        "I have a structured approach that can help you work through this. Would you like to try it with me?",
        "Okay. I'll guide you through it one step at a time.",
    ):
        assert not style_findings(client_line, "direct"), client_line


def test_announced_presence_belongs_to_supportive_only():
    assert not style_findings("Thank you for telling me. I'm here.", "supportive")
    assert style_findings("Thank you for telling me. I'm here.", "reflective")


def test_a_reflective_reply_never_says_i_hear_you():
    assert style_findings("I hear you. What does it mean to you?", "reflective")
    assert not style_findings("You said it keeps coming back. What does it mean to you?", "reflective")


def test_a_reply_that_asks_nothing_before_the_offer_is_a_stall():
    replies = [
        ("You're feeling like a panic attack is coming on.", False),
        ("Your chest is tight. What feels strongest right now?", False),
        ("I have a structured approach. Would you like to try it?", True),
        ("Okay. Let's look at it together, one step at a time.", False),  # after: not judged
    ]
    [finding] = unasked_before_offer(replies)
    assert "panic attack" in str(finding)


def test_an_invitation_to_say_more_counts_as_asking():
    assert not unasked_before_offer([("I'm sorry you're feeling this way. Tell me what is happening right now.", False)])


def test_a_framework_that_ends_without_its_hand_off_buttons_is_caught():
    from tests.evals.validators import missing_handoff

    ok = [("closing", []), ("somatic", []), (None, ["Chat More", "Go to Library"])]
    assert missing_handoff(ok) == []
    bare = [("somatic", []), (None, ["Tell me more"])]
    assert missing_handoff(bare)


def test_a_second_chat_that_cites_the_first_is_caught():
    from tests.evals.validators import references_other_chat

    assert references_other_chat("Last time you said Sundays were hard.", ["sunday"], "hi")
    assert references_other_chat("How are Sunday nights going?", ["sunday"], "I'm tired")
    assert not references_other_chat("How was your Sunday?", ["sunday"], "my sunday was rough")
    assert not references_other_chat("What's on your mind?", ["sunday"], "hi")


def test_a_question_asked_again_is_caught_even_reworded_slightly():
    from tests.evals.validators import repeated_question

    stalled = [
        "That thought keeps returning. Is this the one you want to look at together?",
        "It came up in the meeting. Is this the one you want to look at together?",
    ]
    assert repeated_question(stalled)
    moving = [
        "That thought keeps returning. Is this the one you want to look at together?",
        "It came up in the meeting. What makes that thought difficult for you?",
    ]
    assert not repeated_question(moving)


def test_no_hand_off_is_needed_once_they_have_chosen():
    from tests.evals.validators import missing_handoff

    assert missing_handoff([("somatic", []), (None, [])], ["my chest feels lighter", "Chat More"]) == []


def test_the_clients_own_two_question_lines_are_not_counted_as_stacking():
    from tests.evals.validators import question_count

    assert question_count("Your chest feels lighter. Does that feel right? What would you like to do next?") == 1
    assert question_count("Before we move on, can we check in for a moment? What are you noticing in your body right now compared with when we started?") == 1
    assert question_count("What happened? And how did she react?") == 2
