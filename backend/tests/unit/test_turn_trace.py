# ABOUTME: Checks the turn trace: decisions and code's notes only, never their words, and the timeline the
# ABOUTME: trace script prints from it. No model and no database.

from mani.chat import orchestrator
from mani.llm.schema import NextStage, Reply, StageUpdate
from scripts import trace as trace_script

THEIR_WORDS = "my manager never explains why I was passed over"


def test_the_trace_holds_what_the_reply_reported_about_the_stages_but_never_their_words():
    reply = Reply(
        text="So it keeps happening.", stage_answer="explore",
        stage_updates=[StageUpdate(stage="effective", said=THEIR_WORDS, status="known")],
        next_stage=NextStage(status="partial", said=THEIR_WORDS, gap="path"),
    )
    reported = orchestrator._stage_reports(reply)
    assert reported == {
        "stage_answer": "explore",
        "stage_updates": [{"stage": "effective", "status": "known"}],
        "next_stage": {"status": "partial", "gap": "path"},
    }
    assert THEIR_WORDS not in str(reported)


def test_empty_parts_are_left_out_and_false_is_kept_only_when_asked():
    assert orchestrator._trace(a=None, b="", c=[], d={}, e=0, f="x") == {"e": 0, "f": "x"}


def test_the_raw_reply_is_kept_only_in_debug():
    class Settings:
        ai_debug_mode = False

    reply = Reply(text=THEIR_WORDS)
    assert orchestrator._raw(reply, Settings()) is None
    Settings.ai_debug_mode = True
    assert orchestrator._raw(reply, Settings())["text"] == THEIR_WORDS


def test_the_timeline_reads_a_turn_as_one_block():
    lines = trace_script.turn_lines(3, {
        "moment": "in_stages", "their_message": 9, "phase_before": "effective", "phase_after": "somatic_ask",
        "latency_ms": 3200, "model": {"stage_answer": "explore"},
        "notes": ["explore with words for a stage not said back read as answered"],
        "stages": [{"stage": "effective", "status": "done", "asking": False}],
    })
    assert lines[0] == "#3  their message 9 · in_stages · effective -> somatic_ask (3.2 s)"
    assert "    model reported: stage_answer explore" in lines
    assert "    stages: effective=done" in lines
    assert any("read as answered" in line for line in lines)
