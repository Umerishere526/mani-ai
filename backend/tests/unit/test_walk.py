# ABOUTME: Checks the ABCDE walk: the merge of what they said, the one stage step, and each reply it renders.
# ABOUTME: Built on the real abcde.md and somatic stages, the same content that is seeded.

import uuid

import pytest

from mani.chat import walk
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


def said(stage: str, words: str, status: str = "known", corrected: bool | None = None) -> StageUpdate:
    return StageUpdate(stage=stage, said=words, status=status, corrected=corrected)


def judged(status: str, words: str | None = None, gap: str | None = None) -> NextStage:
    """The reply's judgement of the stage the walk reaches next."""
    return NextStage(status=status, said=words, gap=gap)


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
    assert merged.entries["activate"] == {"said": "dropped from the team meeting", "status": "done", "tries": 0,
                                          "was": ["left out of meetings"]}
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


def test_the_start_turn_clears_the_old_run_and_opens_on_a_judged_from_what_they_said(abcde):
    """AC-3, 2026-10-13: a new start never shows an old run's stages; A is judged when the walk reaches
    it, and nothing is stored for a later stage before the walk gets there."""
    walked = walk.start(abcde, [said("belief", "I am useless")], judged("known", "left out of meetings"))
    assert walked.entries == {"activate": {"said": "left out of meetings", "status": "known"}}
    assert (walked.phase, walked.reached, walked.unjudged) == ("activate", "activate", False)
    assert walked.notes == ["dropped update for belief"]


def test_a_move_answer_moves_exactly_one_stage_and_the_stage_reached_is_judged_then(abcde):
    """2026-10-13: the stage reached is filled from this turn's next_stage judgement of it; stage updates
    for a stage further on are dropped."""
    stored = {"belief": {"said": "I am useless", "status": "known"}}
    walked = walk.advance(abcde, stored, [said("dispute", "x")], "agreed", in_force="belief",
                          report=judged("known", "I stopped going"))
    assert (walked.phase, walked.reached, walked.unjudged) == ("consequence", "consequence", False)
    assert walked.entries["belief"] == {"said": "I am useless", "status": "done", "tries": 0}
    assert walked.entries["consequence"] == {"said": "I stopped going", "status": "known"}
    assert "dispute" not in walked.entries and "dropped update for dispute" in walked.notes


def test_a_stage_reached_without_a_judgement_is_asked_and_reported_apart_from_one_judged_missing(abcde):
    """Thread 4b93d612, 2026-10-14: a stage left unjudged gets the client's question, since the reply's
    text was not written for it, and is flagged; one judged missing gets Mani's own question."""
    stored = {"belief": {"said": "the timeline goes south", "status": "known"}}
    own = "How did thinking the timeline would go south affect how you felt or what you did?"
    unjudged = walk.advance(abcde, stored, None, "agreed", in_force="belief")
    assert unjudged.unjudged and "consequence" not in unjudged.entries
    assert render(abcde, unjudged, text=own, style="directive") == (
        "C is for Consequences. How did that thought affect how you felt or what you did?", [],
    )
    missing = walk.advance(abcde, stored, None, "agreed", in_force="belief", report=judged("missing"))
    assert not missing.unjudged and "consequence" not in missing.entries
    assert render(abcde, missing, text=own, style="directive") == (f"C is for Consequences. {own}", [])


def test_a_judgement_of_the_next_stage_on_a_turn_that_stays_is_neither_stored_nor_flagged(abcde):
    stayed = walk.advance(abcde, {}, None, "not_yet", in_force="belief", report=judged("known", "frustrated"))
    assert stayed.phase == "belief" and "consequence" not in stayed.entries
    assert not stayed.unjudged and stayed.notes == []


def test_a_stage_let_go_reaches_the_next_said_back_from_the_judgement(abcde):
    """Thread 4b93d612: when they skip a stage the walk moves, and [ctx] says so, so the reply's
    confirmation of the next stage is used."""
    first = walk.advance(abcde, {}, None, "not_yet", in_force="belief")
    second = walk.advance(abcde, first.entries, None, "let_go", in_force="belief",
                          report=judged("partial", "you felt frustrated"))
    own = "You mentioned feeling frustrated. Is that how this belief has affected you?"
    assert render(abcde, second, text=own, style="directive") == (f"C is for Consequences. {own}", [])


def test_a_question_holds_the_stage_without_a_try_then_their_yes_to_the_say_back_moves_it(abcde):
    """A question or push-back is answered and the stage held; it never spends a try. Their answer is
    then said back, and their yes to it moves on, not let_go."""
    first = walk.advance(abcde, {}, None, "asked", in_force="belief")
    second = walk.advance(abcde, first.entries, None, "asked", in_force="belief")
    assert (second.phase, second.entries["belief"].get("tries", 0)) == ("belief", 0)
    answered = walk.advance(abcde, second.entries, [said("belief", "I'll be let go")], "answered", in_force="belief")
    assert (answered.phase, answered.reached) == ("belief", None)
    agreed = walk.advance(abcde, answered.entries, None, "agreed", in_force="belief")
    assert agreed.phase == "consequence"
    assert not any("let go" in note for note in agreed.notes)


def test_questions_hold_a_stage_only_so_long_then_count_as_tries(abcde):
    """Past HELD_FOR_QUESTIONS, asked counts as not_yet, so a person who only asks is never held for ever,
    and on E the body check-in waits until then."""
    entries: dict = {}
    for _ in range(walk.HELD_FOR_QUESTIONS):
        held = walk.advance(abcde, entries, None, "asked", in_force="effective")
        assert held.phase == "effective"
        entries = held.entries
    tried = walk.advance(abcde, entries, None, "asked", in_force="effective")
    assert (tried.phase, tried.entries["effective"]["tries"]) == ("effective", 1)
    again = walk.advance(abcde, tried.entries, None, "asked", in_force="effective")
    assert (again.phase, again.entries["effective"]["tries"]) == ("effective", 2)


def test_an_answer_that_cannot_be_true_of_the_stage_is_read_as_not_yet(abcde):
    """AC-2, AC-12: agreed only answers a check of their words, and answered brings words for the stage."""
    asked = walk.advance(abcde, {}, None, "agreed", in_force="belief")
    assert asked.phase == "belief" and asked.notes == ["stage answer invalid: agreed"]
    wordless = walk.advance(abcde, {}, [said("dispute", "x")], "answered", in_force="belief")
    assert wordless.phase == "belief" and "stage answer invalid: answered" in wordless.notes
    with_words = walk.advance(abcde, {}, [said("belief", "I am useless")], "answered", in_force="belief")
    assert with_words.phase == "belief" and with_words.entries["belief"]["status"] == "known"
    assert with_words.entries["belief"]["said"] == "I am useless"


def test_a_plain_no_never_moves_the_stage_and_after_four_the_choice_is_offered(abcde):
    """Spec 0007, AC-1, AC-2: no counter moves a stage; at STALL_LIMIT the reply offers the choice."""
    entries: dict = {}
    for n in range(1, walk.STALL_LIMIT + 2):
        walked = walk.advance(abcde, entries, None, "not_yet", in_force="belief")
        entries = walked.entries
        assert (walked.phase, walked.reached, entries["belief"]["tries"]) == ("belief", None, n)
    assert not walk.next_line(abcde, {"belief": {"tries": walk.STALL_LIMIT - 1}}, "belief").startswith("They have stayed")
    stalled = walk.next_line(abcde, entries, "belief")
    assert stalled.startswith(
        f"They have stayed on belief for {walk.STALL_LIMIT + 1} replies. Your text offers the choice: "
        "keep going with it, skip it (answer let_go), or stop the questions here (answer stopped). "
    )
    assert "If not_yet, write the follow up for this stage, helped by stage_when_stuck when they don't know." in stalled


def test_stopping_the_questions_is_reported_and_moves_nothing(abcde):
    """Spec 0007, AC-3: the walk reports the stop and leaves the store as it was; the orchestrator records it."""
    stored = {"belief": {"said": "I am useless", "status": "known", "tries": 2}}
    walked = walk.advance(abcde, stored, None, "stopped", in_force="belief")
    assert (walked.phase, walked.reached, walked.stopped) == ("belief", None, True)
    assert walked.entries == stored
    assert walked.notes == ["belief stopped by them"]


def test_stopped_on_the_start_turn_is_ignored(abcde):
    started = walk.start(abcde, None, judged("missing"))
    assert (started.phase, started.reached, started.stopped) == ("activate", "activate", False)


def test_a_body_answer_at_the_closing_wins_over_stopped(abcde):
    walked = walk.advance(abcde, {}, None, "stopped", in_force="effective", body_answered=True)
    assert (walked.phase, walked.stopped) == ("somatic_checkin", False)
    assert "stage answer stopped ignored for a body answer" in walked.notes


def test_answered_stores_the_words_and_waits_for_their_yes_to_the_say_back(abcde):
    """Spec 0007 decision 6: substance first, then their agreement; answered never moves by itself."""
    walked = walk.advance(abcde, {"belief": {"status": "partial", "said": "too much"}},
                          [said("belief", "I won't get it all done", "known")], "answered", in_force="belief")
    assert (walked.phase, walked.reached) == ("belief", None)
    assert walked.entries["belief"] == {"said": "I won't get it all done", "status": "known"}
    assert "belief answered: said back for their yes" in walked.notes
    agreed = walk.advance(abcde, walked.entries, None, "agreed", in_force="belief", report=judged("missing"))
    assert (agreed.phase, agreed.reached) == ("consequence", "consequence")


def test_a_yes_to_the_say_back_of_a_partial_stage_stays_and_the_gap_is_asked(abcde):
    """Lolly's 6C: "yea" to a C that held only what they did moved on; now it stays on the gap."""
    stored = {"consequence": {"said": "so you don't start", "status": "partial", "gap": "feeling"}}
    walked = walk.advance(abcde, stored, None, "agreed", in_force="consequence")
    assert (walked.phase, walked.reached) == ("consequence", None)
    assert walked.entries["consequence"]["gap"] == "feeling"
    assert "stage answer invalid: agreed" in walked.notes


def test_a_correction_to_an_earlier_stage_keeps_its_old_words_and_holds_this_stage(abcde):
    """Spec 0007 decision 9: corrected in place with its history; nothing moves until Mani has asked about it."""
    stored = {"belief": {"said": "I won't get it all done", "status": "done", "tries": 0},
              "dispute": {"said": "nothing supports it", "status": "known"}}
    walked = walk.advance(abcde, stored, [said("belief", "I'm lazy", "known", corrected=True)], "agreed",
                          in_force="dispute")
    assert (walked.phase, walked.reached) == ("dispute", None)
    assert walked.entries["belief"] == {"said": "I'm lazy", "status": "done", "tries": 0,
                                        "was": ["I won't get it all done"]}
    assert "earlier stage corrected: clarified before moving" in walked.notes


def test_leaving_the_closing_enters_the_body_route_and_a_body_answer_wins(abcde):
    left = walk.advance(abcde, {"effective": {"said": "I can still start on one thing", "status": "known"}},
                        None, "agreed", in_force="effective")
    assert (left.phase, left.reached) == ("somatic_checkin", None)
    body = walk.advance(abcde, {}, None, "not_yet", in_force="effective", body_answered=True)
    assert body.phase == "somatic_checkin"
    assert body.notes == ["stage answer not_yet ignored for a body answer"]


def render(abcde, walked, text="", style="supportive", feeling=None):
    return walk.reply_text(abcde, walked, text=text, style=style, thread_id=THREAD, feeling=feeling)


def reached(entries: dict, stage: str) -> walk.Walked:
    """A turn whose walk reaches `stage` with `entries` stored."""
    return walk.Walked(entries, stage, stage)


def test_a_missing_stage_is_its_letter_line_then_manis_own_question_about_their_situation(abcde):
    """Thread 425f6a55, 2026-10-14: the client's bare question ("…about what was happening?") was met
    with "regarding?". Mani asks it about their situation, as the client's document adapts D, after the
    letter line code sends; a letter line the model wrote is dropped."""
    own = "What did you start telling yourself when your manager gave you work outside your responsibilities?"
    reached = walk.Walked({}, "belief", "belief")
    assert render(abcde, reached, text=own, style="directive") == (f"B is for Belief. {own}", [])
    assert render(abcde, reached, text=f"B is for Belief. {own}", style="directive") == (
        f"B is for Belief. {own}", ["dropped a letter line"],
    )


def test_a_missing_stage_whose_text_asks_nothing_falls_back_to_the_clients_question(abcde):
    text, notes = render(abcde, walk.Walked({}, "belief", "belief"), text="Thanks for telling me.", style="directive")
    assert text == "B is for Belief. What did you start telling yourself about what was happening?"
    assert notes == ["missing asks nothing"]


def test_a_missing_event_is_asked_with_their_own_word_for_the_feeling(abcde):
    start = walk.start(abcde, None, judged("missing"))
    assert render(abcde, start, feeling="overwhelmed")[0] == (
        "A is for Activating Event. What's been happening that's left you feeling so overwhelmed?"
    )
    assert render(abcde, start) == (
        "A is for Activating Event. What's been happening that's left things feeling so hard?",
        ["slot empty", "missing asks nothing"],
    )


def test_a_missing_event_keeps_the_clients_line_with_their_feeling_over_manis_question(abcde):
    """The client's Situation 3 for A is already about them, through their feeling word; without one,
    Mani's own question is used."""
    start = walk.start(abcde, None, judged("missing"))
    own = "What has been happening at work that you want to look at?"
    assert render(abcde, start, text=own, feeling="overwhelmed")[0] == (
        "A is for Activating Event. What's been happening that's left you feeling so overwhelmed?"
    )
    assert render(abcde, start, text=own) == (f"A is for Activating Event. {own}", ["slot empty"])


@pytest.mark.parametrize("status", ["known", "possible"])
def test_without_manis_own_confirmation_a_known_event_falls_back_to_the_clients_line(abcde, status):
    """AC-4: when Mani's own confirmation cannot be used, the client's confirm line carries their words."""
    start = walk.start(abcde, None, judged(status, "Being left out of meetings at work."))
    assert render(abcde, start, text="Being left out of meetings.", style="reflective")[0] == (
        "A is for Activating Event. You've mentioned being left out of meetings at work. "
        "Is that where these concerns began?"
    )


def test_their_words_inside_a_line_start_lowercase_except_i(abcde):
    """Live, 2026-10-13: "From what you've shared, The client changes..." (muhammad: lowercase the
    first word, except "I" and its contractions)."""
    start = walk.start(abcde, None, judged("possible", "I'm left out of meetings"))
    assert "You mentioned I'm left out of meetings. Is that" in render(abcde, start, text="Left out.")[0]
    assert render(abcde, walk.start(abcde, None, judged("missing")), feeling="Overwhelmed")[0].endswith("feeling so overwhelmed?")


def test_a_known_stage_is_its_letter_line_then_manis_own_confirmation(abcde):
    """muhammad's team lead, 2026-10-13: the model says back what they said and asks, in its own words,
    whether it is right; no fixed phrase is added and its question is kept."""
    own = "Here's what I understand: you've been telling yourself you're useless. Is that still how it feels?"
    assert render(abcde, reached({"belief": {"said": "I am useless", "status": "known"}}, "belief"), text=own) == (
        f"B is for Belief. {own}", [],
    )


def test_on_the_start_turn_a_is_manis_own_confirmation(abcde):
    """The yes turn judges A as the walk reaches it and writes for it at once, so its text is used for A."""
    start = walk.start(abcde, None, judged("known", "your boss criticized your work today"))
    own = "So it started when your boss criticized your work today. Is that where this began for you?"
    assert render(abcde, start, text=own) == (f"A is for Activating Event. {own}", [])


def test_a_confirmation_that_asks_nothing_falls_back(abcde):
    """Logged, so how often Mani's own confirmation cannot be used is known."""
    stored = {"belief": {"said": "I am useless", "status": "known"}}
    phrase = walk.confirm_phrase(abcde, "belief", THREAD)
    assert render(abcde, reached(stored, "belief"), text="You've been telling yourself you're useless.") == (
        f"B is for Belief. You mentioned I am useless. {phrase}", ["confirm text unusable"],
    )


def test_a_partial_stage_asks_only_the_gap_or_falls_back_to_the_clients_question(abcde):
    """AC-5."""
    stored = {"consequence": {"said": "I felt bad", "status": "partial"}}
    on_c = reached(stored, "consequence")
    gap = "What did you do after that?"
    assert render(abcde, on_c, text=gap) == (f"C is for Consequences. {gap}", [])
    text, notes = render(abcde, on_c, text="That sounds hard.")
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
    # Stored ahead by an earlier version, so not reached until the walk gets there.
    assert [(r["stage"], r["status"], r["asking"]) for r in rows] == [
        ("activate", "done", False), ("belief", "missing", True), ("consequence", "not_reached", False),
        ("dispute", "not_reached", False), ("effective", "not_reached", False),
    ]
    assert rows[0]["title"] == "A: Activating Event" and rows[0]["known"] == "left out"


# muhammad's Supportive runs, 2026-10-13: B seeded from the opening line and C from it (thread 7e3062ff),
# then C, D and E asked again though the person had said them (thread 7d102554).
SEEDED = {
    "activate": {"said": "your boss wants you to work overtime as a senior", "status": "done"},
    "belief": {"said": "you're questioning whether you're good at your job", "status": "known"},
    "consequence": {"said": "you're frustrated and questioning your ability", "status": "known"},
}


def test_stages_stored_ahead_by_an_earlier_version_are_ignored_and_judged_when_reached(abcde):
    """The stale C is never said back: the walk ignores it and judges C when it reaches it."""
    moved = walk.advance(abcde, SEEDED, None, "agreed", in_force="belief",
                         report=judged("known", "you and your team are paying for it"))
    assert moved.entries["consequence"] == {"said": "you and your team are paying for it", "status": "known"}
    assert "ignored stored ahead: consequence" in moved.notes
    stayed = walk.advance(abcde, SEEDED, None, "not_yet", in_force="belief")
    assert "consequence" not in stayed.entries


def test_yes_with_more_added_is_agreement_and_moves_on(abcde):
    """Thread 7d102554: "yes this weighing on my mind…" came back as answered with no new words for B."""
    moved = walk.advance(abcde, SEEDED, None, "answered", in_force="belief")
    assert moved.phase == "consequence"
    assert moved.entries["belief"]["said"] == SEEDED["belief"]["said"]
    assert "answered with no update read as agreed" in moved.notes


def test_a_correction_to_an_earlier_stage_is_kept_while_on_a_later_one(abcde):
    """Spec 0004, AC-8: the walk stays put and the earlier stage takes the new words."""
    on_d = {**SEEDED, "belief": {**SEEDED["belief"], "status": "done"}, "consequence": {"said": "x", "status": "done"}}
    fixed = walk.advance(abcde, on_d, [said("activate", "my manager moved my desk", "known", corrected=True)],
                         "not_yet", in_force="dispute")
    assert fixed.entries["activate"]["said"] == "my manager moved my desk"


def test_d_reached_with_only_support_said_asks_only_the_challenge(abcde):
    """Thread 4b93d612: they had said what supports the belief before D was reached. D is judged partial
    with the challenge as its gap, and without Mani's own question the client's line for the challenge
    is sent with their belief in it, never the whole D question again."""
    on_c = {"belief": {"said": "Because of your bad decision, others have to pay for it.", "status": "done"},
            "consequence": {"said": "you felt guilty", "status": "known"}}
    moved = walk.advance(abcde, on_c, None, "agreed", in_force="consequence",
                         report=judged("partial", "your team now works overtime too", gap="challenge"))
    assert moved.entries["dispute"]["gap"] == "challenge"
    text, notes = render(abcde, moved, text="That sounds hard.")
    assert text == ("D is for Dispute. What might make you question the belief that because of your bad "
                    "decision, others have to pay for it?")
    assert notes == ["gap asks nothing"]


def test_a_confirmation_let_go_without_their_words_stores_none(abcde):
    """Words they did not agree to never stand as done, so D never disputes them."""
    let_go = walk.advance(abcde, SEEDED, None, "let_go", in_force="belief")
    assert let_go.entries["belief"] == {"said": "", "status": "done", "tries": 0}


def test_once_they_add_to_a_partial_stage_its_gap_is_dropped(abcde):
    partial = {"said": "your team works overtime too", "status": "partial", "gap": "challenge"}
    full = walk.merge({"dispute": partial}, [said("dispute", "nothing really challenges it")], abcde, in_force="dispute")
    assert "gap" not in full.entries["dispute"]
