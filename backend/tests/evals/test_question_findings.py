# ABOUTME: Checks the question validator against real questions from the 4 October run and the old chat.
# ABOUTME: The counts can only show whether questions got plainer if this check itself is right.

from tests.evals.validators import question_findings


def rules(reply: str) -> list[str]:
    return [f.rule for f in question_findings(reply)]


def test_a_question_wrapped_in_a_restatement_has_a_lead_clause():
    """The client's PDF marks a clause restating what came before as hard to read."""
    reply = (
        "Since you’ve mentioned that you find yourself losing an hour to scrolling, what makes "
        "returning to the time you spent doing other things matter to you?"
    )

    assert rules(reply) == ["lead clause"]
    assert rules("Given the deadline, what do you know for certain?") == ["lead clause"]


def test_the_clients_own_kinds_of_question_pass():
    """Length, ranking and choices are the client's to use (spec 0010): its own replies ask
    "What feels most pressing right now?" and questions of over twenty words."""
    assert rules("What was in that message?") == []
    assert rules("When you try to stop, what happens?") == []
    assert rules("What feels most pressing right now?") == []
    assert rules(
        "Does it feel like you're trying to figure out what the text means, but your mind keeps "
        "taking you back to the worst possibility?"
    ) == []
    assert rules("Do you want to keep working through it together, or would it help to explore a tool?") == []
