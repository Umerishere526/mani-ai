# ABOUTME: Checks the ABCDE walk: the merge of what they said, the one stage step, and each reply it renders.
# ABOUTME: Built on the real abcde.md and somatic stages, the same content that is seeded.

import uuid

import pytest

from mani.chat import walk
from mani.llm.schema import StageUpdate
from mani.models.rows import Framework
from scripts.seed import FRAMEWORKS_DIR, load_somatic_stages, parse_framework

THREAD = uuid.UUID("b0000000-0000-4000-8000-00000000000b")


@pytest.fixture(scope="module")
def abcde() -> Framework:
    parsed = parse_framework(FRAMEWORKS_DIR / "abcde.md")
    somatic = load_somatic_stages()
    return Framework(
        id=parsed["id"], name=parsed["name"], summary=parsed["summary"], body="b",
        phases=parsed["phases"] + list(somatic), stages={**parsed["stages"], **somatic},
        confirm_phrases=parsed["confirm_phrases"],
    )


def said(stage: str, words: str, status: str = "known", corrected: bool | None = None) -> StageUpdate:
    return StageUpdate(stage=stage, said=words, status=status, corrected=corrected)


def test_on_the_stage_in_force_the_latest_words_win_and_the_status_never_drops(abcde):
    stored = {"belief": {"said": "I am useless", "status": "known"}}
    merged = walk.merge(stored, [said("belief", "I let everyone down", "partial")], abcde, in_force="belief")
    assert merged.entries["belief"] == {"said": "I let everyone down", "status": "known"}
    assert merged.updated == {"belief"}


def test_elsewhere_only_a_higher_status_or_a_correction_replaces_what_is_stored(abcde):
    """AC-8, AC-9, AC-12: a correction to an earlier stage replaces its words and keeps it done; a
    lower report is ignored and logged by id and status, never by their words."""
    stored = {"activate": {"said": "left out of meetings", "status": "done", "tries": 0},
              "belief": {"said": "I am useless", "status": "partial"}}
    merged = walk.merge(stored, [
        said("activate", "moved off the project", "known"),
        said("belief", "nobody wants me there", "known"),
        said("activate", "dropped from the team meeting", "partial", corrected=True),
    ], abcde, in_force="dispute")
    assert merged.entries["activate"] == {"said": "dropped from the team meeting", "status": "done", "tries": 0}
    assert merged.entries["belief"] == {"said": "nobody wants me there", "status": "known"}
    assert merged.notes == ["ignored update for activate: known is not above done"]
    assert "moved off" not in " ".join(merged.notes)


def test_an_update_the_framework_cannot_hold_is_ignored(abcde):
    merged = walk.merge({}, [
        said("closing", "it helped"),
        said("belief", "maybe I failed", "possible"),
        said("consequence", "  ", "known"),
        said("activate", "left out", "done"),
    ], abcde, in_force=None)
    assert merged.entries == {}
    assert merged.notes == [
        "ignored update for a stage outside the framework",
        "ignored update for belief: status possible",
        "ignored update for consequence: nothing said",
        "ignored update for activate: status done",
    ]


def test_their_words_are_kept_short_and_cut_at_a_word_boundary(abcde):
    long = "word " * 60
    stored = walk.merge({}, [said("activate", long)], abcde, in_force=None).entries["activate"]["said"]
    assert len(stored) <= walk.SAID_LIMIT and stored.endswith("word") and "  " not in stored


def test_the_start_turn_clears_the_old_run_and_opens_on_a(abcde):
    """AC-3: a new start never shows an old run's done stages, and what they said before the yes seeds it."""
    walked = walk.start(abcde, [said("belief", "I am useless")])
    assert walked.entries == {"belief": {"said": "I am useless", "status": "known"}}
    assert (walked.phase, walked.reached) == ("activate", "activate")


def test_a_move_answer_moves_exactly_one_stage_and_marks_the_one_left_done(abcde):
    stored = {"belief": {"said": "I am useless", "status": "known"},
              "consequence": {"said": "I stopped going", "status": "known"}}
    walked = walk.advance(abcde, stored, None, "agreed", in_force="belief")
    assert (walked.phase, walked.reached) == ("consequence", "consequence"), "never skipped, though known"
    assert walked.entries["belief"] == {"said": "I am useless", "status": "done", "tries": 0}


def test_a_plain_no_stays_once_and_the_second_lets_the_stage_go(abcde):
    """AC-2, AC-8: a stage is asked at most twice; the code backstop moves on as let_go."""
    first = walk.advance(abcde, {}, None, "not_yet", in_force="belief")
    assert (first.phase, first.reached, first.entries["belief"]["tries"]) == ("belief", None, 1)
    second = walk.advance(abcde, first.entries, None, "not_yet", in_force="belief")
    assert second.phase == "consequence"
    assert second.entries["belief"] == {"said": "", "status": "done", "tries": 0}
    assert second.notes == ["belief let go after a second not_yet"]


def test_an_answer_that_cannot_be_true_of_the_stage_is_read_as_not_yet(abcde):
    """AC-2, AC-12: agreed only answers a check of their words, and answered brings words for the stage."""
    asked = walk.advance(abcde, {}, None, "agreed", in_force="belief")
    assert asked.phase == "belief" and asked.notes == ["stage answer invalid: agreed"]
    wordless = walk.advance(abcde, {}, [said("dispute", "x")], "answered", in_force="belief")
    assert wordless.phase == "belief" and "stage answer invalid: answered" in wordless.notes
    with_words = walk.advance(abcde, {}, [said("belief", "I am useless")], "answered", in_force="belief")
    assert with_words.phase == "consequence"
    assert with_words.entries["belief"]["said"] == "I am useless"


def test_leaving_the_closing_enters_the_body_route_and_a_body_answer_wins(abcde):
    left = walk.advance(abcde, {}, [said("effective", "I don't know yet")], "answered", in_force="effective")
    assert (left.phase, left.reached) == ("somatic_checkin", None)
    body = walk.advance(abcde, {}, None, "not_yet", in_force="effective", body_answered=True)
    assert body.phase == "somatic_checkin"
    assert body.notes == ["stage answer not_yet ignored for a body answer"]


def render(abcde, walked, before=None, text="", style="supportive", feeling=None):
    return walk.reply_text(abcde, walked, before or {}, text=text, style=style, thread_id=THREAD, feeling=feeling)


def test_a_missing_stage_is_its_letter_line_then_the_clients_question(abcde):
    """AC-1, AC-6: code sends both, so nothing the model wrote comes before or instead of them."""
    reached = walk.Walked({}, "belief", "belief")
    text, notes = render(abcde, reached, text="Thanks for telling me. What were you thinking?")
    assert text == (
        "B is for Belief. Sometimes when things are difficult, we start drawing conclusions about "
        "ourselves or what's happening. What were you telling yourself about the situation?"
    )
    assert notes == []


def test_a_missing_event_is_asked_with_their_own_word_for_the_feeling(abcde):
    start = walk.start(abcde, None)
    assert render(abcde, start, feeling="overwhelmed")[0] == (
        "A is for Activating Event. What's been happening that's left you feeling so overwhelmed?"
    )
    assert render(abcde, start) == (
        "A is for Activating Event. What's been happening that's left things feeling so hard?", ["slot empty"],
    )


@pytest.mark.parametrize("status", ["known", "possible"])
def test_a_known_or_possible_event_is_the_clients_confirm_line_with_their_words(abcde, status):
    """AC-4: muhammad chose to confirm a known event too, with the same client line."""
    start = walk.start(abcde, [said("activate", "Being left out of meetings at work.", status)])
    assert render(abcde, start, style="reflective")[0] == (
        "A is for Activating Event. You've mentioned being left out of meetings at work. "
        "Is that where these concerns began?"
    )


def test_their_words_inside_a_line_start_lowercase_except_i(abcde):
    """Live, 2026-10-13: "From what you've shared, The client changes..." (muhammad: lowercase the
    first word, except "I" and its contractions)."""
    start = walk.start(abcde, [said("activate", "I'm left out of meetings", "possible")])
    assert "You mentioned I'm left out of meetings. Is that" in render(abcde, start)[0]
    assert render(abcde, walk.start(abcde, None), feeling="Overwhelmed")[0].endswith("feeling so overwhelmed?")


def test_a_known_stage_is_their_words_said_back_then_one_confirm_phrase(abcde):
    """AC-4, AC-7: the model names their words; a question it adds is dropped, since the phrase asks."""
    stored = {"belief": {"said": "I am useless", "status": "known"}}
    reached = walk.Walked(stored, "belief", "belief")
    phrase = walk.confirm_phrase(abcde, "belief", THREAD)
    text, notes = render(abcde, reached, before=stored, text="You said you feel useless. Is that it?")
    assert text == f"B is for Belief. You said you feel useless. {phrase}"
    assert notes == ["naming asks"]
    assert render(abcde, reached, before=stored, text="What else?")[0] == (
        f"B is for Belief. You mentioned I am useless. {phrase}"
    )


def test_text_written_for_another_branch_is_never_used_to_name_their_words(abcde):
    """Their words for the next stage arrived this turn, after [ctx] told the model its text was not
    sent, so the fixed naming sentence is used instead of whatever it wrote."""
    after = {"belief": {"said": "I am useless", "status": "known"}}
    reached = walk.Walked(after, "belief", "belief")
    text, notes = render(abcde, reached, before={}, text="Thank you for sharing that.")
    assert text.startswith("B is for Belief. You mentioned I am useless. ")
    assert notes == ["branch changed"]


def test_a_partial_stage_asks_only_the_gap_or_falls_back_to_the_clients_question(abcde):
    """AC-5."""
    stored = {"consequence": {"said": "I felt bad", "status": "partial"}}
    reached = walk.Walked(stored, "consequence", "consequence")
    gap = "What did you do after that?"
    assert render(abcde, reached, before=stored, text=gap) == (f"C is for Consequences. {gap}", [])
    text, notes = render(abcde, reached, before=stored, text="That sounds hard.")
    assert text.endswith("How did that belief affect how you felt or what you did?")
    assert notes == ["gap asks nothing"]


def test_a_reply_that_stays_has_no_letter_line_and_any_the_model_wrote_is_dropped(abcde):
    """AC-1."""
    stayed = walk.Walked({}, "belief", None)
    text, notes = render(abcde, stayed, text="B is for Belief. I misunderstood. What would be more accurate?")
    assert text == "I misunderstood. What would be more accurate?"
    assert notes == ["dropped a letter line"]


def test_the_confirm_phrase_is_stable_per_thread_and_differs_between_neighbouring_stages(abcde):
    """AC-7."""
    for thread in (THREAD, uuid.uuid4(), uuid.uuid4()):
        phrases = [walk.confirm_phrase(abcde, stage, thread) for stage in ("belief", "consequence", "dispute")]
        assert phrases == [walk.confirm_phrase(abcde, stage, str(thread)) for stage in ("belief", "consequence", "dispute")]
        assert phrases[0] != phrases[1] != phrases[2]
        assert set(phrases) <= set(abcde.confirm_phrases)


def test_the_ledger_view_reads_the_store_after_the_turn(abcde):
    stored = {"activate": {"said": "left out", "status": "done"},
              "dispute": {"said": "they never said why", "status": "partial"}}
    rows = walk.ledger_view(abcde, stored, "belief")
    assert [(r["stage"], r["status"], r["asking"]) for r in rows] == [
        ("activate", "done", False), ("belief", "missing", True), ("consequence", "not_reached", False),
        ("dispute", "partial", False), ("effective", "not_reached", False),
    ]
    assert rows[0]["title"] == "A: Activating Event" and rows[0]["known"] == "left out"
