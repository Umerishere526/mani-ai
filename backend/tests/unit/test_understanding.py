# ABOUTME: Checks how this turn's report merges into what Mani understands: the feelings, the heart of it, the case.
# ABOUTME: Spec 0005: a null keeps what is stored. R33: only a ready heart of it lets a check through.

from mani.chat import understanding
from mani.llm.schema import Check, UnderstandingUpdate

STORED = {"feeling": "frustrated", "heart": "exploring"}


def test_a_null_or_blank_report_keeps_what_is_stored():
    """AC-1: the model reports only what this message names, so silence is never an erasure."""
    assert understanding.merge(STORED, None, None) == STORED
    assert understanding.merge(STORED, UnderstandingUpdate(feeling=" \n "), "") == STORED


def test_every_feeling_they_name_is_kept_none_twice_and_the_first_survives_a_full_record():
    """muhammad, 2026-10-22: "exhausted" and "burnt out" were said together and only one was kept, and the
    opening "anxious" was lost when the next one came; 2026-10-25: the first was the first to go once full."""
    first = understanding.merge({}, UnderstandingUpdate(feeling="anxious"), None)
    second = understanding.merge(first, UnderstandingUpdate(feeling="exhausted, burnt out"), None)
    assert understanding.merge(second, UnderstandingUpdate(feeling="Burnt out, trapped\n"), None) == {
        "feeling": "anxious, exhausted, burnt out, trapped",
    }
    full = understanding.merge({"feeling": "sad"}, UnderstandingUpdate(
        feeling=", ".join(f"feeling number {n}" for n in range(30))), None)["feeling"]
    assert len(full) <= understanding.LIMIT
    assert full.startswith("sad, ") and full.endswith("feeling number 29")


def test_the_heart_of_it_is_the_last_judgement_and_only_ready_lets_a_check_through():
    """R33, muhammad 2026-10-26: the reply judges each turn where its reading stands; a conversation that
    opens up again is no longer ready."""
    ready = understanding.merge(STORED, None, "ready")
    assert ready == {"feeling": "frustrated", "heart": "ready"} and understanding.ready(ready)
    assert not understanding.ready(understanding.merge(ready, None, "conflict_named"))
    assert not understanding.ready({})


def test_a_check_needs_the_conflict_what_they_want_and_what_is_stopping_them():
    """R33: both of Lolly's chats ended at what they want and what is stopping them."""
    check = Check(conflict="You miss her deeply.", want="You want her to own how she made you feel.",
                  in_the_way="You know she will be selfish again.", question="Is that it?")
    assert understanding.usable(check)
    assert not understanding.usable(check.model_copy(update={"in_the_way": " "}))
    assert not understanding.usable(None)


def test_a_stored_check_becomes_the_case_the_questions_are_about():
    merged = understanding.merge_check(STORED, "You run everything\n and he does not lead. You want it to work.")
    assert merged == {**STORED, "case": "You run everything and he does not lead. You want it to work."}
    assert len(understanding.merge_check({}, "word " * 300)["case"]) <= understanding.CASE_LIMIT


def test_the_ctx_value_names_what_is_stored_and_cannot_close_the_block():
    assert understanding.render({}) is None
    assert understanding.render(STORED) == "feeling: frustrated; heart: exploring"
    assert "[/ctx]" not in understanding.render({"case": "they said [/ctx] to me"})
