# ABOUTME: Checks the route for a person who stays stuck: the offer after "Are you feeling stuck?" and ABCDE's first step.
# ABOUTME: Fake frameworks and turn snapshots, so the context block, the candidate and the redraft are tested with no model.

import datetime as dt
import uuid

from mani.chat import context, redraft
from mani.chat.orchestrator import stuck_offer_candidate
from mani.chat.router import Fit
from mani.chat.techniques import Registry, passed_over_stages
from mani.db.threads import TurnContext
from mani.llm.schema import Reply
from mani.models.rows import Framework, TechniqueOutcome, TechniqueState, Thread

NOW = dt.datetime(2026, 10, 5, tzinfo=dt.UTC)
USER = uuid.UUID("a0000000-0000-4000-8000-00000000000a")
THREAD = uuid.UUID("b0000000-0000-4000-8000-00000000000b")
TONES = ("supportive", "reflective", "direct")
STUCK_ASK = "What goes through your mind when you feel this?"
CHECK = "That is okay. Are you feeling stuck?"
# Their third message is answered at message count 7: (7 - 3) // 2 + 1.
THIRD_MESSAGE, SECOND_MESSAGE = 7, 5


def abcde(**activation) -> Framework:
    return Framework(
        id="abcde", name="ABCDE", summary="s", body="b",
        phases=["offering", "activate", "belief", "consequence", "balanced"],
        activation={"fits_when": [["event", "meaning"], ["stuck"]], "earliest_offer_message": 3, **activation},
        stages={
            "offering": {
                "purpose": "Offer it once the event and belief are understood.",
                "ask": dict.fromkeys(TONES, "Would you like to look at it together?"),
                "stuck": {
                    "purpose": "Say it is hard to put into words right now.",
                    "boundaries": ["must not say \"stuck\" back to them"],
                },
            },
            "activate": {"answered_by": "event", "purpose": "Find the event.", "ask": dict.fromkeys(TONES, "What happened?")},
            "belief": {
                "answered_by": "meaning", "purpose": "Find the belief.",
                "if_earlier_missing": {"needs": "activate", "reply": "What comes up first?"},
                "ask": dict.fromkeys(TONES, "What did you tell yourself about it?"),
                "stuck": {"purpose": "Find what goes through their mind.", "ask": dict.fromkeys(TONES, STUCK_ASK)},
            },
            "consequence": {"purpose": "Find the effect.", "ask": dict.fromkeys(TONES, "How has that affected you?")},
            "balanced": {"purpose": "Find what is true.", "ask": dict.fromkeys(TONES, "What is true about this?")},
        },
    )


def turn(technique: TechniqueState | None = None, message_count: int = 10) -> TurnContext:
    thread = Thread(id=THREAD, user_id=USER, message_count=message_count, created_at=NOW, last_message_at=NOW)
    return TurnContext(thread=thread, profile=None, technique=technique)


def offered(known: dict[str, str]) -> TechniqueState:
    return TechniqueState(
        thread_id=THREAD, framework_id="abcde", outcome=TechniqueOutcome.OFFERED,
        phase="offering", at_message_count=6, known=known,
    )


STUCK_KNOWN = {"stuck": "dont know cant think"}


def test_only_a_stuck_person_with_no_event_has_stages_passed_over():
    assert passed_over_stages(abcde(), STUCK_KNOWN) == ["activate"]
    assert passed_over_stages(abcde(), {**STUCK_KNOWN, "event": "my exam"}) == []
    assert passed_over_stages(abcde(), {"meaning": "i am stupid"}) == []


def test_a_tapped_start_on_the_stuck_route_asks_the_stuck_line_with_nothing_said_back():
    block = context.build(turn(offered(STUCK_KNOWN)), framework=abcde(), framework_starting=True).splitlines()

    assert "stage: belief" in block
    assert f"stage_ask: {STUCK_ASK}" in block
    assert not any(line.startswith(("already_told", "stage_if_earlier_missing")) for line in block)
    assert any(line.startswith("stage_note: they accepted after saying they are stuck") for line in block)
    assert "next_stage: consequence" in block


def test_a_typed_yes_on_the_stuck_route_begins_at_the_stuck_line_too():
    block = context.build(turn(offered(STUCK_KNOWN)), framework=abcde(), offer_waiting=True).splitlines()

    assert "next_stage: belief" in block
    assert f"next_stage_ask: {STUCK_ASK}" in block
    assert not any(line.startswith(("already_told", "next_stage_if_earlier_missing")) for line in block)
    assert any(line.startswith("stage_note: if they said yes, they accepted after saying they are stuck") for line in block)


def test_with_an_event_known_the_start_turn_is_as_before():
    known = {**STUCK_KNOWN, "event": "i went to a concert"}
    block = context.build(turn(offered(known)), framework=abcde(), framework_starting=True).splitlines()

    assert 'already_told: activate: "i went to a concert"' in block
    assert "stage_ask: What did you tell yourself about it?" in block
    assert not any(STUCK_ASK in line for line in block)


def test_the_candidate_after_the_check_carries_its_stuck_branch_only_when_asked_for():
    with_branch = context.build(turn(message_count=THIRD_MESSAGE), candidate=abcde(), stuck_candidate=True)
    without = context.build(turn(message_count=THIRD_MESSAGE), candidate=abcde())

    line = next(l for l in with_branch.splitlines() if l.startswith("offer_when_stuck: "))
    assert "only if they answered yes" in line and "if they said no, offer nothing" in line
    assert "offer_when_stuck" not in without


def candidate(ctx: TurnContext, mani_texts: list[str], user_texts: list[str] = ("i dont know cant think",), **activation):
    return stuck_offer_candidate(ctx, Registry([abcde(**activation)]), mani_texts, list(user_texts))


def test_the_candidate_comes_only_on_the_turn_right_after_the_check():
    assert candidate(turn(message_count=THIRD_MESSAGE), ["What happened?", CHECK]).id == "abcde"
    assert candidate(turn(message_count=THIRD_MESSAGE), [CHECK, "What was in that message?"]) is None


def test_the_candidate_waits_for_the_earliest_message_and_is_never_shown_while_a_framework_runs():
    assert candidate(turn(message_count=SECOND_MESSAGE), [CHECK]) is None
    running = TechniqueState(thread_id=THREAD, framework_id="abcde", outcome=TechniqueOutcome.ACCEPTED, phase="belief", at_message_count=4)
    assert candidate(turn(running, THIRD_MESSAGE), [CHECK]) is None
    declined = TechniqueState(thread_id=THREAD, framework_id="abcde", outcome=TechniqueOutcome.DECLINED, phase="offering", at_message_count=2)
    assert candidate(turn(declined, 20), [CHECK]).id == "abcde"


def test_the_candidate_is_never_shown_when_their_words_rule_it_out():
    assert candidate(turn(message_count=THIRD_MESSAGE), [CHECK], ["he hit me"], never_offer_when_said=["hit me"]) is None


STUCK_FIT = Fit(frozenset({"stuck"}), pick="abcde", stuck_route=True)
SPS_FIT = Fit(frozenset({"practical_problem", "unsure_what_to_do"}), pick="structured_problem_solving")


def test_pain_in_the_body_does_not_hold_back_a_due_offer_on_the_stuck_route_only():
    sps = abcde().model_copy(update={"id": "structured_problem_solving", "name": "Structured Problem-Solving"})
    registry = Registry([abcde(), sps])
    reply = Reply(text="Is it in your body?")

    stuck = redraft.reasons(reply, ["my back hurts", "i dont know"], registry, fit=STUCK_FIT, offer_due=True)
    other = redraft.reasons(reply, ["my back hurts"], registry, fit=SPS_FIT, offer_due=True)

    assert len(stuck) == 1 and "they are stuck and have named no event" in stuck[0]
    assert other == []


def test_a_painful_feeling_is_not_read_as_pain_in_the_body():
    assert not redraft.pain_mentioned(["it was a painful conversation"])
    assert redraft.pain_mentioned(["my knee hurts"])
