# ABOUTME: Checks how a reply's text and the question that ends it are joined into what Mani says.
# ABOUTME: No model and no database.

from mani.chat import orchestrator


def test_the_question_goes_on_a_line_of_its_own_and_is_said_once():
    said = orchestrator._with_forward("That meeting left you feeling small. What happened next?", "What happened next?")
    assert said == "That meeting left you feeling small.\n\nWhat happened next?"


def test_a_question_with_no_words_in_it_is_no_question():
    """The live run of 2026-11-16: on the reply that moved to the set of questions the offer takes the question's
    place, the form still asked for one, and the model wrote ".?", which went out on a line of its own before the
    offer."""
    text = "So the fear is tied to the handover, not other signs you've noticed."
    for empty in (".?", "?", " ? ", "...?"):
        assert orchestrator._with_forward(text, empty) == text


def test_a_closing_question_of_two_sentences_is_still_said_once():
    """muhammad's local chat, 2026-11-16: the model put the question and its reason in the text and again, together,
    as the closing question, and the person read both twice. Every sentence of the closing question leaves the text."""
    text = (
        "Not having anyone you trust there leaves you with little support. Did you mean the situation feels "
        "unbearable, or that you might hurt yourself? I'm asking because I want to understand whether you're safe."
    )
    forward = (
        "Did you mean the situation feels unbearable, or that you might hurt yourself? I'm asking because I want to "
        "understand whether you're safe?"
    )
    assert orchestrator._with_forward(text, forward) == (
        "Not having anyone you trust there leaves you with little support.\n\n" + forward)


def test_a_text_that_already_ends_on_the_closing_question_is_not_asked_it_again():
    """The live pass of 2026-11-16: the text led into the question with its reason ("I want to check because ...:
    do you mean ...?") and the same question followed on its own line."""
    text = (
        "That clearly brings up a lot of anger. I want to check because of what you said: do you mean you might "
        "actually hurt him, or are you saying how furious you feel?"
    )
    forward = "Do you mean you might actually hurt him, or are you saying how furious you feel?"
    assert orchestrator._with_forward(text, forward) == text
