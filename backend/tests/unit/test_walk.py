# ABOUTME: Checks the ABCDE walk: the parts they gave, the one step per reply, and each reply it renders.
# ABOUTME: Built on the real abcde.md and somatic stages, the same content that is seeded.

import uuid

import pytest

from mani.chat import understanding, walk
from mani.llm.schema import NextStage, StageUpdate
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


def got(part: str, words: str = "", **flags) -> StageUpdate:
    return StageUpdate(part=part, said=words, **flags)


def judged(*parts: StageUpdate) -> NextStage:
    """The reply's judgement of the stage the walk reaches next: the parts the conversation answers."""
    return NextStage(parts=list(parts))


def stage(step: str, said: dict[str, str] | None = None, **more) -> dict:
    """A stage as the walk stores it."""
    parts = {pid: {"said": words, "source": "said"} for pid, words in (said or {}).items()}
    return {"parts": parts, "step": step, "tries": 0, **more}


BELIEF = "I won't get it all done"


# The parts a stage collects, and the step each reply takes (spec 0007).

def test_parts_they_give_are_kept_and_a_stage_with_a_required_part_missing_keeps_collecting(abcde):
    walked = walk.advance(abcde, {}, [got("did", "you don't start")], None, in_force="consequence")
    entry = walked.entries["consequence"]
    assert (walked.phase, walked.reached, entry["step"], entry["tries"]) == ("consequence", None, "collecting", 0)
    assert entry["parts"] == {"did": {"said": "you don't start", "source": "said"}}
    assert walk.missing_parts(abcde, "consequence", entry) == ["felt"]


def test_every_required_part_filled_gives_the_reading_and_waits_for_their_yes(abcde):
    """No reading is given while a required part is missing; once all are there the stage is read once."""
    first = walk.advance(abcde, {}, [got("belief", BELIEF)], None, in_force="belief")
    entry = first.entries["belief"]
    assert (first.phase, first.reached, entry["step"], entry["read"]) == ("belief", None, "read", {"belief": BELIEF})
    assert "belief complete: read for their yes" in first.notes
    optional = walk.advance(abcde, {}, [got("belief_type", "all or nothing", inferred=True)], None, in_force="belief")
    assert optional.entries["belief"]["step"] == "collecting", "an optional part never completes a stage"


def test_a_yes_to_the_reading_asks_what_they_take_from_it_and_any_answer_then_ends_the_stage(abcde):
    read = {"belief": stage("read", {"belief": BELIEF}, read={"belief": BELIEF})}
    asked = walk.advance(abcde, read, None, "agreed", in_force="belief")
    assert (asked.phase, asked.reached, asked.entries["belief"]["step"]) == ("belief", None, "reflect")
    assert "belief agreed: asking what they take from it" in asked.notes
    for answer in ("not_yet", None):
        ended = walk.advance(abcde, asked.entries, None, answer, in_force="belief",
                             report=judged(got("felt", "you feel guilty", inferred=True)))
        assert (ended.phase, ended.reached, ended.entries["belief"]["step"]) == ("consequence", "consequence", "done")
        assert ended.entries["consequence"]["parts"]["felt"]["source"] == "inferred"
        assert ended.entries["consequence"]["step"] == "collecting", "what they did is still missing"


def test_a_stage_with_nothing_to_reflect_on_ends_on_their_yes(abcde):
    read = {"activate": stage("read", {"event": "a long list undone"}, read={"event": "a long list undone"})}
    ended = walk.advance(abcde, read, None, "agreed", in_force="activate", report=judged())
    assert (ended.phase, ended.reached, ended.entries["activate"]["step"]) == ("belief", "belief", "done")
    assert "belief" not in ended.entries, "nothing answers it yet, so its question is asked"


def test_a_yes_with_more_added_still_ends_the_reading_and_keeps_the_added_words(abcde):
    """Thread 7d102554: "yes this weighing on my mind…" is agreement; the words are kept, not read again."""
    read = {"belief": stage("read", {"belief": BELIEF}, read={"belief": BELIEF})}
    walked = walk.advance(abcde, read, [got("belief_type", "all or nothing", inferred=True)], "agreed", in_force="belief")
    assert walked.entries["belief"]["step"] == "reflect"
    assert walked.entries["belief"]["parts"]["belief_type"]["source"] == "inferred"


def test_words_that_change_a_part_give_a_new_reading_and_an_unchanged_reply_gives_none(abcde):
    """No reading vs a new reading is decided from the parts: a new one only when a part differs."""
    read = {"belief": stage("read", {"belief": BELIEF}, read={"belief": BELIEF})}
    changed = walk.advance(abcde, read, [got("belief", "I'm too behind to catch up")], None, in_force="belief")
    entry = changed.entries["belief"]
    assert (entry["step"], entry["read"], entry["tries"]) == ("read", {"belief": "I'm too behind to catch up"}, 0)
    assert entry["parts"]["belief"]["was"] == [BELIEF]
    assert "belief changed: read again for their yes" in changed.notes
    same = walk.advance(abcde, read, [got("belief", BELIEF)], "not_yet", in_force="belief")
    assert (same.entries["belief"]["step"], same.entries["belief"]["tries"], same.notes) == ("read", 1, [])


def test_a_part_they_reject_is_asked_again(abcde):
    read = {"consequence": stage("read", {"felt": "guilty", "did": "you don't start"},
                                 read={"felt": "guilty", "did": "you don't start"})}
    walked = walk.advance(abcde, read, [got("felt", rejected=True)], None, in_force="consequence")
    entry = walked.entries["consequence"]
    assert (entry["step"], list(entry["parts"])) == ("collecting", ["did"])
    assert walk.missing_parts(abcde, "consequence", entry) == ["felt"]
    assert "consequence part emptied: asked again" in walked.notes


def test_a_yes_when_no_reading_was_given_is_not_a_yes(abcde):
    walked = walk.advance(abcde, {}, None, "agreed", in_force="belief")
    assert (walked.phase, walked.entries["belief"]["step"]) == ("belief", "collecting")
    assert walked.notes == ["stage answer invalid: agreed"]


def test_a_stage_holds_what_their_own_words_gave_against_an_inference_and_keeps_what_it_replaced(abcde):
    held = {"belief": stage("collecting", {"belief": BELIEF})}
    inferred = walk.advance(abcde, held, [got("belief", "they hate me", inferred=True)], None, in_force="belief")
    assert inferred.entries["belief"]["parts"]["belief"]["said"] == BELIEF
    corrected = walk.advance(abcde, held, [got("belief", "I let everyone down", corrected=True)], None,
                             in_force="belief")
    part = corrected.entries["belief"]["parts"]["belief"]
    assert (part["said"], part["was"]) == ("I let everyone down", [BELIEF])


def test_their_words_are_kept_short_and_cut_at_a_word_boundary(abcde):
    walked = walk.advance(abcde, {}, [got("belief", "word " * 60)], None, in_force="belief")
    kept = walked.entries["belief"]["parts"]["belief"]["said"]
    assert len(kept) <= walk.SAID_LIMIT and kept.endswith("word") and "  " not in kept


# Not knowing, and when to stop asking.

def test_i_dont_know_never_moves_a_stage_and_after_four_replies_without_progress_the_choice_is_offered(abcde):
    """Spec 0007, AC-1, AC-2: no counter moves a stage; at STALL_LIMIT the reply offers the choice."""
    entries: dict = {}
    for n in range(1, walk.STALL_LIMIT + 2):
        walked = walk.advance(abcde, entries, None, "not_yet", in_force="belief")
        entries = walked.entries
        assert (walked.phase, walked.reached, entries["belief"]["tries"]) == ("belief", None, n)
    quiet = walk.next_line(abcde, {"belief": stage("collecting", tries=walk.STALL_LIMIT - 1)}, "belief")
    assert not quiet.startswith("They have stayed")
    stalled = walk.next_line(abcde, entries, "belief")
    assert stalled.startswith(
        f"They have stayed on belief for {walk.STALL_LIMIT + 1} replies without getting further. Your text "
        "offers the choice: keep going with it, skip it (answer let_go), or stop the questions here (answer stopped). "
    )


def test_progress_resets_the_count_so_a_stage_with_several_exchanges_is_never_stalled(abcde):
    entries = {"consequence": stage("collecting", tries=3)}
    walked = walk.advance(abcde, entries, [got("did", "you don't start")], None, in_force="consequence")
    assert walked.entries["consequence"]["tries"] == 0


def test_a_part_released_by_its_stop_pushing_counts_as_filled_with_the_closest_thing_they_said(abcde):
    held = {"dispute": stage("collecting", {"evidence": "it all piles up"})}
    walked = walk.advance(abcde, held, [got("logic", "they feel joined", released=True)], None, in_force="dispute")
    entry = walked.entries["dispute"]
    assert entry["parts"]["logic"] == {"said": "they feel joined", "source": "said", "released": True}
    assert (entry["step"], walk.missing_parts(abcde, "dispute", entry)) == ("read", [])
    nothing = walk.advance(abcde, held, [got("logic", released=True)], None, in_force="dispute")
    assert walk.missing_parts(abcde, "dispute", nothing.entries["dispute"]) == []


def test_a_skip_moves_the_stage_and_never_keeps_a_reading_they_did_not_agree_to(abcde):
    read = {"belief": stage("read", {"belief": BELIEF}, read={"belief": BELIEF})}
    skipped = walk.advance(abcde, read, None, "let_go", in_force="belief", report=judged())
    assert (skipped.phase, skipped.entries["belief"]["step"], skipped.entries["belief"]["parts"]) == (
        "consequence", "done", {},
    )
    partly = {"consequence": stage("collecting", {"did": "you don't start"})}
    kept = walk.advance(abcde, partly, None, "let_go", in_force="consequence", report=judged())
    assert kept.entries["consequence"]["parts"]["did"]["said"] == "you don't start"


def test_stopping_the_questions_is_reported_and_moves_nothing(abcde):
    """Spec 0007, AC-3: the walk reports the stop and leaves the store as it was; the orchestrator records it."""
    stored = {"belief": stage("collecting", {"belief_type": "all or nothing"}, tries=2)}
    walked = walk.advance(abcde, stored, None, "stopped", in_force="belief")
    assert (walked.phase, walked.reached, walked.stopped) == ("belief", None, True)
    assert walked.entries == stored
    assert walked.notes == ["belief stopped by them"]


def test_a_body_answer_at_the_closing_wins_over_a_stage_answer(abcde):
    walked = walk.advance(abcde, {}, None, "stopped", in_force="effective", body_answered=True)
    assert (walked.phase, walked.reached, walked.stopped) == ("somatic_checkin", None, False)
    assert walked.notes == ["stage answer stopped ignored for a body answer"]


def test_a_question_holds_the_stage_without_a_try_then_counts_as_a_try(abcde):
    """A question or push-back is answered and the stage held; it never spends a try, until HELD_FOR_QUESTIONS."""
    entries: dict = {}
    for _ in range(walk.HELD_FOR_QUESTIONS):
        held = walk.advance(abcde, entries, None, "asked", in_force="belief")
        entries = held.entries
        assert (held.phase, entries["belief"]["tries"]) == ("belief", 0)
    tried = walk.advance(abcde, entries, None, "asked", in_force="belief")
    assert (tried.phase, tried.entries["belief"]["tries"]) == ("belief", 1)


def test_a_feeling_change_or_a_shift_awaiting_their_answer_holds_the_walk_where_it_is(abcde):
    read = {"belief": stage("read", {"belief": BELIEF}, read={"belief": BELIEF}, tries=1)}
    held = walk.advance(abcde, read, None, "agreed", in_force="belief", hold=True)
    assert (held.phase, held.entries["belief"]["step"], held.entries["belief"]["tries"]) == ("belief", "read", 1)
    assert held.notes == ["belief held while a change awaits their answer"]


def test_a_correction_to_an_earlier_stage_is_kept_with_its_old_words_and_holds_this_stage(abcde):
    stored = {"belief": stage("done", {"belief": BELIEF}),
              "dispute": stage("read", {"evidence": "nothing supports it", "logic": "they feel joined"})}
    walked = walk.advance(abcde, stored, [got("belief", "I'm lazy", corrected=True)], "agreed", in_force="dispute")
    assert (walked.phase, walked.reached) == ("dispute", None)
    part = walked.entries["belief"]["parts"]["belief"]
    assert (part["said"], part["was"], walked.entries["belief"]["step"]) == ("I'm lazy", [BELIEF], "done")
    assert "earlier stage corrected: clarified before moving" in walked.notes


def test_a_part_of_a_later_stage_is_dropped_until_the_walk_reaches_it(abcde):
    walked = walk.advance(abcde, {}, [got("felt", "guilty")], None, in_force="belief")
    assert "consequence" not in walked.entries and "dropped update for felt" in walked.notes


def test_stages_stored_ahead_or_in_an_earlier_shape_are_ignored_and_judged_when_reached(abcde):
    stored = {"belief": {"said": "I am useless", "status": "known"},
              "consequence": stage("collecting", {"did": "stale"})}
    walked = walk.advance(abcde, stored, None, "not_yet", in_force="belief")
    assert "consequence" not in walked.entries
    assert any(note.startswith("ignored stored in an earlier shape: belief") for note in walked.notes)
    assert "ignored stored ahead: consequence" in walked.notes


# Parts bound to what the person told Mani before the framework, and to what they feel as it runs.

def test_the_walk_opens_on_a_with_the_event_from_the_open_chat_as_a_reading_to_confirm(abcde):
    started = walk.start(abcde, [got("belief", "ignored")], judged(), {"event": "a long list undone"})
    entry = started.entries["activate"]
    assert (started.phase, started.reached, started.unjudged) == ("activate", "activate", False)
    assert entry["parts"]["event"] == {"said": "a long list undone", "source": "inferred"}
    assert entry["step"] == "read" and started.notes == ["dropped update for belief"]


def test_a_reply_that_judged_nothing_leaves_the_stage_unjudged_and_a_judged_nothing_stores_nothing(abcde):
    assert walk.start(abcde, None, None).unjudged
    nothing = walk.start(abcde, None, judged())
    assert (nothing.entries, nothing.unjudged) == ({}, False)


def test_a_part_is_filled_from_the_understanding_once_per_value_and_never_over_their_own_words(abcde):
    """C's felt is bound to their feeling: an inference to confirm, refilled only when the feeling itself moves."""
    started = walk.advance(abcde, {"belief": stage("reflect", {"belief": BELIEF})}, None, "not_yet",
                           in_force="belief", report=judged(), known={"feeling": "anxious"})
    entry = started.entries["consequence"]
    assert entry["parts"]["felt"] == {"said": "anxious", "source": "inferred"}
    rejected = walk.advance(abcde, started.entries, [got("felt", rejected=True)], None, in_force="consequence",
                            known={"feeling": "anxious"})
    assert "felt" not in rejected.entries["consequence"]["parts"], "a rejected inference is not asked of them again"
    moved = walk.advance(abcde, rejected.entries, None, "not_yet", in_force="consequence",
                         known={"feeling": "overwhelmed"})
    assert moved.entries["consequence"]["parts"]["felt"]["said"] == "overwhelmed"
    theirs = walk.advance(abcde, {"consequence": stage("collecting", {"felt": "guilty"})}, None, "not_yet",
                          in_force="consequence", known={"feeling": "overwhelmed"})
    assert theirs.entries["consequence"]["parts"]["felt"]["said"] == "guilty"


def test_a_stage_reached_whose_parts_the_reply_answered_in_full_opens_as_the_reading(abcde):
    read = {"consequence": stage("read", {"felt": "guilty", "did": "you don't start"},
                                 read={"felt": "guilty", "did": "you don't start"})}
    moved = walk.advance(abcde, {"belief": stage("reflect", {"belief": BELIEF})}, None, "not_yet", in_force="belief",
                         report=judged(got("felt", "guilty"), got("did", "you don't start")))
    assert moved.entries["consequence"]["step"] == "read"
    assert moved.entries["consequence"]["read"] == read["consequence"]["read"]
    partly = walk.advance(abcde, {"belief": stage("reflect", {"belief": BELIEF})}, None, "not_yet", in_force="belief",
                          report=judged(got("did", "you don't start")))
    assert partly.entries["consequence"]["step"] == "collecting"


# The reply each step renders.

def render(abcde, walked, text="", style="directive", known=None):
    return walk.reply_text(abcde, walked, text=text, style=style, thread_id=THREAD, known=known)


def test_the_letter_line_opens_a_stage_once_and_one_the_model_wrote_is_dropped(abcde):
    """muhammad, 2026-10-17: "A is for Activating Event." only on the reply that reaches the stage."""
    reaches = walk.Walked({}, "belief", "belief")
    assert render(abcde, reaches, "What did you tell yourself?") == ("B is for Belief. What did you tell yourself?", [])
    stays = walk.Walked({}, "belief", None)
    assert render(abcde, stays, "What did you tell yourself?") == ("What did you tell yourself?", [])
    assert render(abcde, stays, "B is for Belief. What did you tell yourself?") == (
        "What did you tell yourself?", ["dropped a letter line"],
    )
    assert render(abcde, walk.Walked({}, "somatic_checkin", None), "Thank you.")[0] == "Thank you."


def test_a_stage_reached_is_manis_own_text_with_the_new_letter_when_it_asks(abcde):
    own = "So the thought is that it can't all get done. Is that how it sits with you?"
    reached = walk.Walked({"belief": stage("read", {"belief": BELIEF})}, "belief", "belief")
    assert render(abcde, reached, own) == (f"B is for Belief. {own}", [])


def test_a_reading_that_asks_nothing_falls_back_to_the_clients_line_or_a_phrase(abcde):
    reading = walk.Walked({"activate": stage("read", {"event": "being left out of meetings"})}, "activate", "activate")
    text, notes = render(abcde, reading, "Left out of meetings.", style="reflective")
    assert text == ("A is for Activating Event. You've mentioned being left out of meetings. "
                    "Is that where these concerns began?")
    assert notes == ["confirm text unusable"]
    on_b = walk.Walked({"belief": stage("read", {"belief": "I am useless"})}, "belief", "belief")
    phrase = walk.confirm_phrase(abcde, "belief", THREAD)
    assert render(abcde, on_b, "You think you're useless.") == (
        f"B is for Belief. You mentioned I am useless. {phrase}", ["confirm text unusable"],
    )


def test_a_missing_part_is_asked_with_the_words_it_refers_to_from_an_earlier_stage(abcde):
    entries = {"belief": stage("done", {"belief": BELIEF}), "consequence": stage("collecting", {"did": "you don't start"})}
    reached = walk.Walked(entries, "consequence", "consequence")
    assert render(abcde, reached, "That sounds hard.") == (
        "C is for Consequences. And when you believe I won't get it all done, how does that leave you feeling?",
        ["gap asks nothing"],
    )


def test_a_part_question_that_cannot_name_what_it_refers_to_falls_back_to_the_stages_own_question(abcde):
    reached = walk.Walked({"consequence": stage("collecting", {"did": "you don't start"})}, "consequence", "consequence")
    assert render(abcde, reached, "That sounds hard.") == (
        "C is for Consequences. How did that thought affect how you felt or what you did?", ["gap asks nothing"],
    )


def test_the_event_is_asked_with_their_own_word_for_the_feeling_when_nothing_is_known(abcde):
    start = walk.start(abcde, None, judged())
    assert render(abcde, start, "Thanks.", known={"feeling": "overwhelmed"}) == (
        "A is for Activating Event. What's been happening that's left you feeling overwhelmed?",
        ["missing asks nothing"],
    )
    assert render(abcde, start, "Thanks.", style="supportive", known={"feeling": "Overwhelmed"})[0].endswith(
        "left you feeling so overwhelmed?")
    assert render(abcde, start, "Thanks.") == (
        "A is for Activating Event. What's been happening that's behind this?", ["missing asks nothing"],
    )


def test_a_stage_left_unjudged_gets_the_stages_own_question_and_no_note(abcde):
    reached = walk.Walked({}, "belief", "belief", unjudged=True)
    assert render(abcde, reached, "What did you tell yourself?") == (
        "B is for Belief. What did you start telling yourself about what was happening?", [],
    )


def test_a_reply_that_stays_with_no_text_asks_the_next_missing_part(abcde):
    stays = walk.Walked({"consequence": stage("collecting", {"did": "you don't start"}),
                         "belief": stage("done", {"belief": BELIEF})}, "consequence", None)
    text, notes = render(abcde, stays, "")
    assert text.startswith("And when you believe") and notes == ["stay text empty"]


def test_the_question_a_reply_ends_on_is_kept_on_its_stage(abcde):
    walked = walk.with_last_ask(abcde, walk.Walked({}, "belief", None), "I see. What did you tell yourself?")
    assert walked.entries["belief"]["last_ask"] == "What did you tell yourself?"
    assert walk.with_last_ask(abcde, walk.Walked({}, "belief", None), "I see.").entries == {}
    assert walk.with_last_ask(abcde, walk.Walked({}, "belief", None, stopped=True), "Right?").entries == {}


# What the reply is told, and what a person watching sees.

def test_each_step_tells_the_reply_what_its_text_is_for(abcde):
    collecting = walk.next_line(abcde, {}, "consequence")
    assert "Report in stage_updates every part their message gives." in collecting
    assert "the first missing part (stage_missing)" in collecting and "stage_last_question" in collecting
    read = walk.next_line(abcde, {"belief": stage("read", {"belief": BELIEF})}, "belief")
    assert "Your last reply gave your reading." in read
    assert "answer agreed: your text asks one question about what they take from it (how true the thought feels" in read
    assert "the walk reaches consequence: " in read
    plain = walk.next_line(abcde, {"activate": stage("read", {"event": "x"})}, "activate")
    assert "answer agreed: the walk reaches belief" in plain
    reflect = walk.next_line(abcde, {"belief": stage("reflect", {"belief": BELIEF})}, "belief")
    assert "Whatever they answer, even I don't know, the stage ends" in reflect
    closing = walk.next_line(abcde, {}, "effective")
    assert "the questions end, and the body check-in is sent after your text" in closing


def test_the_ledger_view_reads_the_store_after_the_turn(abcde):
    stored = {"activate": stage("done", {"event": "left out"}),
              "belief": stage("collecting", {"belief_type": "all or nothing"}),
              "dispute": stage("read", {"evidence": "they never said why"})}
    rows = walk.ledger_view(abcde, stored, "belief")
    # Stored ahead by an earlier version, so not reached until the walk gets there.
    assert [(r["stage"], r["status"], r["asking"]) for r in rows] == [
        ("activate", "done", False), ("belief", "partial", True), ("consequence", "not_reached", False),
        ("dispute", "not_reached", False), ("effective", "not_reached", False),
    ]
    assert rows[0]["title"] == "A: Activating Event" and rows[0]["known"] == "left out"
    assert walk.ledger_view(abcde, {"belief": stage("reflect", {"belief": BELIEF})}, "belief")[1]["status"] == "reflecting"
    assert walk.ledger_view(abcde, {}, "belief")[1]["status"] == "missing"


def test_the_confirm_phrase_is_stable_per_thread_and_differs_between_neighbouring_stages(abcde):
    for thread in (THREAD, uuid.uuid4(), uuid.uuid4()):
        phrases = [walk.confirm_phrase(abcde, s, thread) for s in ("belief", "consequence", "dispute")]
        assert phrases == [walk.confirm_phrase(abcde, s, str(thread)) for s in ("belief", "consequence", "dispute")]
        assert phrases[0] != phrases[1] != phrases[2]
        assert set(phrases) <= set(abcde.confirm_phrases)


def test_the_understanding_the_walk_reads_has_the_keys_the_content_binds_parts_to(abcde):
    bound = {p["from"].removeprefix("understanding.") for s in walk.content_stages(abcde)
             for p in walk.specs(abcde, s) if p.get("from")}
    assert bound <= set(understanding.KEYS)
