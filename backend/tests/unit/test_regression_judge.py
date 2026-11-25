# ABOUTME: Checks the regression judge's own logic: which dimensions a scenario is scored on, that a verdict can name
# ABOUTME: only those, how a saved record becomes a conversation again, the run's quality figures and an experiment.

from __future__ import annotations

import argparse
import json
import uuid

from openai.lib._pydantic import to_strict_json_schema

from evals import regress
from evals.regression import checks, judge, report
from evals.drive import Conversation, Exchange
from mani.chat.techniques import Registry
from mani.models.rows import Prompt
from mani.prompts import cache, composer


def record(sid: str, style: str, scores: dict[str, int] | None = None) -> dict:
    exchange = {"conversation": 1, "said": "hi", "tapped": False, "reply": "Hello.", "buttons": [], "trace": {},
                "seconds": 1.0, "paused": False, "crisis": False}
    verdict = {"scores": {name: {"score": score} for name, score in scores.items()}} if scores else None
    return {"id": sid, "style": style, "status": "run", "exchanges": [exchange], "judge": verdict}


def test_safety_is_scored_only_where_the_scenario_is_about_safety():
    """An ordinary conversation's average is never lifted by a safety score nothing tested."""
    assert judge.SAFETY not in judge.dimensions_for({"group": "pacing", "expect": {}})
    assert judge.SAFETY in judge.dimensions_for({"group": "safety", "expect": {}})
    assert judge.SAFETY in judge.dimensions_for({"group": "pacing", "expect": {"safety": {"first": "danger"}}})
    assert len(judge.dimensions_for({"group": "pacing"})) == 9


def test_a_verdict_can_name_only_the_scenarios_dimensions():
    """The run of 2026-11-25 was scored on eighteen criteria where ten were meant, because the verdict's shape let
    the judge name any of them."""
    schema = to_strict_json_schema(judge._verdict(("naturalness", "repetition")))
    assert '"enum": ["naturalness", "repetition"]' in json.dumps(schema)


def test_a_saved_record_is_rebuilt_as_the_conversation_the_person_saw():
    saved = record("TC-01", "reflective")
    saved["exchanges"].append({**saved["exchanges"][0], "conversation": 2, "said": "another chat"})
    rebuilt = judge.conversation_of(saved, "reflective")
    assert rebuilt.style == "reflective" and [e.said for e in rebuilt.exchanges] == ["hi"]
    assert rebuilt.exchanges[0].reply == "Hello."


async def test_a_score_out_of_range_is_reported_missing_never_counted(monkeypatch):
    async def scored(http, settings, model, messages, schema, *, effort):
        assert effort == judge.JUDGE_EFFORT and "higher is always better" in messages[0]["content"]
        return {"summary": "ok", "scores": [
            {"criterion": "naturalness", "score": 4, "explanation": "", "excerpts": []},
            {"criterion": "repetition", "score": 9, "explanation": "", "excerpts": []}]}
    monkeypatch.setattr(judge, "structured", scored)
    conversation = Conversation(style="directive", exchanges=[Exchange("hi", False, "Hello.", [], {}, 1.0, False)])
    verdict = await judge.judge(None, conversation, {"id": "TC-01", "title": "t", "group": "pacing"})
    assert list(verdict["scores"]) == ["naturalness"]
    assert "repetition" in verdict["missing"] and "naturalness" not in verdict["missing"]


def test_quality_is_the_mean_of_each_conversations_mean_overall_and_by_style():
    run = {"scenarios": [record("TC-01", "directive", {"naturalness": 4, "repetition": 2}),
                         record("TC-02", "supportive", {"naturalness": 5, "repetition": 5, "safety": 5}),
                         record("TC-03", "supportive")],
           "modes": [{"triplet": "x", "score": 3}, {"triplet": "y", "error": "failed"}]}
    judged = report.quality(run)
    assert judged == {"conversations": 2, "overall": 4.0, "dimensions": {"naturalness": 4.5, "repetition": 3.5, "safety": 5.0},
                      "styles": {"directive": 3.0, "supportive": 5.0}, "mode_differentiation": 3.0}
    assert report.quality({"scenarios": [record("TC-03", "supportive")]}) is None


async def test_the_styles_are_compared_only_when_all_three_played(monkeypatch):
    seen = []

    async def compared(http, name, conversations):
        seen.append((name, sorted(conversations)))
        return {"triplet": name, "styles": sorted(conversations), "score": 4}
    monkeypatch.setattr(regress, "judge_modes", compared)
    scenarios = [{"id": f"TC-{n}", "style": style, "triplet": group}
                 for n, (style, group) in enumerate([("directive", "a"), ("supportive", "a"), ("reflective", "a"),
                                                     ("directive", "b"), ("supportive", "b")], 1)]
    records = [record(s["id"], s["style"]) for s in scenarios]
    verdicts = await regress.modes(None, records, scenarios)
    assert seen == [("a", ["directive", "reflective", "supportive"])] and [v["score"] for v in verdicts] == [4]


async def test_an_experiment_swaps_the_model_effort_and_prompt_for_the_run_only(monkeypatch, tmp_path):
    """A candidate model or prompt is measured without touching the prompt row the running app reads."""
    def prompt(name: str) -> Prompt:
        return Prompt(id=uuid.uuid4(), name=name, content=f"{name} as seeded", model_id="seeded/model",
                      model_parameters={"temperature": 0.3, "reasoning_effort": "high"}, routing={"zdr": True})
    seeded = cache.Config(prompts={"mani": prompt("mani"), "summarization": prompt("summarization")},
                          registry=Registry([]), loaded_at=0.0)

    async def load() -> cache.Config:
        return seeded
    monkeypatch.setattr(cache, "load", load)
    monkeypatch.setattr(composer, "model_settings", composer.model_settings)
    candidate = tmp_path / "candidate.md"
    candidate.write_text("---\nname: mani\n---\nThe candidate prompt.\n")
    args = argparse.Namespace(model="other/model", effort="low", prompt_file=str(candidate))

    assert regress.experiment(args) == {"model": "other/model", "effort": "low", "prompt_file": str(candidate)}

    config = await cache.load()
    assert config.prompts["mani"].content == "The candidate prompt." and seeded.prompts["mani"].content == "mani as seeded"
    assert composer.model_settings(config, "mani") == ("other/model", {"temperature": 0.3, "reasoning_effort": "low"},
                                                        {"zdr": True})
    assert composer.model_settings(config, "summarization")[0] == "seeded/model"
    assert regress.experiment(argparse.Namespace(model=None, effort=None, prompt_file=None)) is None


def test_a_detail_given_earlier_and_not_repeated_is_looked_for_in_the_reply():
    """muhammad's brief (2026-11-25): conversations that need memory of earlier details."""
    def turn(said: str, reply: str) -> Exchange:
        return Exchange(said, False, reply, [], {}, 1.0, False)
    chat = Conversation(style="directive", exchanges=[turn("my sister dana visits on friday", "Okay."),
                                                      turn("so what do i say to her?", "Tell Dana before Friday.")])
    assert checks.recalls_at(chat, 2, ["dana", "friday"]).passed
    assert not checks.recalls_at(chat, 1, ["thursday"]).passed
    assert not checks.recalls_at(chat, 3, ["dana"]).passed
