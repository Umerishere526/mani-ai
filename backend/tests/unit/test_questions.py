# ABOUTME: Which sentences of a reply are questions, and whether the reply ends on one: what code keeps of Mani's own
# ABOUTME: words so the next reply can be told what was already asked.

from mani.chat.questions import asked_in, ends_on_one, held_to_one


def test_the_questions_of_a_reply_are_its_sentences_that_end_on_a_question_mark():
    text = 'That sounds tiring.\n\nYou said "why me?" and left it there. What happened next? And who was with you?'
    assert asked_in(text) == ["What happened next?", "And who was with you?"]
    assert ends_on_one(text) and not ends_on_one("I'm here, and we can stay with this.") and asked_in("") == []


def test_a_question_that_closes_inside_quotes_still_counts_and_line_breaks_are_folded():
    text = 'Try finishing this:\n"What would I say to a friend?"'
    assert asked_in(text) == ['Try finishing this: "What would I say to a friend?"'] and ends_on_one(text)


def test_a_reply_keeps_only_its_last_question_and_its_layout():
    text = "You keep saying yes. What happens then?\n\nYou're running on empty.\n\nWhat would change if you said no once?"
    assert held_to_one(text, "answer") == (
        "You keep saying yes.\n\nYou're running on empty.\n\nWhat would change if you said no once?",
        "more than one question")
    assert held_to_one("That's hard. What happened next?", "answer") == ("That's hard. What happened next?", None)


def test_a_frustrated_message_gets_no_question_at_all():
    text = "Fair, I've been circling. She leans on you because you always say yes.\n\nWhat would change if you said no?"
    assert held_to_one(text, "Frustrated") == (
        "Fair, I've been circling. She leans on you because you always say yes.", "question after frustration")
