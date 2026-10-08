# ABOUTME: Checks the cost baseline's arithmetic: totals, medians, ranges and the compare table.
# ABOUTME: Runs are built from plain rows, so nothing here calls a model or needs a database.

from __future__ import annotations

import json
import sys
import time
import uuid

import pytest

from mani.chat.techniques import Registry
from mani.models.rows import Prompt
from mani.prompts.cache import Config
from scripts import baseline
from scripts.seed import load_prompts
from tests.seeded import seeded_replies, seeded_tuning


def cost_row(input_tokens: int, *, reasoning: int = 0, purpose: str = "chat") -> dict:
    """One admin.llm_calls row as the eval reads it."""
    return {
        "purpose": purpose, "outcome": "ok", "input_tokens": input_tokens,
        "cached_input_tokens": input_tokens // 2, "output_tokens": 100,
        "reasoning_tokens": reasoning, "latency_ms": 1000,
    }


def turn(line: int, *rows: dict, turn_latency_ms: int = 1200) -> dict:
    return baseline.turn_row(
        line=line, token=f"line {line}", kind="typed", rows=list(rows),
        turn_latency_ms=turn_latency_ms,
    )


def run(number: int, scenario: str, *turns: dict, findings: int = 0) -> dict:
    return baseline.scenario_result(
        run=number, scenario=scenario, findings=findings, turns=list(turns)
    )


def test_a_turn_counts_every_call_it_made_including_the_exercise_pick():
    """A retried provider call and the exercise pick are part of what the turn cost."""
    row = turn(4, cost_row(1000), cost_row(1100), cost_row(300, purpose="exercise_select"))

    assert row["calls"] == 3
    assert row["input_tokens"] == 2400
    assert row["model_latency_ms"] == 3000
    assert row["purposes"] == ["chat", "chat", "exercise_select"]


def test_scenario_totals_give_the_median_and_range_across_runs():
    results = [
        run(1, "journey", turn(1, cost_row(1000)), turn(2, cost_row(1000)), findings=3),
        run(2, "journey", turn(1, cost_row(1000)), turn(2, cost_row(1000), cost_row(1000))),
        run(3, "journey", turn(1, cost_row(1000)), turn(2, cost_row(4000)), findings=1),
    ]

    totals = baseline.summarize(results)["summary"]["journey"]["totals"]

    assert totals["input_tokens"] == {"median": 3000.0, "min": 2000, "max": 5000}
    assert totals["calls"] == {"median": 2.0, "min": 2, "max": 3}
    assert isinstance(totals["calls"]["median"], float)
    assert totals["findings"] == {"median": 1.0, "min": 0, "max": 3}


def test_an_even_run_count_keeps_the_median_between_two_values():
    results = [run(1, "s", turn(1, cost_row(1000))), run(2, "s", turn(1, cost_row(2001)))]

    totals = baseline.summarize(results)["summary"]["s"]["totals"]

    assert totals["input_tokens"]["median"] == 1500.5


def test_a_line_that_did_not_send_in_every_run_says_how_often_it_did():
    """When the offer lands a turn earlier, the `@accept` line sends nothing in that run."""
    results = [
        run(1, "journey", turn(1, cost_row(1000)), turn(3, cost_row(1000))),
        run(2, "journey", turn(1, cost_row(1000)), turn(2, cost_row(1000)), turn(3, cost_row(1000))),
        run(3, "journey", turn(1, cost_row(1000)), turn(3, cost_row(1000))),
    ]

    lines = baseline.summarize(results)["summary"]["journey"]["lines"]

    assert [(entry["line"], entry["present_in"]) for entry in lines] == [(1, 3), (2, 1), (3, 3)]


def test_the_whole_sets_totals_are_taken_per_run_before_the_median():
    results = [
        run(1, "a", turn(1, cost_row(1000))), run(1, "b", turn(1, cost_row(1000))),
        run(2, "a", turn(1, cost_row(3000))), run(2, "b", turn(1, cost_row(3000))),
        run(3, "a", turn(1, cost_row(1000))), run(3, "b", turn(1, cost_row(9000))),
    ]

    totals = baseline.summarize(results)["totals"]

    assert totals["median"]["input_tokens"] == 6000.0
    assert (totals["min"]["input_tokens"], totals["max"]["input_tokens"]) == (2000, 10000)


def test_thinking_asked_for_but_never_reported_is_flagged():
    """A reasoning count of 0 on every call means it is being lost, not that it was free."""
    silent = [run(1, "s", turn(1, cost_row(1000, reasoning=0)))]
    thought = [run(1, "s", turn(1, cost_row(1000, reasoning=40)))]

    assert baseline.reasoning_reported({"chat": "high", "exercise_select": "high"}, silent) is False
    assert baseline.reasoning_reported({"chat": "high"}, thought) is True
    assert baseline.reasoning_reported({"chat": None, "exercise_select": "none"}, silent) is True


@pytest.mark.parametrize(
    ("url", "local"),
    [
        ("postgresql://postgres:pw@127.0.0.1:54342/postgres", True),
        ("postgresql://postgres:pw@localhost:54342/postgres", True),
        ("postgresql://postgres:pw@[::1]:54342/postgres", True),
        ("postgresql://postgres.abc:pw@aws-0-eu-west-2.pooler.supabase.com:6543/postgres", False),
    ],
)
def test_only_a_local_database_is_measured(url, local):
    assert baseline.is_local(url) is local


def saved(label: str, input_tokens: int, findings: int = 0, **header) -> dict:
    results = [run(1, "journey", turn(1, cost_row(input_tokens)), findings=findings)]
    return {
        "label": label, "model": "openai/gpt-6-luna", "scripts": "aaaaaaaaaaaa", "runs": 1,
        **header, "results": results, **baseline.summarize(results),
    }


def table_row(output: str, scenario: str, key: str) -> list[str]:
    lines = output.splitlines()
    start = lines.index(scenario)
    return next(line for line in lines[start:] if line.startswith(f"{key} ")).split()


def test_compare_prints_the_change_and_percent_per_scenario():
    output = baseline.compare(saved("before", 2000), saved("after", 1500))

    assert table_row(output, "journey", "input_tokens") == ["input_tokens", "2000.0", "1500.0", "-500.0", "-25.0%"]
    assert table_row(output, "total", "input_tokens")[-1] == "-25.0%"
    assert "measured the same way" in output


def test_a_change_from_zero_prints_no_percent():
    output = baseline.compare(saved("before", 1000, findings=0), saved("after", 1000, findings=2))

    assert table_row(output, "journey", "findings") == ["findings", "0.0", "2.0", "+2.0", "n/a"]


def test_compare_names_what_was_measured_differently():
    """A changed script or run count means the two files do not measure the same lines."""
    output = baseline.compare(
        saved("before", 1000), saved("after", 1000, scripts="bbbbbbbbbbbb", runs=3)
    )

    assert "measured differently:" in output
    assert "scripts: aaaaaaaaaaaa -> bbbbbbbbbbbb" in output
    assert "runs: 1 -> 3" in output


def test_compare_refuses_a_missing_file_or_one_that_is_not_a_baseline(tmp_path, capsys):
    real = tmp_path / "real.json"
    real.write_text(json.dumps(saved("real", 1000)))
    other = tmp_path / "other.json"
    other.write_text(json.dumps({"something": "else"}))

    assert baseline.main(["compare", str(real), str(tmp_path / "absent.json")]) == 1
    assert "no such file" in capsys.readouterr().err
    assert baseline.main(["compare", str(real), str(other)]) == 1
    assert "not a baseline file" in capsys.readouterr().err
    assert baseline.main(["compare", str(real), str(real)]) == 0


@pytest.mark.parametrize(
    ("argv", "reason"),
    [
        (["--baseline"], "--baseline needs --label"),
        (["--baseline", "--label", "has space"], "--label takes letters, digits, - and _ only"),
        (["--baseline", "--label", "x", "--runs", "0"], "--runs must be at least 1"),
        (["--baseline", "--label", "x", "--scenario", "journey_abcde"], "cannot be used with --baseline"),
        (["--baseline", "--label", "x", "--user", "someone"], "cannot be used with --baseline"),
        (["--baseline", "--label", "x", "--style", "direct"], "cannot be used with --baseline"),
        (["--style", "gentle"], "invalid choice: 'gentle'"),
        (["--runs", "3"], "only apply with --baseline"),
        (["--label", "x"], "only apply with --baseline"),
    ],
)
def test_a_baseline_always_runs_the_same_set_with_fresh_users(monkeypatch, capsys, argv, reason):
    from scripts import eval_replies

    monkeypatch.setattr(sys, "argv", ["eval_replies.py", *argv])
    with pytest.raises(SystemExit) as refused:
        eval_replies._parse_args()
    assert refused.value.code == 2
    assert reason in capsys.readouterr().err


def test_a_baseline_with_a_label_is_accepted(monkeypatch):
    from scripts import eval_replies

    monkeypatch.setattr(sys, "argv", ["eval_replies.py", "--baseline", "--label", "before-lean_1"])
    args = eval_replies._parse_args()
    assert (args.baseline, args.label, args.runs) == (True, "before-lean_1", None)


def test_a_scenario_can_be_played_in_one_style(monkeypatch):
    from scripts import eval_replies

    monkeypatch.setattr(sys, "argv", ["eval_replies.py", "--scenario", "journey_dbt_stop", "--style", "supportive"])
    args = eval_replies._parse_args()
    assert (args.scenario, args.style) == ("journey_dbt_stop", "supportive")


def test_a_saved_baseline_shows_when_the_replies_or_the_tuning_changed():
    rows = [Prompt(id=uuid.uuid4(), name=p["name"], content=p["content"]) for p in load_prompts()]

    def hashes(**changed: str) -> dict:
        prompts = {
            row.name: row.model_copy(update={"content": changed.get(row.name, row.content)})
            for row in rows
        }
        config = Config(
            prompts=prompts, registry=Registry([]), loaded_at=time.monotonic(),
            replies=seeded_replies(), tuning=seeded_tuning(),
        )
        return baseline.content_hashes(config)

    seeded = hashes()

    assert hashes(tuning="x: 1")["tuning"] != seeded["tuning"]
    assert hashes(replies="x: 1")["replies"] != seeded["replies"]
    assert hashes(tuning="x: 1")["replies"] == seeded["replies"]
