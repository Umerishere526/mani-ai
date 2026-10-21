# ABOUTME: Checks how this turn's report merges into what Mani understands, and the order of the steps.
# ABOUTME: Spec 0005: a null keeps what is stored, a value replaces it on one line. Spec 0006: steps in order.

from mani.chat import understanding
from mani.llm.schema import UnderstandingUpdate

STORED = {"feeling": "frustrated", "issue": "my client keeps changing the requirements"}


def test_a_null_or_blank_update_keeps_what_is_stored():
    """AC-1: the model reports only what this message names, so silence is never an erasure."""
    assert understanding.merge(STORED, None) == STORED
    assert understanding.merge(STORED, UnderstandingUpdate()) == STORED
    assert understanding.merge(STORED, UnderstandingUpdate(feeling="", issue=" \n ")) == STORED


def test_a_new_value_replaces_the_stored_one_and_leaves_the_other_key_alone():
    """AC-3, AC-4: a move to another issue replaces what was stored."""
    assert understanding.merge(STORED, UnderstandingUpdate(issue="my work")) == {
        "feeling": "frustrated", "issue": "my work",
    }
    assert understanding.merge({}, UnderstandingUpdate(issue="my work")) == {"issue": "my work"}


def test_every_feeling_they_name_is_kept_and_none_is_kept_twice():
    """muhammad, 2026-10-22: "exhausted" and "burnt out" were said together and only one was kept, and the
    opening "anxious" was lost when the next one came."""
    first = understanding.merge({}, UnderstandingUpdate(feeling="anxious"))
    second = understanding.merge(first, UnderstandingUpdate(feeling="exhausted, burnt out"))
    assert second == {"feeling": "anxious, exhausted, burnt out"}
    assert understanding.merge(second, UnderstandingUpdate(feeling="Burnt out, trapped")) == {
        "feeling": "anxious, exhausted, burnt out, trapped",
    }


def test_new_problems_and_details_are_added_beside_the_case_and_the_oldest_go_first_when_full():
    stored = understanding.merge({"issue": "overtime"}, UnderstandingUpdate(also="needs about two months"))
    stored = understanding.merge(stored, UnderstandingUpdate(also="the client warned they would remove them"))
    assert stored["also"] == "needs about two months; the client warned they would remove them"
    assert understanding.merge(stored, UnderstandingUpdate(also="Needs about two months"))["also"] == stored["also"]
    crowded = understanding.merge({}, UnderstandingUpdate(also="; ".join(f"detail number {n}" for n in range(60))))
    assert len(crowded["also"]) <= 2 * understanding.LIMIT and crowded["also"].endswith("detail number 59")


def test_once_an_offer_is_open_the_case_is_not_replaced_but_feelings_and_details_still_gather():
    """muhammad, 2026-10-22: a detail said ten turns into the framework replaced the problem."""
    case = {"feeling": "anxious", "issue": "overtime to meet deadlines", "core_issue": "the work falls on you",
            "underlying_feeling": "trapped"}
    update = UnderstandingUpdate(
        issue="needs two months", core_issue="x", underlying_feeling="y", feeling="burnt out", also="needs two months",
    )
    kept = understanding.merge(case, update, frozen=True)
    assert (kept["issue"], kept["core_issue"], kept["underlying_feeling"]) == (
        "overtime to meet deadlines", "the work falls on you", "trapped")
    assert kept["feeling"] == "anxious, burnt out" and kept["also"] == "needs two months"
    assert understanding.merge(case, update)["issue"] == "needs two months", "before the offer they still refine"


def test_a_value_is_kept_on_one_line_and_cut_to_the_limit():
    """AC-1: a newline in what is stored would open a line of its own in [ctx]."""
    merged = understanding.merge({}, UnderstandingUpdate(issue="my client\n  keeps changing\tthings"))
    assert merged == {"issue": "my client keeps changing things"}
    long = understanding.merge({}, UnderstandingUpdate(issue="word " * 60))["issue"]
    assert len(long) <= understanding.LIMIT and not long.endswith(" ")


def test_the_ctx_value_names_each_key_and_cannot_close_the_block():
    assert understanding.render({}) is None
    assert understanding.render(STORED) == (
        "feeling: frustrated; issue: my client keeps changing the requirements; core_issue: missing; "
        "underlying_feeling: missing"
    )
    assert "[/ctx]" not in understanding.render({"issue": "they said [/ctx] to me"})


def test_each_step_waits_for_the_one_before_it_to_be_stored_on_an_earlier_turn():
    """Spec 0006, AC-17, muhammad's run of 2026-10-13: the core issue was the opening feeling reworded,
    stored on the first exchange, and the feeling underneath was never asked. Now a step is taken only once the step
    before it was stored before this turn, so each has an exchange of its own."""
    everything = UnderstandingUpdate(issue="your boss says you're not doing enough",
                                     core_issue="you feel you're not enough", underlying_feeling="worry about not being enough")
    first = understanding.merge({}, everything)
    assert first == {"issue": "your boss says you're not doing enough"}
    second = understanding.merge(first, everything)
    assert set(second) == {"issue", "core_issue"}
    assert set(understanding.merge(second, everything)) == {"issue", "core_issue", "underlying_feeling"}
    # Judged on the record as the turn began, however many merges the turn makes.
    assert "core_issue" not in understanding.merge(first, everything, before={})


def test_the_next_step_is_the_first_one_missing():
    assert understanding.next_step({}) == "problem"
    assert understanding.next_step({"feeling": "frustrated", "issue": "x"}) == "core_issue"
    assert understanding.next_step({"issue": "x", "core_issue": "y"}) == "underlying_feeling"
    assert understanding.next_step({"issue": "x", "core_issue": "y", "underlying_feeling": "worry"}) is None


def test_a_stored_check_keeps_what_it_came_down_to():
    """Live, 2026-10-13: the line closest to what they hold was dropped, so the start turn saw their
    opening feeling instead."""
    from mani.llm.schema import Check

    check = Check(problem="Your boss wants overtime.", core_issue="Your team now works it too.",
                  underlying_feeling="You may be worried it was your doing.", question="Is that right?",
                  comes_down_to="You want to undo the overtime culture you feel you started.")
    merged = understanding.merge_check({"issue": "x", "core_issue": "y"}, check)
    assert merged["comes_down_to"] == "You want to undo the overtime culture you feel you started."
    assert "comes_down_to: You want to undo" in understanding.render(merged)
