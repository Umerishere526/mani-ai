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


def test_an_offer_that_depends_on_what_it_meant_waits_and_says_why():
    why = redraft.reasons(offer("act_choice_point"), ["i felt embarrassed"], registry(), offer_not_allowed=False, earliest_wait=True)
    assert len(why) == 1 and "what they took it to mean" in why[0] and "ACT Choice Point" in why[0]


def test_a_feeling_or_size_they_never_gave_is_a_reason():
    feeling = redraft.reasons(Reply(text="That sounds stressful. What do you need first?"), ["i have an exam"], registry(), offer_not_allowed=False)
    size = redraft.reasons(Reply(text="You have a lot on your plate."), ["i have an exam"], registry(), offer_not_allowed=False)

    assert len(feeling) == 1 and "stressful" in feeling[0]
    assert len(size) == 1 and "a lot" in size[0]
    assert all("ask " not in note for note in (*feeling, *size))


def test_their_own_feeling_or_size_word_may_come_back():
    said = ["i am stressed, there is a lot to do"]
    draft = Reply(text="You are stressed, with a lot to do. What comes first?")

    assert redraft.reasons(draft, said, registry(), offer_not_allowed=False) == []


def test_a_reply_that_asks_nothing_or_asks_again_is_not_a_reason():
    """The model's to get right from its instructions; the code does not redraft it."""
    for text in (
        "It is okay to feel that way. I am here with you.",
        "Which part of the exam feels most urgent?",
    ):
        assert redraft.reasons(Reply(text=text), ["i have an exam"], registry(), offer_not_allowed=False) == []


def test_the_offer_veto_notes_do_not_tell_the_model_to_ask_a_question():
    too_early = redraft.reasons(offer("act_choice_point"), ["x"], registry(), offer_not_allowed=False, earliest_wait=True)
    not_allowed = redraft.reasons(offer("act_choice_point"), ["x"], registry(), offer_not_allowed=True)
    ruled_out = redraft.reasons(offer("behavioral_activation"), ["my dog died"], registry(), offer_not_allowed=False)

    notes = [*too_early, *not_allowed, *ruled_out]
    assert len(notes) == 3
    assert all("ask " not in note for note in notes)
