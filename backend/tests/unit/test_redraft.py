# ABOUTME: Checks which drafted replies are asked for again, and for what reason.
# ABOUTME: Each reason is a rule about the person, the cadence or what the facts point to, so each is a plain test.

from mani.chat import redraft
from mani.chat.router import Fit
from mani.chat.techniques import Registry
from mani.llm.schema import Reply, SmartPrompt
from mani.models.rows import Framework


def _framework(framework_id: str, name: str, **activation) -> Framework:
    return Framework(
        id=framework_id, name=name, summary="s", body="b", phases=["offering"],
        activation=activation,
        stages={"offering": {
            "purpose": f"Offer {name}.",
            "ask": {"supportive": f"Would {name} help?"},
        }},
    )


def registry() -> Registry:
    stop = _framework("dbt_stop", "DBT STOP")
    stop.stages["offering"]["panic"] = {
        "purpose": "Say back what is happening right now.",
        "ask": {"supportive": "Would it help to pause here with me?"},
    }
    return Registry([
        _framework("abcde", "ABCDE"),
        _framework("behavioral_activation", "Behavioral Activation", never_offer_when_said=["died"]),
        _framework("structured_problem_solving", "Structured Problem-Solving"),
        _framework("act_choice_point", "ACT Choice Point"),
        stop,
    ])


def offer(technique: str) -> Reply:
    return Reply(
        text="There are some questions we could go through. Would you like to try it?",
        prompts=[SmartPrompt(label="Try it", technique=technique), SmartPrompt(label="Keep chatting", decline=True)],
    )


ABCDE_FITS = Fit(frozenset({"event", "meaning"}), pick="abcde")
EVENT_ONLY = Fit(frozenset({"event"}), leading="abcde", missing="meaning")
NOTHING = Fit(frozenset())


def test_a_clean_question_stands():
    draft = Reply(text="What is the hardest part of the evenings?")
    assert redraft.reasons(draft, ["i'm lonely"], registry(), fit=NOTHING) == []


# ---------------------------------------------------------------------------
# The ordered chain of offer reasons (spec 0005, AC-7)
# ---------------------------------------------------------------------------


def test_a_scripted_phrase_is_a_reason_even_when_the_person_used_it():
    draft = Reply(text="It sounds like the concert got in the way. What happened?")
    reasons = redraft.reasons(draft, ["It sounds like I messed up"], registry())
    assert len(reasons) == 1
    assert "'it sounds like'" in reasons[0]


def test_1_showing_again_the_offer_they_asked_about_is_no_new_offer():
    why = redraft.reasons(
        offer("abcde"), ["what would that involve?"], registry(), fit=NOTHING,
        clear_ok=False, waiting="abcde", asked_about_waiting=True,
    )
    assert why == []


def test_1_showing_again_an_offer_they_typed_past_needs_the_usual_window():
    why = redraft.reasons(
        offer("abcde"), ["i keep replaying it"], registry(), fit=NOTHING,
        clear_ok=False, waiting="abcde",
    )
    assert len(why) == 1 and "not allowed yet" in why[0]


def test_2_an_offer_before_the_cadence_allows_it_is_a_reason():
    why = redraft.reasons(offer("abcde"), ["x"], registry(), fit=ABCDE_FITS, clear_ok=False)
    assert len(why) == 1 and "not allowed yet" in why[0]


def test_2_an_offer_during_a_cooldown_is_not_allowed_even_when_nothing_fits():
    """Checked before the facts, so it is never told to ask what is happening after the whole
    story has been told."""
    why = redraft.reasons(offer("abcde"), ["x"], registry(), fit=EVENT_ONLY, clear_ok=False)
    assert len(why) == 1 and "not allowed yet" in why[0]


def test_2_an_offer_what_they_said_rules_out_is_a_reason():
    fits = Fit(frozenset({"low_mood"}), pick="abcde")
    why = redraft.reasons(offer("behavioral_activation"), ["my dog died"], registry(), fit=fits)
    assert len(why) == 1 and "Behavioral Activation" in why[0] and "Never offer one when" in why[0]
    assert redraft.ruled_out(offer("behavioral_activation"), ["my dog died"], registry()) == "behavioral_activation"


def test_2_the_manager_chat_at_its_second_message_is_too_early_not_redirected():
    """ABCDE waits for the third message, so an offer of it at the second is held, never
    turned into another framework."""
    why = redraft.reasons(
        offer("abcde"), ["my manager embarrassed me today because he wants me to fail"], registry(),
        fit=ABCDE_FITS, earliest_ok=lambda framework_id: framework_id != "abcde",
    )
    assert len(why) == 1 and "ABCDE too early" in why[0]


def test_3_an_offer_the_facts_disagree_with_is_redirected_to_the_pick():
    why = redraft.reasons(offer("structured_problem_solving"), ["x"], registry(), fit=ABCDE_FITS)
    assert len(why) == 1
    assert why[0].startswith("the facts you listed point to ABCDE (`abcde`): offer that instead")
    assert "Would ABCDE help?" in why[0]


def test_3_a_panicked_person_is_redirected_to_stops_panic_wording():
    panicked = Fit(frozenset({"overwhelmed_now"}), pick="dbt_stop")
    why = redraft.reasons(offer("act_choice_point"), ["x"], registry(), fit=panicked)
    assert len(why) == 1 and "point to DBT STOP" in why[0]
    assert "Would it help to pause here with me?" in why[0]
    assert "Would DBT STOP help?" not in why[0]


def test_3_about_to_act_keeps_stops_action_wording():
    acting = Fit(frozenset({"overwhelmed_now", "about_to_act"}), pick="dbt_stop")
    why = redraft.reasons(offer("act_choice_point"), ["x"], registry(), fit=acting)
    assert "Would DBT STOP help?" in why[0]


def test_3_a_pick_that_may_not_be_offered_yet_means_offer_nothing():
    why = redraft.reasons(
        offer("structured_problem_solving"), ["x"], registry(), fit=ABCDE_FITS,
        earliest_ok=lambda framework_id: framework_id != "abcde",
    )
    assert len(why) == 1 and "not allowed yet" in why[0]


def test_5_offering_a_framework_they_only_point_to_is_told_to_ask_what_it_needs():
    """covers spec 0005 AC-16: the leading framework is never offered, only asked toward."""
    why = redraft.reasons(offer("abcde"), ["x"], registry(), fit=EVENT_ONLY)
    assert len(why) == 1
    assert why[0].startswith("nothing they have said fits a set of questions yet: offer nothing")
    assert "what they took that event to mean" in why[0]


def test_5_offering_another_framework_when_nothing_fits_gets_the_same_reason():
    why = redraft.reasons(offer("act_choice_point"), ["x"], registry(), fit=EVENT_ONLY)
    assert len(why) == 1 and why[0].startswith("nothing they have said fits")
    assert "nearest" not in why[0]


def test_5_with_no_fact_at_all_it_asks_what_is_happening():
    why = redraft.reasons(offer("structured_problem_solving"), ["x"], registry(), fit=NOTHING)
    assert len(why) == 1 and "ask what is happening for them" in why[0]


def test_6_not_offering_a_framework_that_fits_when_an_offer_is_due_is_a_reason():
    why = redraft.reasons(Reply(text="What else?"), ["x"], registry(), fit=ABCDE_FITS, offer_due=True)
    assert len(why) == 1 and why[0].startswith("you have talked for several replies and not offered: offer ABCDE")


def test_6_a_framework_they_only_point_to_is_never_asked_for():
    """covers spec 0005 AC-16: an event alone leads to ABCDE, which is still never offered."""
    assert redraft.reasons(Reply(text="What else?"), ["x"], registry(), fit=EVENT_ONLY, offer_due=True) == []


def test_6_with_no_fact_nothing_is_forced_when_due():
    assert redraft.reasons(Reply(text="What else?"), ["x"], registry(), fit=NOTHING, offer_due=True) == []


def test_6_a_due_offer_is_not_asked_for_while_pain_may_be_physical():
    why = redraft.reasons(Reply(text="Is it in your body?"), ["i'm in pain"], registry(), fit=ABCDE_FITS, offer_due=True)
    assert why == []


def test_a_turn_whose_facts_are_not_read_keeps_the_cadence_checks_only():
    assert redraft.reasons(offer("abcde"), ["x"], registry(), fit=None) == []
    assert redraft.reasons(Reply(text="What else?"), ["x"], registry(), fit=None, offer_due=True) == []


def test_only_the_pick_may_be_offered():
    assert redraft.offers_the_pick("abcde", ABCDE_FITS)
    assert not redraft.offers_the_pick("abcde", EVENT_ONLY)
    assert not redraft.offers_the_pick("act_choice_point", ABCDE_FITS)
    assert not redraft.offers_the_pick("abcde", NOTHING)
    assert redraft.offers_the_pick("abcde", None)


# ---------------------------------------------------------------------------
# Words they never used
# ---------------------------------------------------------------------------


def test_a_feeling_or_size_they_never_gave_is_a_reason():
    feeling = redraft.reasons(Reply(text="That sounds stressful. What do you need first?"), ["i have an exam"], registry())
    size = redraft.reasons(Reply(text="You have a lot on your plate."), ["i have an exam"], registry())

    assert len(feeling) == 1 and "stressful" in feeling[0]
    assert len(size) == 1 and "a lot" in size[0]
    assert all("ask " not in note for note in (*feeling, *size))


def test_their_own_feeling_or_size_word_may_come_back():
    said = ["i am stressed, there is a lot to do"]
    draft = Reply(text="You are stressed, with a lot to do. What comes first?")

    assert redraft.reasons(draft, said, registry()) == []


def test_a_reply_that_asks_nothing_or_asks_again_is_not_a_reason():
    """The model's to get right from its instructions; the code does not redraft it."""
    for text in (
        "It is okay to feel that way. Take your time.",
        "Which part of the exam feels most urgent?",
    ):
        assert redraft.reasons(Reply(text=text), ["i have an exam"], registry()) == []


def test_the_offer_veto_notes_do_not_tell_the_model_to_ask_a_question():
    too_early = redraft.reasons(offer("abcde"), ["x"], registry(), fit=ABCDE_FITS, earliest_ok=lambda _: False)
    not_allowed = redraft.reasons(offer("abcde"), ["x"], registry(), fit=ABCDE_FITS, clear_ok=False)
    ruled_out = redraft.reasons(offer("behavioral_activation"), ["my dog died"], registry(), fit=ABCDE_FITS)

    notes = [*too_early, *not_allowed, *ruled_out]
    assert len(notes) == 3
    assert all("ask " not in note for note in notes)
