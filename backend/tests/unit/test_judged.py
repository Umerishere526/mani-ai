# ABOUTME: Safety from the turn's reply, through the pause rules muhammad set on 2026-11-13, 11-14 and 11-16: never a
# ABOUTME: pause on the first danger message, the body only on a refused help, and the first message back never.

import uuid

from mani.chat.judged import danger_value, judge, safety_record
from mani.chat.pause import ReturnCheck
from mani.chat.reply import Safety
from mani.chat.safety import State

CHECK = ReturnCheck(pause_id=uuid.UUID("00000000-0000-4000-8000-0000000000b1"), kind="paused_thread", reason="pills")


def judged(before: State, read: Safety, record: dict | None = None, **given):
    return judge(before, read, record or {}, **{"return_check": None, "answering_return": None, **given})


def test_the_levels_map_onto_the_pause_rules_values():
    assert [danger_value(level) for level in ("none", "unsure", "danger")] == ["none", "unsure", "now"]


def test_a_first_danger_message_in_a_clear_conversation_never_pauses():
    j = judged(State.CLEAR, Safety(level="danger", about="themselves"))
    assert j.state_after is State.DANGER and j.pausing is False


def test_danger_that_goes_on_after_mani_answered_it_pauses():
    assert judged(State.DANGER, Safety(level="danger", about="themselves")).pausing is True


def test_help_in_place_never_pauses():
    assert judged(State.DANGER, Safety(level="danger", about="themselves", help_in_place=True)).pausing is False


def test_a_body_symptom_pauses_only_when_happening_now_and_help_is_refused():
    assert judged(State.DANGER, Safety(level="danger", about="body", symptom_now="yes")).pausing is False
    assert judged(State.DANGER, Safety(level="danger", about="body", symptom_now="yes", declined=True)).pausing is True


def test_the_first_message_back_after_a_pause_never_pauses():
    j = judged(State.CLEAR, Safety(level="danger", about="themselves"), return_check=CHECK)
    assert j.pausing is False


def test_after_the_return_check_only_danger_still_there_pauses():
    assert judged(State.DANGER, Safety(level="danger", about="themselves"), answering_return="p").pausing is False
    still = Safety(level="danger", about="themselves", still_there=True)
    assert judged(State.DANGER, still, answering_return="p").pausing is True


def test_a_worry_that_settles_is_recorded_settled():
    j = judged(State.UNSURE, Safety(level="none"))
    assert j.settled_now is True and j.state_after is State.CLEAR


def test_the_record_keeps_whose_danger_was_reached_and_the_return_check_asked():
    j = judged(State.DANGER, Safety(level="danger", about="themselves"))
    after = safety_record({}, return_check=CHECK, answering_return=None, judged=j, read_about="themselves")
    assert after["danger_reached"] is True and after["danger_about"] == "themselves"
    assert after["return_check"] == {"pause": str(CHECK.pause_id), "state": "asked"}


def test_code_raises_a_body_worry_the_model_held_lower_and_says_so():
    """The call-now line is added only when code raised the turn: the model's own danger reply already says it."""
    held_lower = Safety(level="unsure", about="body", symptom_now="unsaid")
    raised = judged(State.CLEAR, held_lower)
    assert raised.state_after is State.DANGER and raised.body_emergency is True
    assert judged(State.CLEAR, Safety(level="danger", about="body", symptom_now="yes")).body_emergency is False
    assert judged(State.DANGER, held_lower, {"danger_about": "body"}).body_emergency is False, "once per body worry"
    assert judged(State.DANGER, held_lower, {"danger_about": "themselves"}).body_emergency is True, (
        "the final review, 2026-11-18: chest pain after an overdose went out with no call-now line")
