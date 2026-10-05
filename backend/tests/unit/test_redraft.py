# ABOUTME: Checks which drafted replies are asked for again, and for what reason.
# ABOUTME: Each reason is a rule about the person or the cadence, so each is a plain test.

import pytest

from mani.chat import redraft
from mani.chat.techniques import Registry
from mani.llm.schema import Reply, SmartPrompt
from mani.models.rows import Framework


def registry() -> Registry:
    return Registry([
        Framework(
            id="behavioral_activation", name="Behavioral Activation", summary="s", body="b",
            phases=["offering"], activation={"never_offer_when_said": ["died"]},
        ),
        Framework(
            id="act_choice_point", name="ACT Choice Point", summary="s", body="b",
            phases=["offering"], activation={},
        ),
    ])


def offer(technique: str) -> Reply:
    return Reply(
        text="There are some questions we could go through. Would you like to try it?",
        prompts=[SmartPrompt(label="Try it", technique=technique), SmartPrompt(label="Keep chatting", decline=True)],
    )


def test_a_clean_question_stands():
    draft = Reply(text="What is the hardest part of the evenings?")
    assert redraft.reasons(draft, ["i'm lonely"], registry(), offer_not_allowed=False) == []


def test_a_feeling_they_never_named_is_a_reason():
    draft = Reply(text="With the exam this stressful, what do you need first?")
    why = redraft.reasons(draft, ["i have an exam"], registry(), offer_not_allowed=False)
    assert len(why) == 1 and "stressful" in why[0]


def test_an_offer_before_the_clients_cadence_allows_it_is_a_reason():
    why = redraft.reasons(offer("act_choice_point"), ["my dog died"], registry(), offer_not_allowed=True)
    assert len(why) == 1 and "not allowed yet" in why[0]


def test_an_offer_what_they_said_rules_out_is_a_reason():
    why = redraft.reasons(offer("behavioral_activation"), ["my dog died"], registry(), offer_not_allowed=False)
    assert len(why) == 1 and "Behavioral Activation" in why[0]
    assert redraft.ruled_out(offer("behavioral_activation"), ["my dog died"], registry()) == "behavioral_activation"


def test_the_same_offer_is_fine_when_nothing_rules_it_out():
    assert redraft.reasons(offer("behavioral_activation"), ["i stopped answering people"], registry(), offer_not_allowed=False) == []
    assert redraft.ruled_out(offer("act_choice_point"), ["my dog died"], registry()) is None


def test_not_offering_is_never_a_reason_on_its_own():
    """Mani offers when what they have said makes a fit clear, never because enough messages
    have passed (client meeting, 2026-10-02)."""
    leaning = Reply(text="What is the hardest part?", heading_toward="act_choice_point")
    assert redraft.reasons(leaning, ["my dog died"], registry(), offer_not_allowed=False) == []


def test_a_reply_with_no_question_is_never_a_reason_on_its_own():
    """A question is asked when it earns its place (ADR-015): a reply that only receives what they
    said stands."""
    receiving = Reply(text="Small, and in front of everyone.")
    assert redraft.reasons(receiving, ["i felt small in front of everyone"], registry(), offer_not_allowed=False) == []


def test_an_offer_that_depends_on_what_it_meant_waits_and_says_why():
    why = redraft.reasons(offer("act_choice_point"), ["i felt embarrassed"], registry(), offer_not_allowed=False, earliest_wait=True)
    assert len(why) == 1 and "what they took it to mean" in why[0] and "ACT Choice Point" in why[0]


FIRST = (
    "It can be hard to choose when everything feels like a big step. Would picking one of these small "
    "actions, opening your laptop to look at one travel destination, browsing a site for one new "
    "learning opportunity, or simply sitting near a window for a few minutes, feel most manageable "
    "to you today?"
)
SAME_AGAIN = (
    "It is okay that you are not sure. Between opening your laptop to look at one travel destination, "
    "browsing for one learning opportunity, or sitting by a window for a few minutes, which one "
    "feels like the most manageable one to start with today?"
)


def test_the_same_choices_asked_again_are_redrafted():
    """Observed: someone who asked Mani to pick got the same three options back, reworded, twice."""
    why = redraft.reasons(
        Reply(text=SAME_AGAIN), [], registry(), offer_not_allowed=False, last_mani_text=FIRST
    )
    assert any("asks the question you asked last turn" in w for w in why)


def test_a_different_question_after_an_answer_is_not_a_repeat():
    moved_on = Reply(text="Opening your laptop to look at one place sounds like a start. When will you do it?")
    assert redraft.reasons(
        moved_on, [], registry(), offer_not_allowed=False, last_mani_text=FIRST
    ) == []


@pytest.mark.parametrize("text, phrase", [
    ("It sounds like the evenings are the hardest. What happens then?", "it sounds like"),
    ("That sounds like a rough experience. What happened next?", "that sounds"),
    ("It makes sense that the memory would come back. When did it start?", "it makes sense"),
    ("I hear you. What did he say?", "i hear you"),
])
def test_a_stock_phrase_is_a_reason_the_first_time_it_is_used(text, phrase):
    """Client meeting, 2026-10-02: "every answer was: it sounds like". muhammad, 2026-10-05: not
    once, not at all."""
    why = redraft.reasons(Reply(text=text), ["evenings"], registry(), offer_not_allowed=False)
    assert len(why) == 1 and f'"{phrase}"' in why[0]


@pytest.mark.parametrize("text", [
    "Does that make sense as a first step?",
    "Opening your laptop sounds like a start. When will you do it?",
])
def test_ordinary_words_that_share_a_stock_phrase_are_not_one(text):
    assert redraft.reasons(Reply(text=text), ["ok"], registry(), offer_not_allowed=False) == []


@pytest.mark.parametrize("text", [
    "I am here with you. Focus on your breathing for a moment and take it slowly.",
    "Take a deep breath. Where are you right now?",
    "Try to ground yourself by noticing your feet on the floor. Is someone with you?",
])
def test_an_instruction_or_exercise_of_manis_own_is_a_reason(text):
    """muhammad, 2026-10-05: no guidance of Mani's own, not even in panic. Practices come from a
    framework's practice stage or the Library."""
    why = redraft.reasons(Reply(text=text), ["i am having a panic attack"], registry(), offer_not_allowed=False)
    assert len(why) == 1 and "instruction" in why[0]


def test_a_practice_inside_a_running_framework_stands():
    practice = Reply(text="Take a deep breath in through your nose, and let it out slowly. How was that?")
    assert redraft.reasons(
        practice, ["my chest"], registry(), offer_not_allowed=False, framework_running=True
    ) == []


def test_talking_about_their_breathing_is_not_an_instruction():
    draft = Reply(text="Your breathing felt fast at the start. What changed when you sat down?")
    assert redraft.reasons(draft, ["my breathing was fast"], registry(), offer_not_allowed=False) == []


def test_an_offer_that_also_asks_its_own_question_is_a_reason():
    """The repair drops an offer that shares its reply with another question, so the person never
    reaches the framework; the model is asked to choose one instead."""
    both = Reply(
        text="The thought keeps coming back after that meeting. How has it been affecting you?",
        prompts=[SmartPrompt(label="Try it", technique="act_choice_point"),
                 SmartPrompt(label="Keep chatting", decline=True)],
    )
    why = redraft.reasons(both, ["i keep thinking i'm bad at my job"], registry(), offer_not_allowed=False)
    assert len(why) == 1 and "offer" in why[0] and "question" in why[0]


def test_an_offer_whose_only_question_asks_to_try_it_stands():
    assert redraft.reasons(offer("act_choice_point"), ["x"], registry(), offer_not_allowed=False) == []


@pytest.mark.parametrize("text", [
    "Breathe as slowly as you can. Is anyone nearby?",
    "Try to focus on just this moment. Is anyone nearby?",
    "I am right here with you. Keep breathing slowly. Is someone with you?",
    "I am here with you. Please just breathe however you can right now. What do you need?",
])
def test_more_ways_of_giving_an_instruction_are_caught(text):
    why = redraft.reasons(Reply(text=text), ["panic"], registry(), offer_not_allowed=False)
    assert len(why) == 1 and "instruction" in why[0]


@pytest.mark.parametrize("text", [
    "It is understandable that a moment like that would stay with you. What happened next?",
    "Being alone when that memory came back sounds very difficult. What came up?",
])
def test_more_stock_empathy_is_caught(text):
    why = redraft.reasons(Reply(text=text), ["x"], registry(), offer_not_allowed=False)
    assert any("stock" in w for w in why)
