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
    """AC-3, AC-4: a different feeling, or a move to another issue, replaces what was stored."""
    assert understanding.merge(STORED, UnderstandingUpdate(feeling="angry")) == {
        "feeling": "angry", "issue": STORED["issue"],
    }
    assert understanding.merge({}, UnderstandingUpdate(issue="my work")) == {"issue": "my work"}


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
        "in_their_control: missing"
    )
    assert "[/ctx]" not in understanding.render({"issue": "they said [/ctx] to me"})


def test_each_step_waits_for_the_one_before_it_to_be_stored_on_an_earlier_turn():
    """Spec 0006, AC-17, muhammad's run of 2026-10-13: the core issue was the opening feeling reworded,
    stored on the first exchange, and control was never asked. Now a step is taken only once the step
    before it was stored before this turn, so each has an exchange of its own."""
    everything = UnderstandingUpdate(issue="your boss says you're not doing enough",
                                     core_issue="you feel you're not enough", in_their_control="ask him")
    first = understanding.merge({}, everything)
    assert first == {"issue": "your boss says you're not doing enough"}
    second = understanding.merge(first, everything)
    assert set(second) == {"issue", "core_issue"}
    assert set(understanding.merge(second, everything)) == {"issue", "core_issue", "in_their_control"}
    # Judged on the record as the turn began, however many merges the turn makes.
    assert "core_issue" not in understanding.merge(first, everything, before={})


def test_the_next_step_is_the_first_one_missing():
    assert understanding.next_step({}) == "problem"
    assert understanding.next_step({"feeling": "frustrated", "issue": "x"}) == "core_issue"
    assert understanding.next_step({"issue": "x", "core_issue": "y"}) == "control"
    assert understanding.next_step({"issue": "x", "core_issue": "y", "in_their_control": "not sure"}) is None


def test_a_stored_check_keeps_what_it_came_down_to():
    """Live, 2026-10-13: the line closest to what they hold was dropped, so the start turn saw their
    opening feeling instead."""
    from mani.llm.schema import Check

    check = Check(problem="Your boss wants overtime.", core_issue="Your team now works it too.",
                  in_their_control="You'll raise it with HR.", question="Is that right?",
                  comes_down_to="You want to undo the overtime culture you feel you started.")
    merged = understanding.merge_check({"issue": "x", "core_issue": "y"}, check)
    assert merged["comes_down_to"] == "You want to undo the overtime culture you feel you started."
    assert "comes_down_to: You want to undo" in understanding.render(merged)
