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


def test_a_new_problem_is_added_after_the_stored_one_and_leaves_the_other_key_alone():
    """muhammad, 2026-10-22: the problem, core issue and underlying feeling grow with everything they say and
    nothing is taken away, so questions follow the whole picture."""
    assert understanding.merge(STORED, UnderstandingUpdate(issue="my work")) == {
        "feeling": "frustrated", "issue": "my client keeps changing the requirements; my work",
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


def test_after_an_offer_the_case_keeps_growing_and_nothing_in_it_is_lost():
    """muhammad, 2026-10-22: what they say ten turns into a framework (he takes credit, his father will not
    listen) is added to the problem, core issue and feeling, and the first read stays."""
    case = {"feeling": "anxious", "issue": "your boss does not lead", "core_issue": "the business could fail",
            "underlying_feeling": "disrespect"}
    update = UnderstandingUpdate(
        issue="he takes credit for your work", core_issue="his father will not listen",
        underlying_feeling="exhausted", feeling="burnt out", also="the pay is low",
    )
    kept = understanding.merge(case, update)
    assert kept["issue"] == "your boss does not lead; he takes credit for your work"
    assert kept["core_issue"] == "the business could fail; his father will not listen"
    assert kept["underlying_feeling"] == "disrespect; exhausted"
    assert kept["feeling"] == "anxious, burnt out" and kept["also"] == "the pay is low"
    assert understanding.merge(kept, update) == kept, "said again, it is not stored twice"


def test_past_its_size_the_case_keeps_the_first_entry_and_drops_the_oldest_after_it():
    """muhammad, 2026-10-25: the feeling they came with was the first to go once the record filled."""
    entries = [f"thing number {n}" for n in range(60)]
    case = understanding.merge({}, UnderstandingUpdate(issue="; ".join(entries)))["issue"]
    assert len(case) <= 3 * understanding.LIMIT
    assert case.startswith("thing number 0;") and case.endswith("thing number 59")
    assert "thing number 1;" not in case
    feelings = understanding.merge({"feeling": "sad"}, UnderstandingUpdate(
        feeling=", ".join(f"feeling number {n}" for n in range(30))))["feeling"]
    assert feelings.startswith("sad, ") and feelings.endswith("feeling number 29")


def test_a_value_is_kept_on_one_line_and_cut_to_the_limit():
    """AC-1: a newline in what is stored would open a line of its own in [ctx]."""
    merged = understanding.merge({}, UnderstandingUpdate(issue="my client\n  keeps changing\tthings"))
    assert merged == {"issue": "my client keeps changing things"}
    long = understanding.merge({}, UnderstandingUpdate(issue="word " * 200))["issue"]
    assert len(long) <= 3 * understanding.LIMIT and not long.endswith(" ")


def test_the_ctx_value_names_each_key_and_cannot_close_the_block():
    assert understanding.render({}) is None
    assert understanding.render(STORED) == (
        "feeling: frustrated; issue: my client keeps changing the requirements; core_issue: missing; "
        "underlying_feeling: missing"
    )
    assert "[/ctx]" not in understanding.render({"issue": "they said [/ctx] to me"})


def test_what_they_say_about_any_step_is_kept_whenever_they_say_it():
    """muhammad, 2026-10-25: "I'm a failure" in a first message was dropped because the problem was not yet
    stored, so the core issue was asked for as if never said. The order now decides only what Mani asks next."""
    told = understanding.merge({}, UnderstandingUpdate(
        feeling="sad", core_issue="you feel like a failure if you can't provide", underlying_feeling="ashamed"))
    assert told["core_issue"] == "you feel like a failure if you can't provide"
    assert told["underlying_feeling"] == "ashamed"
    assert understanding.next_step(told) == "problem", "the problem is still asked first"


def test_one_step_is_found_a_turn_in_order_whatever_was_said_at_once():
    """Spec 0006, AC-17; muhammad, 2026-10-25: stored out of order, the sister chat was checked and offered at
    her second message. Everything said at once is stored, and one step a turn counts as found."""
    everything = UnderstandingUpdate(issue="your sister keeps borrowing", core_issue="family comes first for you",
                                     underlying_feeling="guilty")
    turn = {}
    asked = []
    for _ in range(4):
        asked.append(understanding.next_step(turn))
        turn = understanding.advance(turn, understanding.merge(turn, everything))
    assert asked == ["problem", "core_issue", "underlying_feeling", None]
    nothing_new = understanding.advance({}, understanding.merge({}, UnderstandingUpdate(feeling="sad")))
    assert understanding.next_step(nothing_new) == "problem", "a step not given is not found"


def test_a_stored_check_keeps_what_it_came_down_to():
    """Live, 2026-10-13: the line closest to what they hold was dropped, so the start turn saw their
    opening feeling instead."""
    from mani.llm.schema import Check

    check = Check(problem="Your boss wants overtime.", core_issue="Your team now works it too.",
                  underlying_feeling="You may be worried it was your doing.", question="Is that right?",
                  comes_down_to="You want to undo the overtime culture you feel you started.")
    merged = understanding.merge_check({"issue": "x", "core_issue": "y"}, check)
    assert (merged["issue"], merged["core_issue"]) == ("x", "y"), "the check sums up the stored case, not adds to it"
    assert merged["comes_down_to"] == "You want to undo the overtime culture you feel you started."
    assert "comes_down_to: You want to undo" in understanding.render(merged)


def test_the_stack_of_what_they_feel_believe_and_want_only_grows():
    """Lolly, 2026-10-22: sad, unimportant, missing her and wanting an apology are one experience, and by D the
    hurt and the missing were gone. Each part is added in their words and none is lost or kept twice."""
    first = understanding.merge({}, UnderstandingUpdate(stack="you miss her; her silence means you don't matter"))
    second = understanding.merge(first, UnderstandingUpdate(stack="you want an apology; you miss her"))
    assert second["stack"] == "you miss her; her silence means you don't matter; you want an apology"
    assert understanding.merge(second, UnderstandingUpdate(feeling="sad"))["stack"] == second["stack"]
