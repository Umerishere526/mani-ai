# ABOUTME: Checks which drafted replies are asked for again, and for what reason.
# ABOUTME: Each reason is a rule about the person or the cadence, so each is a plain test.

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
    draft = Reply(text="That sounds stressful. What do you need first?")
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


def test_not_offering_when_the_closest_fit_is_due_is_a_reason_if_mani_leans_somewhere():
    leaning = Reply(text="What is the hardest part?", heading_toward="act_choice_point")
    why = redraft.reasons(leaning, ["my dog died"], registry(), offer_not_allowed=False, closest_fit_due=True)
    assert len(why) == 1 and "offer the nearest set" in why[0]


def test_a_due_closest_fit_is_not_forced_when_mani_has_no_lean():
    undecided = Reply(text="What is the hardest part?")
    assert redraft.reasons(undecided, ["hi"], registry(), offer_not_allowed=False, closest_fit_due=True) == []


def test_a_due_closest_fit_is_not_forced_while_pain_may_be_physical():
    leaning = Reply(text="Is it in your body?", heading_toward="act_choice_point")
    assert redraft.reasons(leaning, ["i'm in pain"], registry(), offer_not_allowed=False, closest_fit_due=True) == []


def test_a_comfort_with_no_question_is_a_reason_before_an_offer():
    comfort = Reply(text="It is okay to feel that way. I am here with you.")
    why = redraft.reasons(comfort, ["i felt small"], registry(), offer_not_allowed=False, needs_question=True)
    assert len(why) == 1 and "asks no question" in why[0]


def test_no_question_is_fine_when_it_is_not_needed():
    """While the questions run, on a safety concern, or when they asked only to be heard."""
    comfort = Reply(text="It is okay to feel that way. I am here with you.")
    assert redraft.reasons(comfort, ["i felt small"], registry(), offer_not_allowed=False, needs_question=False) == []


def test_an_offer_carries_its_own_permission_question():
    assert redraft.reasons(offer("act_choice_point"), ["x"], registry(), offer_not_allowed=False, needs_question=True) == []


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
