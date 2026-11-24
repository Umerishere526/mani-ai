# ABOUTME: Holding a reply to one question: the question it chose goes after its text, and what it asked is known
# ABOUTME: exactly, so the next reply can be told; the text's own words are kept whole.

from mani.chat.questions import held_to_one


def test_the_chosen_question_goes_after_the_text_on_its_own_line_whatever_its_form():
    assert held_to_one("Your sister leans on you a lot.", "Tell me about the last time she asked.",
                       frustrated=False) == (
        "Your sister leans on you a lot.\n\nTell me about the last time she asked.",
        "Tell me about the last time she asked.", None)


def test_text_that_asks_nothing_goes_out_exactly_as_written():
    text = "That sounds tiring.\n\nYou said \"why me?\" and left it there."
    assert held_to_one(text, "", frustrated=False) == (text, "", None)


def test_a_question_the_text_asks_beside_the_chosen_one_is_taken_out_and_the_layout_kept():
    text = "You keep saying yes. What happens then?\n\nYou're running on empty."
    assert held_to_one(text, "What would change if you said no once?", frustrated=False) == (
        "You keep saying yes.\n\nYou're running on empty.\n\nWhat would change if you said no once?",
        "What would change if you said no once?", "question in the text")


def test_with_no_chosen_question_the_text_keeps_its_last_one_where_it_stands():
    text = "You keep saying yes. What happens then?\n\nWhat would change if you said\nno once? It's a lot."
    assert held_to_one(text, "", frustrated=False) == (
        "You keep saying yes.\n\nWhat would change if you said\nno once? It's a lot.",
        "What would change if you said no once?", "more than one question")


def test_a_frustrated_message_gets_no_question_at_all():
    text = "Fair, I've been circling. She leans on you because you always say yes. Does that fit?"
    assert held_to_one(text, "What would help right now?", frustrated=True) == (
        "Fair, I've been circling. She leans on you because you always say yes.", "", "question after frustration")
    assert held_to_one("Fair.", "", frustrated=True) == ("Fair.", "", None)
