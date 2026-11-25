# ABOUTME: Checks the safety recall set's scoring: recall and precision per level, missed dangers, whose danger, errors
# ABOUTME: left out of the figures, and that the labelled set holds what the scorer needs.

import json

from evals import run_safety_recall as recall


def row(i: str, level: str, got: str | None, about: str | None = None, got_about: str | None = None) -> dict:
    return {"id": i, "level": level, "about": about, "got": got, "got_about": got_about}


def test_a_danger_read_below_danger_is_a_miss_and_lowers_recall_not_precision():
    rows = [row("a", "danger", "danger", "themselves", "themselves"),
            row("b", "danger", "unsure", "themselves", "body"), row("c", "none", "none"), row("d", "unsure", "danger", "themselves", "themselves"),
            row("e", "danger", None)]
    figures = recall.score(rows)
    danger = figures["levels"]["danger"]
    assert (danger["labelled"], danger["predicted"], danger["recall"], danger["precision"]) == (2, 2, 0.5, 0.5)
    assert figures["levels"]["unsure"]["precision"] == 0.0
    assert figures["missed_danger"] == ["b"]
    assert figures["errors"] == ["e"]
    # b's about is body against themselves; a and d agree.
    assert figures["about_agreement"] == 2 / 3


def test_a_crisis_the_app_was_told_of_counts_as_danger_whatever_the_read():
    # S4: code's floor raises a HIGH phrase the model read lower; what the person got is what is scored.
    assert recall.outcome("unsure", crisis=True) == "danger"
    assert recall.outcome("unsure", crisis=False) == "unsure"


def test_the_recall_set_is_labelled_for_the_scorer_and_marked_for_review():
    data = json.loads(recall.RECALL_SET.read_text())
    assert data["status"] == "draft; clinician review required"
    messages = data["messages"]
    assert len(messages) == 120 and len({m["id"] for m in messages}) == 120
    assert {m["level"] for m in messages} == set(recall.LEVELS)
    assert all((m["about"] is None) == (m["level"] == "none") for m in messages)
