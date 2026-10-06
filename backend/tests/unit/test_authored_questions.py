# ABOUTME: Checks every question the content hands the model opens on the question, not on a clause before it.
# ABOUTME: Read through the seed parser, so this is the wording the database receives.

import pytest

from scripts.seed import FRAMEWORKS_DIR, load_somatic_stages, parse_framework
from tests.evals.validators import question_findings

FRAMEWORKS = [parse_framework(p) for p in sorted(FRAMEWORKS_DIR.glob("*.md"))]
# The offering stage's wording, its panic branch included, belongs to scope row 6.
LEFT_OUT_STAGES = {"offering"}


def _said(value) -> list[str]:
    """A line said to the person, which may be one string or one per style."""
    if isinstance(value, dict):
        return [text for text in value.values() if isinstance(text, str)]
    return [value] if isinstance(value, str) else []


def stage_lines(stage: dict) -> list[str]:
    """Every line of a stage that is said to the person: its ask, its replies and those of any
    branch. `when`, `prompts`, `purpose` and `ready_when` never are."""
    lines = _said(stage.get("ask"))
    for branch in stage.get("if_unclear") or []:
        lines += _said(branch.get("reply"))
    for value in stage.values():
        if isinstance(value, dict) and "ask" in value:
            lines += stage_lines(value)
    return lines


AUTHORED = [
    pytest.param(line, id=f"{framework['id']}.{stage_id}.{n}")
    for framework in FRAMEWORKS
    for stage_id, stage in framework["stages"].items()
    if stage_id not in LEFT_OUT_STAGES
    for n, line in enumerate(stage_lines(stage))
] + [
    pytest.param(line, id=f"somatic.{stage_id}.{n}")
    for stage_id, stage in load_somatic_stages().items()
    for n, line in enumerate(stage_lines(stage))
]


@pytest.mark.parametrize("line", AUTHORED)
def test_every_authored_question_opens_on_the_question(line):
    assert question_findings(line) == []


def test_the_lines_are_read_from_every_place_a_stage_keeps_them():
    stage = {
        "ask": {"direct": "What happened?"},
        "if_unclear": [{"when": "they decline", "reply": "Okay. Where now?", "prompts": ["Chest"]}],
        "panic": {"purpose": "steady them", "ask": {"reflective": "What do you see?"}},
    }

    assert sorted(stage_lines(stage)) == sorted(["What happened?", "Okay. Where now?", "What do you see?"])
