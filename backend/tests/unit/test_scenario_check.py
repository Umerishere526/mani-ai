# ABOUTME: The scenario check's expectations: when Mani's check may come, and the shape of scenarios.json.
# ABOUTME: No model and no database; the live run itself is scripts/scenario_check.py.

from __future__ import annotations

import json

from scripts import scenario_check


def test_a_check_before_the_conversation_says_how_it_is_is_flagged_on_that_message():
    """muhammad's run, 2026-10-12: an offer at line 3 of a conversation that only says how it is at
    line 4. Mani's check now comes where that offer did (spec 0006)."""
    assert scenario_check.timing_flags(3, 5, {"check_from": 4, "check_by": 5}) == {
        3: "checked at their message 3, expected from 4"
    }
    assert scenario_check.timing_flags(4, 5, {"check_from": 4, "check_by": 5}) == {}


def test_a_missing_check_is_flagged_by_the_last_line_unless_the_conversation_names_another():
    assert scenario_check.timing_flags(None, 5, {}) == {5: "no check by their message 5"}
    assert scenario_check.timing_flags(None, 3, {"check_by": 5}) == {}
    assert scenario_check.timing_flags(5, 5, {"check_by": 4}) == {5: "checked at their message 5, expected by 4"}


def test_every_conversation_in_the_file_has_lines_and_expectations_that_can_be_met():
    groups = json.loads(scenario_check.SCENARIOS.read_text())
    every = scenario_check.conversations(groups)
    assert len(every) == sum(len(g["conversations"]) for g in groups.values()), "a name is used twice"
    for name, conversation in every.items():
        expect = conversation["expect"]
        earliest = expect.get("check_from", scenario_check.EARLIEST_CHECK)
        assert conversation["lines"], name
        assert earliest >= scenario_check.EARLIEST_CHECK, name
        assert expect.get("check_by", len(conversation["lines"])) >= earliest, name


def test_mani_talking_about_the_person_instead_of_to_them_is_flagged():
    """muhammad's Directive run, 2026-10-13: a third person note pasted into A's client line."""
    said_about = ("A is for Activating Event. From what you've shared, their boss criticized their client "
                  "communication seems to be what started these concerns. Is that right?")
    said_to = said_about.replace("their boss criticized their", "your boss criticized your")
    assert scenario_check.TALKS_ABOUT_THEM.search(said_about)
    assert not scenario_check.TALKS_ABOUT_THEM.search(said_to)


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


def test_a_stage_reached_without_its_letter_line_or_a_known_stage_asked_is_flagged():
    """Spec 0004, AC-1 and AC-4, read from the turn's stage trace: ids and statuses, never words."""
    stages = {
        "activate": {"intro": "A is for Activating Event.", "ask": {"supportive": "What happened?"}},
        "belief": {"intro": "B is for Belief.", "ask": {"supportive": "What did you tell yourself?"}},
    }

    def trace(asking: str, status: str) -> list[dict]:
        return [{"stage": s, "status": status if s == asking else "missing", "asking": s == asking}
                for s in stages]

    on_a = trace("activate", "missing")
    assert scenario_check.stage_flags("A is for Activating Event. What happened?", on_a, None, stages, "supportive") == []
    assert scenario_check.stage_flags("What happened?", on_a, None, stages, "supportive") == [
        "stage reply without its letter line"]
    assert scenario_check.stage_flags("Can you say more?", on_a, on_a, stages, "supportive") == [], "a stay has none"
    known_b = trace("belief", "known")
    assert scenario_check.stage_flags(
        "B is for Belief. What did you tell yourself?", known_b, on_a, stages, "supportive",
    ) == ["asked a stage already known"]
    assert scenario_check.stage_flags("Anything", None, on_a, stages, "supportive") == []


# Mani's five replies in the client's way of communication sample, word for word (2026-10-13).
SAMPLE_REPLIES = (
    "I'm listening. What's frustrating you?",
    "When everything feels frustrating, sometimes it's because several things have been building up for a "
    "while. I don't want to assume that's what's happening to you.",
    "That's a lot of frustration coming from every direction at work. I want to understand something before "
    "we go further.",
    "That would be frustrating, especially when other people's lack of follow-through creates additional work "
    "for you. But I want to understand the pattern rather than assume everyone is the problem.",
    "So your ability to do your job depends on other people fulfilling their responsibilities. When they "
    "don't, your work gets held up, and you're left dealing with the consequences.",
)


def test_explaining_people_is_flagged_and_the_clients_sample_never_is():
    """muhammad's run, 2026-10-13: the reply explained how criticism works on people instead of finding out."""
    explained = ("Being criticized by your boss can make it hard to separate one piece of feedback from what you "
                 "think it says about your ability.")
    assert scenario_check.EXPLAINS_PEOPLE.search(explained)
    assert not any(scenario_check.EXPLAINS_PEOPLE.search(reply) for reply in SAMPLE_REPLIES)


def test_a_stage_reached_otherwise_than_expected_is_flagged_once():
    """Thread 7d102554: C was reached as missing and asked though they had said it."""
    seen: set[str] = set()
    trace = [{"stage": "consequence", "status": "missing", "asking": True}]
    assert scenario_check.reached_flags(trace, {"consequence": "said back"}, seen) == [
        "reached consequence as missing, expected said back"
    ]
    assert scenario_check.reached_flags(trace, {"consequence": "said back"}, seen) == [], "only when first reached"
    partial = [{"stage": "dispute", "status": "partial", "asking": True}]
    assert scenario_check.reached_flags(partial, {"dispute": "said back"}, seen) == []
