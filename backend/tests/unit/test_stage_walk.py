# ABOUTME: Walks every seeded framework from the turn they accept it to the body check.
# ABOUTME: Whatever the person replies, one stage is asked per turn and none is asked twice.

import datetime as dt
import uuid

import pytest

from mani.chat import context, repairs
from mani.chat.techniques import SOMATIC_STAGES, Registry
from mani.db.threads import TurnContext
from mani.llm.schema import Reply, TechniqueState as ReportedState
from mani.models.rows import Framework, TechniqueOutcome, TechniqueState, Thread
from scripts.seed import FRAMEWORKS_DIR, load_somatic_stages, parse_framework, with_somatic_route

USER = uuid.UUID("a0000000-0000-4000-8000-00000000000a")
THREAD = uuid.UUID("b0000000-0000-4000-8000-00000000000b")
NOW = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
STYLE = "supportive"

# What a person says to a stage question, in the order the walk uses them.
REPLIES = ["I don't know", "yes", "sure", "why does that matter?", "It was the meeting on Monday."]

FRAMEWORKS = {
    parsed["id"]: Framework(**parsed)
    for parsed in (
        with_somatic_route(parse_framework(path), load_somatic_stages())
        for path in sorted(FRAMEWORKS_DIR.glob("*.md"))
    )
}


def turn(
    framework: Framework, phase: str, *, outcome=TechniqueOutcome.ACCEPTED, starting=False, said="",
    holds=0,
):
    """The [ctx] lines the model gets when the person has just replied at `phase`."""
    state = TechniqueState(
        thread_id=THREAD, framework_id=framework.id, outcome=outcome, phase=phase,
        at_message_count=6, holds=holds,
    )
    thread = Thread(id=THREAD, user_id=USER, message_count=6, created_at=NOW, last_message_at=NOW)
    block = context.build(
        TurnContext(thread=thread, profile=None, technique=state),
        framework=framework, framework_starting=starting, their_last=context.classify_reply(said),
    )
    return block.splitlines()


def recorded(
    framework: Framework, reports: str, phase: str, *, accepting=False, holds=0, text="Thank you.",
    asked_again=False,
):
    """What the code records when the model reports stage `reports`, having been at `phase`
    with `holds` extra turns already used."""
    reply = Reply(text=text, state=ReportedState(technique=framework.id, step=reports))
    return repairs.apply(
        reply, Registry([framework]), said="", already_offered=[], current_framework_id=framework.id,
        current_phase=phase, selected_label=None, accepted_this_turn=accepting, framework_running=True,
        cooldown_passed=True, conversation_style=STYLE, wants_title=False, current_holds=holds,
        asked_again=asked_again,
    )


def shown(lines: list[str], key: str) -> str | None:
    return next((line.removeprefix(f"{key}: ") for line in lines if line.startswith(f"{key}: ")), None)


@pytest.mark.parametrize("framework_id", sorted(FRAMEWORKS))
def test_a_framework_asks_one_stage_per_turn_to_the_body_check_whatever_they_reply(framework_id):
    framework = FRAMEWORKS[framework_id]
    # The turn they accept: the model asks the second stage, as ADR 011 allows.
    second = framework.phases[2]
    start = turn(framework, "offering", outcome=TechniqueOutcome.OFFERED, starting=True)
    assert shown(start, "stage") == framework.phases[1]
    fixed = recorded(framework, second, "offering", accepting=True)
    assert fixed.phase == second

    stored, asked, turns = fixed.phase, [], 0
    while stored != "somatic_checkin":
        said = REPLIES[turns % len(REPLIES)]
        lines = turn(framework, stored, said=said)
        next_stage = framework.phases[framework.phase_index(stored) + 1]
        assert shown(lines, "answered") == stored
        assert shown(lines, "stage") == next_stage
        assert not any(line.startswith(("next_stage", "answered_ask")) for line in lines)
        if next_stage not in SOMATIC_STAGES:
            assert not any(line.startswith(("stage_ready_when", "stage_if_unclear")) for line in lines)
        ask = shown(lines, "stage_ask")
        assert ask and ask not in asked, f"{stored} -> {next_stage} asks {ask!r} a second time"
        asked.append(ask)

        fixed = recorded(framework, next_stage, stored)
        assert fixed.phase == next_stage
        assert not fixed.notes
        stored, turns = fixed.phase, turns + 1
        assert turns < len(framework.phases), "the walk did not reach the body check"


@pytest.mark.parametrize("framework_id", sorted(FRAMEWORKS))
def test_a_hold_keeps_the_answered_stage_and_shows_the_same_next_stage_again(framework_id):
    framework = FRAMEWORKS[framework_id]
    answered = framework.phases[2]
    before = turn(framework, answered, said="I don't know")
    held = recorded(framework, answered, answered)
    assert held.phase == answered
    assert held.notes == [f"held at {answered}"]
    assert shown(turn(framework, held.phase, said="ok"), "stage") == shown(before, "stage")


def test_dbt_stop_holds_at_the_pause_while_they_act_on_the_urge():
    framework = FRAMEWORKS["dbt_stop"]
    held = recorded(framework, "pause", "pause")
    assert held.phase == "pause"
    assert held.notes == ["held at pause"]
    assert shown(turn(framework, "pause", said="I started typing again"), "stage") == "observe"


@pytest.mark.parametrize("framework_id", sorted(FRAMEWORKS))
def test_a_counted_hold_is_used_once_then_the_next_stage_is_recorded(framework_id):
    framework = FRAMEWORKS[framework_id]
    answered = framework.phases[2]
    following = framework.phases[3]
    first = recorded(framework, answered, answered)
    assert (first.phase, first.holds) == (answered, 1)
    used = turn(framework, answered, said="I still do not get it", holds=first.holds)
    assert "hold_used: yes" in used
    assert shown(used, "stage") == following
    second = recorded(framework, answered, answered, holds=first.holds)
    assert (second.phase, second.holds) == (following, 0)
    assert second.notes == [f"hold limit at {answered}"]


@pytest.mark.parametrize("framework_id", sorted(FRAMEWORKS))
def test_a_client_line_holds_without_using_the_extra_turn(framework_id):
    framework = FRAMEWORKS[framework_id]
    answered = framework.phases[2]
    for holds in (0, 1):
        fixed = recorded(framework, answered, answered, holds=holds, text=repairs.CLIENT_LINES[0])
        assert (fixed.phase, fixed.holds) == (answered, holds)
        assert fixed.notes == [f"redirect held at {answered}"]


def test_dbt_stops_acting_branches_use_the_extra_turn_even_when_quoted():
    framework = FRAMEWORKS["dbt_stop"]
    branch = next(b for b in framework.stages["pause"]["if_unclear"] if "returns to the action" in b["when"])
    fixed = recorded(framework, "pause", "pause", text=repairs.reply_for(branch, STYLE))
    assert (fixed.phase, fixed.holds, fixed.notes) == ("pause", 1, ["held at pause"])


@pytest.mark.parametrize("framework_id", sorted(FRAMEWORKS))
def test_a_person_who_keeps_asking_for_the_question_again_still_reaches_the_body_check(framework_id):
    framework = FRAMEWORKS[framework_id]
    stored, holds, turns = framework.phases[2], 0, 0
    while stored != "somatic_checkin":
        # The model holds whenever it may, and moves on when told its extra turn is used.
        lines = turn(framework, stored, said="what do you mean?", holds=holds)
        reports = stored if "hold_used: yes" not in lines else shown(lines, "stage")
        fixed = recorded(framework, reports, stored, holds=holds)
        stored, holds, turns = fixed.phase, fixed.holds, turns + 1
        assert turns <= 2 * len(framework.phases), "the walk did not reach the body check"
    assert turns <= 2 * (len(framework.phases) - 3)


@pytest.mark.parametrize("framework_id", sorted(FRAMEWORKS))
def test_a_request_to_hear_the_question_again_shows_only_that_question_and_is_held_once(framework_id):
    framework = FRAMEWORKS[framework_id]
    answered = framework.phases[2]
    state = TechniqueState(
        thread_id=THREAD, framework_id=framework.id, outcome=TechniqueOutcome.ACCEPTED,
        phase=answered, at_message_count=6, holds=0,
    )
    thread = Thread(id=THREAD, user_id=USER, message_count=6, created_at=NOW, last_message_at=NOW)
    lines = context.build(
        TurnContext(thread=thread, profile=None, technique=state), framework=framework, asked_again=True,
    ).splitlines()
    assert shown(lines, "answered") == answered
    assert shown(lines, "asked_again") == "yes"
    assert shown(lines, "answered_ask") == framework.stages[answered]["ask"][STYLE]
    assert shown(lines, "stage") is None

    first = recorded(framework, framework.phases[3], answered, asked_again=True)
    assert (first.phase, first.holds) == (answered, 1)
    second = recorded(framework, framework.phases[3], answered, holds=1, asked_again=True)
    assert (second.phase, second.holds) == (framework.phases[3], 0)

