# ABOUTME: Walks every seeded framework from the turn they accept it to the body check.
# ABOUTME: The model judges each step (spec 0010); the code keeps one extra attempt per step and never goes back.

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
    asked_again=False, ending=None,
):
    """What the code records when the model reports stage `reports`, having been at `phase`
    with `holds` extra turns already used."""
    reply = Reply(text=text, state=ReportedState(technique=framework.id, step=reports), ending=ending)
    return repairs.apply(
        reply, Registry([framework]), already_offered=[], current_framework_id=framework.id,
        current_phase=phase, selected_label=None, accepted_this_turn=accepting, framework_running=True,
        offer_allowed=True, conversation_style=STYLE, wants_title=False, current_holds=holds,
        asked_again=asked_again,
    )


def steps(lines: list[str]) -> list[str]:
    return [line.removeprefix("step: ") for line in lines if line.startswith("step: ")]


def question_steps(framework: Framework) -> list[str]:
    return framework.phases[1 : framework.phase_index("somatic_checkin")]


def shown(lines: list[str], key: str) -> str | None:
    return next((line.removeprefix(f"{key}: ") for line in lines if line.startswith(f"{key}: ")), None)


@pytest.mark.parametrize("framework_id", sorted(FRAMEWORKS))
def test_a_framework_walked_one_step_at_a_time_reaches_the_body_check_resolved(framework_id):
    framework = FRAMEWORKS[framework_id]
    start = turn(framework, "offering", outcome=TechniqueOutcome.OFFERED, starting=True)
    assert steps(start) == question_steps(framework)
    first = question_steps(framework)[0]
    stored = recorded(framework, first, "offering", accepting=True).phase
    assert stored == first

    asked, turns, fixed = [], 0, None
    while stored != "somatic_checkin":
        lines = turn(framework, stored, said=REPLIES[turns % len(REPLIES)])
        remaining = question_steps(framework)[question_steps(framework).index(stored):]
        assert shown(lines, "current_step") == stored
        assert steps(lines) == remaining
        following = framework.phases[framework.phase_index(stored) + 1]
        fixed = recorded(framework, following, stored)
        assert fixed.phase == following
        if following not in SOMATIC_STAGES:
            assert following not in asked, f"{following} asked a second time"
            asked.append(following)
        stored, turns = fixed.phase, turns + 1
        assert turns < len(framework.phases), "the walk did not reach the body check"
    assert fixed.ending == "resolved"


@pytest.mark.parametrize("framework_id", sorted(FRAMEWORKS))
def test_the_model_may_move_straight_to_a_later_step(framework_id):
    framework = FRAMEWORKS[framework_id]
    questions = question_steps(framework)
    if len(questions) < 3:
        pytest.skip("too few steps to pass one")
    fixed = recorded(framework, questions[2], questions[0])
    assert (fixed.phase, fixed.holds, fixed.notes) == (questions[2], 0, [])


@pytest.mark.parametrize(("ending", "expected"), [("pivoted", "pivoted"), ("stopped", "stopped"), ("resolved", "resolved")])
@pytest.mark.parametrize("framework_id", sorted(FRAMEWORKS))
def test_an_ending_on_any_step_goes_to_the_body_check_in(framework_id, ending, expected):
    framework = FRAMEWORKS[framework_id]
    stored = question_steps(framework)[0]
    fixed = recorded(framework, stored, stored, ending=ending)
    assert (fixed.phase, fixed.ending) == ("somatic_checkin", expected)


@pytest.mark.parametrize("framework_id", sorted(FRAMEWORKS))
def test_reaching_the_check_in_early_with_no_ending_reported_is_recorded_as_pivoted(framework_id):
    framework = FRAMEWORKS[framework_id]
    fixed = recorded(framework, "somatic_checkin", question_steps(framework)[0])
    assert (fixed.phase, fixed.ending) == ("somatic_checkin", "pivoted")


@pytest.mark.parametrize("framework_id", sorted(FRAMEWORKS))
def test_a_step_never_moves_back_and_never_past_the_check_in(framework_id):
    framework = FRAMEWORKS[framework_id]
    questions = question_steps(framework)
    stored = questions[1] if len(questions) > 1 else questions[0]
    back = recorded(framework, "offering", stored)
    assert back.phase == framework.phases[framework.phase_index(stored) + 1]
    past = recorded(framework, "somatic_practice", questions[0])
    assert past.phase == "somatic_checkin"


@pytest.mark.parametrize("framework_id", sorted(FRAMEWORKS))
def test_one_more_attempt_is_counted_once_then_the_next_step_is_recorded(framework_id):
    framework = FRAMEWORKS[framework_id]
    answered = question_steps(framework)[0]
    following = framework.phases[framework.phase_index(answered) + 1]
    first = recorded(framework, answered, answered)
    assert (first.phase, first.holds, first.notes) == (answered, 1, [f"held at {answered}"])
    used = turn(framework, answered, said="I still do not get it", holds=first.holds)
    assert "hold_used: yes" in used
    second = recorded(framework, answered, answered, holds=first.holds)
    assert (second.phase, second.holds) == (following, 0)
    assert second.notes == [f"hold limit at {answered}"]


def test_dbt_stop_holds_at_the_pause_while_they_act_on_the_urge():
    framework = FRAMEWORKS["dbt_stop"]
    held = recorded(framework, "pause", "pause")
    assert held.phase == "pause"
    assert held.notes == ["held at pause"]


@pytest.mark.parametrize("framework_id", sorted(FRAMEWORKS))
def test_a_client_line_holds_without_using_the_extra_turn(framework_id):
    framework = FRAMEWORKS[framework_id]
    answered = question_steps(framework)[0]
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
    stored, holds, turns = question_steps(framework)[0], 0, 0
    while stored != "somatic_checkin":
        # The model holds whenever it may, and moves on when told its extra attempt is used.
        lines = turn(framework, stored, said="what do you mean?", holds=holds)
        reports = stored if "hold_used: yes" not in lines else framework.phases[framework.phase_index(stored) + 1]
        fixed = recorded(framework, reports, stored, holds=holds, asked_again=holds == 0)
        stored, holds, turns = fixed.phase, fixed.holds, turns + 1
        assert turns <= 2 * len(framework.phases), "the walk did not reach the body check"
