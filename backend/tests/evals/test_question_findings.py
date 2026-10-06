# ABOUTME: Checks the question validator against real questions from the 4 October run and the old chat.
# ABOUTME: The counts can only show whether questions got plainer if this check itself is right.

from tests.evals.validators import question_findings


def rules(reply: str, their_message: str = "I went to a concert", **kwargs) -> list[str]:
    return [f.rule for f in question_findings(reply, their_message, **kwargs)]


def test_a_question_wrapped_in_a_restatement_is_long_and_has_a_lead_clause():
    reply = (
        "Since you’ve mentioned that you find yourself losing an hour to scrolling, what makes "
        "returning to the time you spent doing other things matter to you?"
    )

    assert sorted(rules(reply)) == ["lead clause", "long question"]
    assert rules(
        "Since that presentation is due Friday, what do you know for certain?"
    ) == ["lead clause"]


def test_a_short_plain_question_about_what_they_said_passes():
    assert rules("What was in that message?") == []
    assert rules("We can sit with that. What does being alone feel like for you today?") == []
    assert rules("When you try to stop, what happens?") == []


def test_worksheet_and_ranking_words_are_flagged_but_not_words_that_only_contain_them():
    assert rules("What gives it that meaning?") == ["flagged word"]
    assert rules("What would you like to explore first?") == ["flagged word"]
    assert rules("Which part is pulling the most on you?") == ["flagged word"]
    assert rules("Was it a meaningful night?") == []
    assert rules("Shall we keep this reflective?") == []


def test_an_either_or_is_a_fault_only_when_handed_to_someone_who_is_stuck():
    reply = "Would you like to try an exercise, or would you prefer to keep talking?"

    assert rules(reply, "i cant decide") == ["either/or"]
    assert rules(reply, "I went to a concert") == []
    assert rules(reply, "i cant decide", in_framework=True) == []
    assert "either/or" in rules(
        "Would it help to name a few of them, or would you rather sit with the restlessness?",
        "Not sure yet",
    )


def test_the_clients_own_choices_are_not_counted_as_an_either_or():
    library = "You'd rather not check in with your body right now. Would you like to keep chatting or go to the Library?"

    assert rules(library, "not sure") == []
