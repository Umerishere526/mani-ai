# ABOUTME: The scenario check's expectations: when an offer may come, and the shape of scenarios.json.
# ABOUTME: No model and no database; the live run itself is scripts/scenario_check.py.

from __future__ import annotations

import json

from mani.chat import context
from scripts import scenario_check


def test_an_offer_before_the_conversation_says_how_it_is_is_flagged_on_that_message():
    """muhammad's run, 2026-10-12: an offer at line 3 of a conversation that only says how it is at
    line 4. The window alone could not see it."""
    assert scenario_check.timing_flags(3, 5, {"offer_from": 4, "offer_by": 5}) == {
        3: "offered at their message 3, expected from 4"
    }
    assert scenario_check.timing_flags(4, 5, {"offer_from": 4, "offer_by": 5}) == {}


def test_a_missing_offer_is_flagged_only_when_the_conversation_reaches_its_latest_message():
    assert scenario_check.timing_flags(None, 5, {"offer_by": 5}) == {5: "no offer by their message 5"}
    assert scenario_check.timing_flags(None, 3, {"offer_by": 5}) == {}
    assert scenario_check.timing_flags(5, 5, {"offer_by": 4}) == {5: "offered at their message 5, expected by 4"}


def test_without_its_own_earliest_message_a_conversation_waits_for_the_window():
    early = context.FIRST_OFFER_OPENS - 1
    assert scenario_check.timing_flags(early, 5, {}) == {
        early: f"offered at their message {early}, expected from {context.FIRST_OFFER_OPENS}"
    }


def test_every_conversation_in_the_file_has_lines_and_expectations_that_can_be_met():
    groups = json.loads(scenario_check.SCENARIOS.read_text())
    every = scenario_check.conversations(groups)
    assert len(every) == sum(len(g["conversations"]) for g in groups.values()), "a name is used twice"
    for name, conversation in every.items():
        expect = conversation["expect"]
        earliest = expect.get("offer_from", context.FIRST_OFFER_OPENS)
        assert conversation["lines"], name
        assert earliest >= context.FIRST_OFFER_OPENS, name
        assert expect.get("offer_by", earliest) >= earliest, name


def test_offer_wording_in_a_reply_of_the_models_own_is_flagged():
    """Spec 0003, AC-11: an offer the model writes in its text is never sent as one, so the run
    counts how often it happens."""
    from mani.chat.techniques import Registry
    from mani.models.rows import Framework

    registry = Registry([Framework(id="abcde", name="ABCDE", summary="s", body="b", phases=["offering"])])
    assert scenario_check.offer_words_in_text("There's a set of questions called ABCDE for this.", registry)
    assert scenario_check.offer_words_in_text("A framework could help. Would you like to try it?", registry)
    assert not scenario_check.offer_words_in_text("What happened after the meeting?", registry)


def test_a_line_matches_the_clients_template_only_when_just_the_slots_changed():
    template = "We can keep talking. What's been happening that's making things feel so <how they described it>?"
    assert scenario_check.matches_template(
        "We can keep talking. What's been happening that's making things feel so heavy?", template
    )
    assert not scenario_check.matches_template(
        "We can keep talking. What has been happening that makes things feel so heavy?", template
    )


def test_every_answer_after_an_offer_names_what_kind_of_answer_it_is():
    groups = json.loads(scenario_check.SCENARIOS.read_text())
    answered = [c for c in scenario_check.conversations(groups).values() if "after_offer" in c]
    assert {c["after_offer"]["answer"] for c in answered} == {"no", "moved_on", "yes"}
    assert all(c["after_offer"]["lines"] for c in answered)
