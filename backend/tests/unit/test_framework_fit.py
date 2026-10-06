# ABOUTME: Checks the client's selection table applied to reported facts: what fits, the tie rules, and what is missing.
# ABOUTME: Driven by the shipped fits_when content and fake fact lists, so no model call is needed.

import pytest

from mani.chat.router import choose, kept_facts
from scripts.seed import FRAMEWORKS_DIR, parse_framework

_SHIPPED = [parse_framework(path) for path in sorted(FRAMEWORKS_DIR.glob("*.md"))]
ACTIVATIONS = {f["id"]: f["activation"] for f in _SHIPPED}
ORDER = {f["id"]: f["display_order"] for f in _SHIPPED}


def fit(*facts: str, excluded: frozenset[str] = frozenset()):
    return choose(frozenset(facts), ACTIVATIONS, ORDER, excluded=excluded)


# ---------------------------------------------------------------------------
# Only facts in their own words count (AC-2)
# ---------------------------------------------------------------------------


def test_a_fact_quoted_from_their_message_is_kept():
    kept = kept_facts([("overwhelmed_now", "might have a panic attack")], ["I feel like I might have a panic attack."])
    assert kept.present == {"overwhelmed_now"} and kept.notes == []


def test_a_fact_quoted_only_from_mani_is_dropped():
    # The person's messages are the only ones passed in; Mani's words are never searched.
    kept = kept_facts([("event", "your manager criticised you")], ["it was a bad day"])
    assert kept.present == frozenset()
    assert kept.notes == ["dropped a fact not in their words: event"]


def test_a_quote_spanning_two_messages_is_dropped():
    kept = kept_facts([("event", "bad day my manager")], ["it was a bad day", "my manager shouted"])
    assert kept.present == frozenset()


def test_a_one_word_quote_is_dropped():
    kept = kept_facts([("meaning", "useless")], ["i feel useless"])
    assert kept.present == frozenset()


def test_an_unknown_fact_is_dropped_and_noted():
    kept = kept_facts([("sad_mood", "very sad today")], ["i am very sad today"])
    assert kept.present == frozenset()
    assert kept.notes == ["dropped an unknown fact: sad_mood"]


def test_case_and_punctuation_do_not_matter():
    kept = kept_facts([("meaning", "He wants me to FAIL")], ["my manager embarrassed me, he wants me to fail!"])
    assert kept.present == {"meaning"}


def test_panic_from_three_messages_ago_no_longer_counts():
    messages = ["I think I might have a panic attack", "it passed a bit", "now I am just tired"]
    kept = kept_facts([("overwhelmed_now", "might have a panic attack")], messages)
    assert kept.present == frozenset()


def test_an_older_event_still_counts():
    messages = ["my manager embarrassed me today", "it passed a bit", "now I am just tired"]
    kept = kept_facts([("event", "my manager embarrassed me today")], messages)
    assert kept.present == {"event"}


# ---------------------------------------------------------------------------
# What fits, and the client's tie rules (AC-4)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("facts", "expected"),
    [
        (("event", "meaning"), "abcde"),
        (("painful_thought",), "thought_reframe"),
        (("low_mood",), "behavioral_activation"),
        (("cannot_begin",), "behavioral_activation"),
        (("practical_problem", "unsure_what_to_do"), "structured_problem_solving"),
        (("cannot_control",), "act_choice_point"),
        (("overwhelmed_now",), "dbt_stop"),
        (("about_to_act",), "dbt_stop"),
    ],
)
def test_each_framework_fits_on_its_own_facts(facts, expected):
    assert fit(*facts).pick == expected


def test_about_to_act_goes_first_over_everything():
    assert fit("about_to_act", "practical_problem", "unsure_what_to_do").pick == "dbt_stop"


def test_overwhelmed_right_now_goes_before_reflection():
    assert fit("overwhelmed_now", "cannot_control").pick == "dbt_stop"
    assert fit("overwhelmed_now", "event", "meaning").pick == "dbt_stop"


def test_panic_about_a_practical_problem_stays_with_problem_solving():
    """ADR 010's lost wallet chat: panicking, and still able to work through what to do."""
    assert fit("overwhelmed_now", "practical_problem", "unsure_what_to_do").pick == "structured_problem_solving"


def test_knowing_but_not_starting_goes_to_activation_over_problem_solving_and_act():
    assert fit("cannot_begin", "practical_problem", "unsure_what_to_do").pick == "behavioral_activation"
    assert fit("cannot_begin", "cannot_control").pick == "behavioral_activation"


def test_what_cannot_be_controlled_goes_to_act():
    assert fit("cannot_control", "practical_problem", "unsure_what_to_do").pick == "act_choice_point"
    assert fit("cannot_control", "event", "meaning").pick == "act_choice_point"
    assert fit("cannot_control", "painful_thought").pick == "act_choice_point"


def test_not_knowing_what_to_do_goes_to_problem_solving_over_low_mood():
    assert fit("low_mood", "practical_problem", "unsure_what_to_do").pick == "structured_problem_solving"


def test_a_named_event_goes_to_abcde_over_a_thought():
    assert fit("event", "meaning", "painful_thought").pick == "abcde"


def test_a_rule_never_promotes_a_framework_that_does_not_fit():
    """An event with no meaning does not make ABCDE fit, so the thought is the fit."""
    assert fit("event", "painful_thought").pick == "thought_reframe"


# ---------------------------------------------------------------------------
# When nothing fits: the leading framework and what it still needs (AC-5)
# ---------------------------------------------------------------------------


def test_an_event_alone_leads_to_abcde_and_needs_its_meaning():
    result = fit("event")
    assert (result.pick, result.leading, result.missing) == (None, "abcde", "meaning")


def test_a_problem_alone_leads_to_problem_solving():
    result = fit("practical_problem")
    assert (result.leading, result.missing) == ("structured_problem_solving", "unsure_what_to_do")


def test_no_facts_lead_nowhere():
    result = fit()
    assert (result.pick, result.leading, result.missing) == (None, None, None)


def test_an_excluded_framework_is_never_picked():
    """An ABCDE they have already finished hands the pick to the next that fits."""
    result = fit("event", "meaning", "painful_thought", excluded=frozenset({"abcde"}))
    assert result.pick == "thought_reframe"
