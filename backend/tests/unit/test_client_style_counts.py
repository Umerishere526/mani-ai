# ABOUTME: Checks the counts the client style check reports for a conversation's replies.
# ABOUTME: Real reply text in, numbers out; the model is not involved.

from mani.chat.repairs import PERMISSION_QUESTIONS
from scripts.client_style_counts import (
    SEEMS_LIKE,
    SOUNDS_LIKE,
    Turn,
    count_conversation,
    count_dashes,
    count_reply,
    figures,
    own_words,
    own_words_before_acceptance,
    restating_read,
    short_message_turns,
    shuffled_for_reading,
    style_read_replies,
)

DESCRIPTION = "These questions help you pause and understand what is happening, so you feel less overwhelmed."
DESCRIPTIONS = frozenset({DESCRIPTION})
PERMISSION = PERMISSION_QUESTIONS["reflective"]


def an_offer(part: str) -> str:
    """An offer as the code composes it: Mani's part, the description, the permission question."""
    return f"{part}\n\n{DESCRIPTION}\n\n{PERMISSION}"


def test_a_reply_counts_its_questions_stock_phrases_and_dashes():
    reply = "I hear you — and I’m here for you. What happened? Did it start at work?"

    counts = count_reply(reply)

    assert counts.questions == 2
    assert counts.stock_phrases == 2
    assert counts.dashes == 1


def test_stock_phrases_are_found_however_the_model_spells_them():
    reply = "I am here with you. That makes sense. I'm right here with you, and I hear you."

    assert count_reply(reply).stock_phrases == 4


def test_sounds_like_and_seems_like_are_found_in_every_form_and_counted_per_phrase():
    reply = (
        "It sounds like a hard day. That sounds like a lot. Sounds like you tried. "
        "It SEEMS LIKE it went fast, and it seems as if you stopped. It seems as though it ended."
    )

    phrases = count_reply(reply).phrases

    assert phrases[SOUNDS_LIKE.pattern] == 3
    assert phrases[SEEMS_LIKE.pattern] == 3
    assert count_reply("It sounds like. It sounds like.").phrases == {SOUNDS_LIKE.pattern: 2}


def test_only_dash_punctuation_counts_not_a_hyphen_inside_a_word_or_a_list_marker():
    assert count_reply("Let's do a check-in now.").dashes == 0
    assert count_reply("You stopped – then started again - twice.").dashes == 2
    assert count_dashes("Three things:\n- one\n  - two\n* three") == 0


def test_an_offer_is_cut_back_to_what_mani_wrote_of_it():
    reply = an_offer("That sounds like a hard week.")

    assert own_words(reply, DESCRIPTIONS) == "That sounds like a hard week."
    assert own_words("What happened?", DESCRIPTIONS) == "What happened?"


def test_an_offer_whose_buttons_were_dropped_is_still_cut_back_to_mani_part():
    turns = [Turn("I feel panicky", an_offer("That sounds fast."))]

    counts = count_conversation(turns, DESCRIPTIONS)

    assert counts.own_questions == 0
    assert counts.long_replies == 0


def test_questions_are_counted_on_mani_own_words_and_not_after_the_person_accepts():
    turns = [
        Turn("I can't stop scrolling", "What happens just before you pick it up?"),
        Turn("I get bored", an_offer("Boredom can pull you in."), offered=True),
        Turn("Try it", "Okay. Can you put the phone down for a moment?", tapped=True),
    ]

    counts = count_conversation(turns, DESCRIPTIONS)

    assert counts.questions == 3
    assert counts.own_replies == 2
    assert counts.own_questions == 1
    assert counts.offer_at == 2


def test_a_feeling_in_the_description_the_code_adds_is_not_mani_naming_it():
    turns = [Turn("I keep scrolling", an_offer("It can be hard to stop."), offered=True)]

    assert count_conversation(turns, DESCRIPTIONS).unused_feelings == []


def test_a_feeling_mani_names_that_the_person_never_used_is_counted():
    turns = [
        Turn("I keep scrolling", "That sounds exhausting."),
        Turn("I feel tired of it", "You sound tired of it."),
    ]

    assert count_conversation(turns, DESCRIPTIONS).unused_feelings == ["exhausting"]


def test_a_size_phrase_mani_adds_is_counted_and_one_the_person_used_is_not():
    turns = [
        Turn("I have a lot on", "That is a lot to hold."),
        Turn("work is hard", "So much is riding on it."),
    ]

    assert count_conversation(turns, DESCRIPTIONS).unused_sizes == ["so much"]


def test_a_size_phrase_in_the_description_the_code_adds_is_not_counted():
    turns = [Turn("I keep scrolling", f"Okay.\n\nA lot of people find {DESCRIPTION}\n\n{PERMISSION}")]
    description = f"A lot of people find {DESCRIPTION}"

    assert count_conversation(turns, frozenset({description})).unused_sizes == []


def test_figures_report_a_lot_apart_from_the_other_size_phrases():
    turns = [Turn("a", "That is a lot."), Turn("b", "It is a burden.")]

    result = figures([("direct", 1, count_conversation(turns, DESCRIPTIONS))])

    assert result["unused_a_lot"] == 1
    assert result["unused_size_phrases"] == 1


def test_the_style_read_shows_the_first_two_replies_in_mani_own_words_each_under_its_message():
    turns = [
        Turn("I'm panicking", an_offer("Stay with me."), offered=True),
        Turn("Try it", "Okay, one breath.", tapped=True),
        Turn("later", "Third reply."),
    ]

    read = style_read_replies(turns, DESCRIPTIONS)

    assert read == [
        "**Person:** I'm panicking\n\n**Mani:** Stay with me.",
        "**Person:** Try it\n\n**Mani:** Okay, one breath.",
    ]


def test_a_conversation_is_read_from_its_start_to_the_acceptance():
    turns = [
        Turn("a", "First.", offered=True),
        Turn("Try it", "After.", tapped=True),
    ]

    assert own_words_before_acceptance(turns, DESCRIPTIONS) == "**Person:** a\n\n**Mani:** First."


def test_a_tagged_conversation_marks_the_offer_reply_and_the_opening_after_a_tap():
    turns = [
        Turn("a", "Plain."),
        Turn("Chat More", "Opening.", tapped=True),
        Turn("b", "First.", offered=True),
    ]

    read = own_words_before_acceptance(turns, DESCRIPTIONS, tagged=True)

    assert "**Mani:** Plain." in read
    assert "**Mani:** [after tap] Opening." in read
    assert "**Mani:** [offer] First." in read
    assert "[offer]" not in own_words_before_acceptance(turns, DESCRIPTIONS)


def saved(conversation: str, style: str, run: int, reply: str) -> dict:
    turn = {"message": "I cannot stop scrolling", "reply": reply, "offered": False, "tapped": False,
            "scripted": False, "buttons": [], "framework": None}
    return {"conversation": conversation, "style": style, "run": run, "turns": [turn]}


def test_the_restating_read_takes_run_one_of_every_source_and_hides_the_source_until_the_key():
    sources = {
        "zzbefore": [saved("scroll", "direct", 1, "You keep scrolling."), saved("scroll", "direct", 2, "Run two.")],
        "zzafter": [saved("scroll", "direct", 1, "What starts it?")],
    }

    read = restating_read(sources, DESCRIPTIONS)
    body, key = read.split("## Key")

    assert body.startswith("# Restating read")
    assert "zzbefore" not in body and "zzafter" not in body
    assert "You keep scrolling." in body and "What starts it?" in body
    assert "Run two." not in read
    assert "zzbefore · scroll · direct" in key and "zzafter · scroll · direct" in key
    assert restating_read(sources, DESCRIPTIONS) == read


def test_a_shuffled_reading_hides_where_each_entry_came_from_until_the_key():
    entries = [(f"source {n}", f"text {n}") for n in range(8)]

    read = shuffled_for_reading(entries)
    body, key = read.split("## Key")

    assert "source" not in body
    assert all(f"text {n}" in body for n in range(8))
    numbered = {
        line.split(": ")[0].removeprefix("- "): line.split(": ")[1]
        for line in key.splitlines() if line.startswith("- ")
    }
    for number, source in numbered.items():
        text = body.split(f"## {number}\n\n")[1].split("\n")[0]
        assert text == f"text {source.removeprefix('source ')}"
    assert shuffled_for_reading(entries) == read


def test_replies_of_more_than_three_sentences_and_with_two_questions_are_counted():
    turns = [
        Turn("a", "One. Two. Three."),
        Turn("b", "One. Two. Three. Four."),
        Turn("c", "What changed? And why now?"),
    ]

    counts = count_conversation(turns, DESCRIPTIONS)

    assert counts.long_replies == 1
    assert counts.double_question_replies == 1


def test_a_stock_phrase_said_twice_in_a_conversation_is_counted_once_per_phrase():
    turns = [
        Turn("a", "I hear you. What is going on?"),
        Turn("b", "I hear you. What changed this week?"),
        Turn("c", "That makes sense."),
    ]

    counts = count_conversation(turns, DESCRIPTIONS)

    assert counts.phrases_said_twice == 1
    assert counts.stock_phrases == 3
    assert counts.repeated_openers == 1


def test_stock_phrases_are_counted_in_mani_own_words_before_the_person_accepts():
    description = "It sounds like these questions help you pause."
    turns = [
        Turn("I can't stop scrolling", "It sounds like a loop. What starts it?"),
        Turn("I get bored", f"Boredom pulls.\n\n{description}\n\n{PERMISSION}", offered=True),
        Turn("Try it", "Okay. It sounds like you are ready. What is first?", tapped=True),
    ]

    counts = count_conversation(turns, frozenset({description}))

    assert counts.own_phrases == {SOUNDS_LIKE.pattern: 1}
    assert counts.stock_phrases == 1
    assert counts.all_stock_phrases == 3


def test_a_stock_phrase_said_twice_in_mani_own_words_is_counted_once_per_phrase():
    turns = [
        Turn("a", "It sounds like a hard week."),
        Turn("b", "That sounds like a long one. It seems like you are tired."),
    ]

    counts = count_conversation(turns, DESCRIPTIONS)

    assert counts.phrases_said_twice == 1
    assert counts.stock_phrases == 3


def test_figures_total_sounds_like_and_seems_like_in_own_words_and_in_every_reply():
    turns = [
        Turn("a", "It sounds like a hard week.", offered=True),
        Turn("Try it", "It seems like a start.", tapped=True),
    ]

    result = figures([("direct", 1, count_conversation(turns, DESCRIPTIONS))])

    assert result["sounds_or_seems_like"] == 1
    assert result["sounds_or_seems_like_all"] == 2
    assert result["stock_phrases_per_conversation_direct"] == 1
    assert result["stock_phrases_all_per_conversation_direct"] == 2


def test_a_conversation_with_no_offer_has_none():
    turns = [Turn("a", "Tell me more about the deadline.")]

    assert count_conversation(turns, DESCRIPTIONS).offer_at is None


def test_short_messages_are_counted_in_raw_words_and_taps_are_left_out():
    turns = [
        Turn("Yes.", "r"),
        Turn("I don't know", "r"),
        Turn("I don't really know", "r"),
        Turn("Try it", "r", tapped=True),
        Turn("idk", "r"),
    ]

    assert short_message_turns(turns) == [0, 1, 4]


def test_figures_take_the_question_ratio_within_a_run_then_average_the_runs():
    one_question = [Turn("a", "What happened?"), Turn("b", "I see.")]
    two_questions = [Turn("a", "What happened?"), Turn("b", "Why?")]
    records = [
        ("direct", 1, count_conversation(one_question, DESCRIPTIONS)),
        ("direct", 2, count_conversation(two_questions, DESCRIPTIONS)),
    ]

    result = figures(records)

    assert result["questions_per_reply_own"] == (0.5 + 1.0) / 2
    assert result["conversations"] == 2
    assert result["offered"] == 0
