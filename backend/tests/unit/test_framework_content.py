# ABOUTME: Checks the six framework files keep the shape a stage that moves on needs.
# ABOUTME: Readiness only on the first stage, branches only where the inventory keeps them.

import pytest

from scripts.seed import FRAMEWORKS_DIR, load_somatic_stages, parse_framework

FRAMEWORKS = {p.stem: parse_framework(p) for p in sorted(FRAMEWORKS_DIR.glob("*.md"))}

FIRST_STAGE = {
    "abcde": "activate",
    "act_choice_point": "situation",
    "behavioral_activation": "stopped",
    "dbt_stop": "stop",
    "structured_problem_solving": "problem",
    "thought_reframe": "thought",
}

# The stage each framework's questions end on; the body check follows it, with no closing question.
LAST_STAGE = {
    "abcde": "balanced",
    "act_choice_point": "action",
    "behavioral_activation": "barrier",
    "dbt_stop": "proceed",
    "structured_problem_solving": "first_action",
    "thought_reframe": "reframe",
}

# Each later stage that still carries branches, and how many: every one leaves or redirects the
# framework or protects someone, so each is a hold when it fires. A new branch here is a decision.
LATER_BRANCHES = {
    ("abcde", "balanced"): 1,
    ("act_choice_point", "toward"): 1,
    ("behavioral_activation", "barrier"): 1,
    ("dbt_stop", "pause"): 3,
    ("dbt_stop", "proceed"): 1,
    ("structured_problem_solving", "facts"): 1,
    ("thought_reframe", "facts_for"): 1,
    ("thought_reframe", "reframe"): 1,
}


STYLES = {"supportive", "reflective", "direct"}


def test_every_framework_is_covered_here():
    assert set(FRAMEWORKS) == set(FIRST_STAGE)


@pytest.mark.parametrize("framework_id", sorted(FIRST_STAGE))
def test_only_the_first_stage_carries_a_readiness_test(framework_id):
    framework = FRAMEWORKS[framework_id]
    with_readiness = [s for s, body in framework["stages"].items() if "ready_when" in body]
    assert with_readiness == [FIRST_STAGE[framework_id]]


@pytest.mark.parametrize("framework_id", sorted(FIRST_STAGE))
def test_a_branch_is_marked_start_only_only_on_the_first_stage(framework_id):
    framework = FRAMEWORKS[framework_id]
    flagged = {
        stage
        for stage, body in framework["stages"].items()
        for branch in body.get("if_unclear") or []
        if branch.get("start_only")
    }
    assert flagged <= {FIRST_STAGE[framework_id]}


def test_later_stages_keep_only_the_branches_that_leave_or_protect():
    found = {}
    for framework_id, framework in FRAMEWORKS.items():
        for stage, body in framework["stages"].items():
            if stage in ("offering", FIRST_STAGE[framework_id]):
                continue
            if body.get("if_unclear"):
                found[(framework_id, stage)] = len(body["if_unclear"])
    assert found == LATER_BRANCHES


def test_the_two_part_stages_are_two_stages_that_each_ask_one_thing():
    assert FRAMEWORKS["abcde"]["phases"] == [
        "offering", "activate", "belief", "consequence",
        "evidence_for", "evidence_against", "balanced",
    ]
    assert FRAMEWORKS["thought_reframe"]["phases"] == [
        "offering", "thought", "significance", "facts_for", "facts_against",
        "alternative", "reframe",
    ]
    for framework_id in ("abcde", "thought_reframe"):
        for stage in FRAMEWORKS[framework_id]["stages"].values():
            for ask in stage["ask"].values():
                assert ask.count("?") == 1


def test_only_dbt_stops_acting_branches_and_the_balanced_thought_branches_use_the_extra_turn():
    counted = {
        (framework_id, stage, branch["when"][:20])
        for framework_id, framework in FRAMEWORKS.items()
        for stage, body in framework["stages"].items()
        for branch in body.get("if_unclear") or []
        if branch.get("counted")
    }
    assert {(framework_id, stage) for framework_id, stage, _ in counted} == {
        ("dbt_stop", "stop"), ("dbt_stop", "pause"),
        ("abcde", "balanced"), ("thought_reframe", "reframe"),
    }
    assert len(counted) == 7



def _redirect_branches():
    for framework_id, framework in FRAMEWORKS.items():
        for stage, body in framework["stages"].items():
            if stage == "offering":
                continue
            for branch in body.get("if_unclear") or []:
                if not branch.get("counted") and not branch.get("start_only"):
                    yield framework_id, stage, branch


# Redirect branches whose reply is scenario wording ("Confronting him alone..."): the model is
# not going to write it word for word, so a real redirect there is counted. Reword the reply
# as text that fits any scenario, then take it off this list.
SCENARIO_WORDED_REDIRECTS = {
    ("act_choice_point", "situation", "the situation is actually controllable"),
    ("act_choice_point", "toward", "response creates danger"),
    ("dbt_stop", "proceed", "chooses retaliation"),
    ("thought_reframe", "facts_for", "the thought is supported by an established fact"),
}


def test_every_redirect_branch_can_be_recognised_in_every_style():
    from mani.chat import repairs

    for framework_id, stage, branch in _redirect_branches():
        for style in STYLES:
            assert repairs._match_key(repairs.reply_for(branch, style)), (framework_id, stage, branch["when"])


def test_the_scenario_worded_redirects_listed_above_still_exist():
    existing = [(f, st, branch["when"]) for f, st, branch in _redirect_branches()]
    for framework_id, stage, when in SCENARIO_WORDED_REDIRECTS:
        assert any(
            (f, st) == (framework_id, stage) and found.startswith(when) for f, st, found in existing
        ), f"{framework_id} {stage} {when} is no longer a redirect branch: take it off the list"


def test_only_abcde_is_offered_after_a_yes_to_the_stuck_check():
    flagged = [fid for fid, f in FRAMEWORKS.items() if f["activation"].get("stuck_offer")]
    assert flagged == ["abcde"]


def test_no_framework_carries_the_fields_the_model_now_judges_without():
    """The model judges when a step is done and which framework fits (spec 0010), so nothing
    seeded may still carry the removed fit or step fields."""
    removed = {"fits_when", "earliest_offer_message"}
    step_fields = {"if_earlier_missing", "ask_simpler", "picks_from_options", "answered_by"}
    for framework_id, framework in FRAMEWORKS.items():
        assert not removed & set(framework["activation"]), framework_id
        for stage, body in framework["stages"].items():
            assert not step_fields & set(body), f"{framework_id} {stage}"


# A person panicked with no action in view must never be asked about one.
_ACTION_WORDS = ("send", "sent", "post", "call", "message", "action", "typing", "unsent")


@pytest.mark.parametrize("phase", ["offering", "stop", "pause", "observe", "proceed"])
def test_dbt_stop_has_a_panic_branch_with_no_action_in_it(phase):
    panic = FRAMEWORKS["dbt_stop"]["stages"][phase].get("panic")
    assert panic and panic.get("purpose")
    asks = panic.get("ask") or {}
    assert set(asks) == {"supportive", "reflective", "direct"}
    for text in [panic["purpose"], *asks.values(), *(panic.get("boundaries") or [])]:
        words = set(text.lower().replace(".", " ").replace(",", " ").replace("?", " ").split())
        assert not words & set(_ACTION_WORDS), (phase, text)


def test_the_panic_offer_waits_until_mani_has_asked_what_is_happening():
    boundaries = FRAMEWORKS["dbt_stop"]["stages"]["offering"]["panic"]["boundaries"]
    assert any("asked what is happening" in b for b in boundaries)


@pytest.mark.parametrize("framework_id", sorted(LAST_STAGE))
def test_a_framework_ends_on_its_last_question_stage_with_no_closing_question(framework_id):
    framework = FRAMEWORKS[framework_id]
    assert framework["phases"][-1] == LAST_STAGE[framework_id]
    assert "closing" not in framework["phases"]
    assert "closing" not in framework["stages"]
    for stage in framework["stages"].values():
        assert "anything you would add" not in str(stage)


def test_the_body_check_is_asked_after_every_framework_whatever_the_last_answer_named():
    stage = load_somatic_stages()["somatic_checkin"]
    assert not any("action" in branch["when"] for branch in stage["if_unclear"])
    assert "skipped" not in stage["ready_when"]


@pytest.mark.parametrize("framework_id, stage", [("abcde", "balanced"), ("thought_reframe", "reframe")])
def test_not_knowing_what_is_fair_gets_one_gentler_question_then_moves_on(framework_id, stage):
    branches = FRAMEWORKS[framework_id]["stages"][stage]["if_unclear"]
    assert len(branches) == 1
    assert branches[0]["counted"] is True
    assert branches[0]["reply"] == "That is fine. What is one thing about this that you do know is true?"


@pytest.mark.parametrize("framework_id", ["abcde", "thought_reframe"])
def test_the_balanced_thought_is_asked_for_as_what_is_true_never_as_what_is_fair(framework_id):
    """A person asked what "a fairer way to see it" is said they did not know what fairer meant."""
    for stage, body in FRAMEWORKS[framework_id]["stages"].items():
        texts = [*body.get("ask", {}).values(), body.get("ask_simpler", "")]
        missing = body.get("if_earlier_missing")
        if missing:
            texts += [missing["reply"]] if isinstance(missing["reply"], str) else list(missing["reply"].values())
        for text in texts:
            assert "fair" not in text.lower(), (framework_id, stage, text)
