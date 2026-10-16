# ABOUTME: Checks how this turn's report merges into what Mani understands, and the order of the steps.
# ABOUTME: Spec 0005: a null keeps what is stored, a value replaces it on one line. Spec 0006: steps in order.

from mani.chat import understanding
from mani.llm.schema import Check, UnderstandingUpdate

STORED = {"feeling": "frustrated", "issue": "my client keeps changing the requirements"}


def test_a_null_or_blank_update_keeps_what_is_stored():
    """AC-1: the model reports only what this message names, so silence is never an erasure."""
    assert understanding.merge(STORED, None) == STORED
    assert understanding.merge(STORED, UnderstandingUpdate()) == STORED
    assert understanding.merge(STORED, UnderstandingUpdate(feeling="", issue=" \n ")) == STORED


def test_a_new_value_replaces_the_stored_one_and_leaves_the_other_key_alone():
    """Spec 0005 AC-3, AC-4: a move to another issue replaces what was stored. A different feeling is
    held for their yes instead (spec 0007, decision 8), the stored one untouched."""
    assert understanding.merge(STORED, UnderstandingUpdate(feeling="angry")) == {
        "feeling": "frustrated", "issue": STORED["issue"], "feeling_asked": "angry",
    }
    assert understanding.merge({}, UnderstandingUpdate(issue="my work")) == {"issue": "my work"}


def test_a_value_is_kept_on_one_line_and_cut_to_the_limit():
    """AC-1: a newline in what is stored would open a line of its own in [ctx]."""
    merged = understanding.merge({}, UnderstandingUpdate(issue="my client\n  keeps changing\tthings"))
    assert merged == {"issue": "my client keeps changing things"}
    long = understanding.merge({}, UnderstandingUpdate(issue="word " * 60))["issue"]
    assert len(long) <= understanding.LIMIT and not long.endswith(" ")


def test_what_they_feel_in_their_body_is_kept_and_shown_but_is_never_a_step():
    """A sensation named early stays for the body check-in, and it neither opens nor blocks the check."""
    kept = understanding.merge(STORED, UnderstandingUpdate(body="your chest gets tight"))
    assert kept["body"] == "your chest gets tight"
    assert "body: your chest gets tight" in understanding.render(kept)
    assert understanding.next_step(kept) == understanding.next_step(STORED)


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
    check = Check(problem="Your boss wants overtime.", core_issue="Your team now works it too.",
                  in_their_control="You'll raise it with HR.", question="Is that right?",
                  comes_down_to="You want to undo the overtime culture you feel you started.")
    merged = understanding.merge_check({"issue": "x", "core_issue": "y"}, check)
    assert merged["comes_down_to"] == "You want to undo the overtime culture you feel you started."
    assert "comes_down_to: You want to undo" in understanding.render(merged)


def test_a_check_with_nothing_it_comes_down_to_is_never_sent():
    """The client, 2026-10-16: what it comes down to is the only sentence of the check they read, so a check
    without it would ask its question with nothing before it."""
    full = Check(
        problem="your coworkers miss deadlines", core_issue="the work lands on you", in_their_control="not sure yet",
        comes_down_to="It comes down to carrying what others drop.", question="Have you been able to talk to them about it?",
    )
    assert understanding.usable(full)
    assert not understanding.usable(full.model_copy(update={"comes_down_to": "  "}))


def test_the_event_they_describe_is_kept_and_shown_but_is_never_a_step():
    """Spec 0007, AC-9: the event that started it is recorded from the first message that names it."""
    stored = understanding.merge({}, UnderstandingUpdate(event="your boss criticized your report in front of the team"))
    assert stored == {"event": "your boss criticized your report in front of the team"}
    assert understanding.next_step(stored) == "problem"
    assert understanding.render(stored) == (
        "event: your boss criticized your report in front of the team; issue: missing; "
        "core_issue: missing; in_their_control: missing"
    )


def test_a_replaced_issue_or_event_is_kept_in_the_history():
    """Spec 0007, AC-16: a change is corrected in place and what it replaced is kept, never rendered."""
    stored = {"issue": "the list", "history": {"issue": ["x"]}}
    merged = understanding.merge(stored, UnderstandingUpdate(issue="your partner doesn't help"))
    assert merged["issue"] == "your partner doesn't help"
    assert merged["history"] == {"issue": ["x", "the list"]}
    assert "history" not in understanding.render(merged)
    # The same value again is not a change, and an untracked key keeps no history.
    assert understanding.merge(merged, UnderstandingUpdate(issue="your partner doesn't help"))["history"] == merged["history"]
    assert "history" not in understanding.merge({"body": "tight chest"}, UnderstandingUpdate(body="sore neck"))
    assert "feeling_asked" in understanding.merge({"feeling_asked": "dread"}, None)


def test_a_changed_feeling_waits_for_their_yes():
    """Spec 0007 decision 8: a different feeling is asked about, stored on yes, dropped on no."""
    asked = understanding.merge(STORED, UnderstandingUpdate(feeling="dread"))
    assert asked["feeling"] == "frustrated" and asked["feeling_asked"] == "dread"
    stored = understanding.merge(asked, None, feeling_answer="yes")
    assert stored["feeling"] == "dread" and "feeling_asked" not in stored
    assert stored["history"]["feeling"] == ["frustrated"]
    assert "feeling_asked" not in understanding.merge(asked, None, feeling_answer="no")
    assert understanding.merge({}, UnderstandingUpdate(feeling="dread")) == {"feeling": "dread"}
    assert understanding.merge(asked, UnderstandingUpdate(feeling="panic"))["feeling_asked"] == "panic"
    assert "feeling_asked" not in understanding.render(asked)
    # The same word again is not a change, and an answer with nothing pending changes nothing.
    assert "feeling_asked" not in understanding.merge(STORED, UnderstandingUpdate(feeling="frustrated"))
    assert understanding.merge(STORED, None, feeling_answer="yes") == STORED
