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
    assert walked.entries["belief"] == {"said": "I am useless", "status": "done"}
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
        "C is for Consequences. When you believe that, how does it affect how you feel and what you do?", [],
    )
    missing = walk.advance(abcde, stored, None, "agreed", in_force="belief", report=judged("missing"))
    assert not missing.unjudged and "consequence" not in missing.entries
    assert render(abcde, missing, text=own, style="directive") == (f"C is for Consequences. {own}", [])


def test_a_judgement_of_the_next_stage_on_a_turn_that_stays_is_neither_stored_nor_flagged(abcde):
    stayed = walk.advance(abcde, {}, None, "not_yet", in_force="belief", report=judged("known", "frustrated"))
    assert stayed.phase == "belief" and "consequence" not in stayed.entries
    assert not stayed.unjudged and stayed.notes == []


def test_the_stage_reached_after_not_knowing_is_said_back_from_the_judgement(abcde):
    """Thread 4b93d612: once they answer, the walk reaches the next stage and the reply's confirmation
    of it is used."""
    first = walk.advance(abcde, {}, None, "not_yet", in_force="belief")
    second = walk.advance(abcde, first.entries, [said("belief", "I am not good enough")], "answered",
                          in_force="belief", report=judged("partial", "you felt frustrated"))
    own = "You mentioned feeling frustrated. Is that how this belief has affected you?"
    assert render(abcde, second, text=own, style="directive") == (f"C is for Consequences. {own}", [])


def test_not_knowing_never_moves_the_walk_however_often_it_is_said(abcde):
    """muhammad, 2026-10-21: a stage that is not clear keeps the conversation on it. The second not_yet
    used to let it go, which ended frameworks having helped no one."""
    walked = walk.advance(abcde, {}, None, "not_yet", in_force="belief")
    for _ in range(5):
        walked = walk.advance(abcde, walked.entries, None, "not_yet", in_force="belief")
        assert (walked.phase, walked.reached) == ("belief", None)
    assert walked.notes == []


def test_a_stage_said_back_moves_only_when_they_confirm_or_correct_it(abcde):
    """A stage already known is confirmed by them, never passed. Not yet, or a stop, leaves it where it is."""
    stored = {"belief": {"said": "I am useless", "status": "known"}}
    assert walk.advance(abcde, stored, None, "not_yet", in_force="belief").phase == "belief"
    assert walk.advance(abcde, stored, None, "stop", in_force="belief").phase == "belief"
    assert walk.advance(abcde, stored, None, "agreed", in_force="belief").phase == "consequence"
    corrected = walk.advance(abcde, stored, [said("belief", "I let them down", corrected=True)], "corrected",
                             in_force="belief")
    assert (corrected.phase, corrected.entries["belief"]["said"]) == ("consequence", "I let them down")


def test_an_answer_that_cannot_be_true_of_the_stage_is_read_as_not_yet(abcde):
    """AC-2, AC-12: agreed only answers a check of their words, and answered brings words for the stage."""
    asked = walk.advance(abcde, {}, None, "agreed", in_force="belief")
    assert asked.phase == "belief" and asked.notes == ["stage answer invalid: agreed"]
    wordless = walk.advance(abcde, {}, [said("dispute", "x")], "answered", in_force="belief")
    assert wordless.phase == "belief" and "stage answer invalid: answered" in wordless.notes
    with_words = walk.advance(abcde, {}, [said("belief", "I am useless")], "answered", in_force="belief")
    assert with_words.phase == "consequence"
    assert with_words.entries["belief"]["said"] == "I am useless"


def test_leaving_the_last_stage_enters_the_body_check_in(abcde):
    """Whether they would like to check in with their body is asked first (muhammad, 2026-10-27)."""
    left = walk.advance(abcde, {}, [said("effective", "I don't know yet")], "answered", in_force="effective")
    assert (left.phase, left.reached) == ("somatic_ask", None)


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
    assert text == "B is for Belief. When that happens, what thought worries you most?"
    assert notes == ["missing asks nothing"]


def test_a_missing_event_is_asked_with_their_own_word_for_the_feeling(abcde):
    start = walk.start(abcde, None, judged("missing"))
    assert render(abcde, start, feeling="overwhelmed")[0] == (
        "A is for Activating Event. What's been happening that's left you feeling so overwhelmed?"
    )
    assert render(abcde, start) == (
        "A is for Activating Event. What's been happening that's made things feel so hard?",
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
    assert text.endswith("how does it affect how you feel and what you do?")
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


def test_once_they_add_to_a_partial_stage_its_gap_is_dropped(abcde):
    partial = {"said": "your team works overtime too", "status": "partial", "gap": "challenge"}
    full = walk.merge({"dispute": partial}, [said("dispute", "nothing really challenges it")], abcde, in_force="dispute")
    assert "gap" not in full.entries["dispute"]


def test_the_part_still_to_ask_is_kept_while_the_stage_is_partial_and_dropped_when_it_is_known(abcde):
    """muhammad, 2026-10-21 (sister thread): D asked what supports the belief and, on later turns, never
    asked what might challenge it, because the stored gap was dropped by the next update. The part still to
    ask is kept until the stage is known; only an id the stage has a line for counts."""
    partial = {"said": "family should always help", "status": "partial", "gap": "challenge"}

    def update(status: str, gap: str | None = None) -> StageUpdate:
        return StageUpdate(stage="dispute", said="we always help family", status=status, gap=gap)

    def merged(update: StageUpdate) -> dict:
        return walk.merge({"dispute": partial}, [update], abcde, in_force="dispute").entries["dispute"]

    assert merged(update("partial"))["gap"] == "challenge"
    assert merged(update("partial", "information"))["gap"] == "information"
    assert merged(update("partial", "no such line"))["gap"] == "challenge"
    assert "gap" not in merged(update("known"))


def test_d_support_said_on_a_stay_turn_leaves_the_challenge_still_to_ask(abcde):
    """The walk stays on D, stores what supports the belief, and remembers that the challenge was not asked."""
    on_d = {"belief": {"said": "I should help", "status": "done"}, "consequence": {"said": "guilty", "status": "done"}}
    stayed = walk.advance(abcde, on_d, [StageUpdate(stage="dispute", said="family always helps", status="partial",
                                                    gap="challenge")], "not_yet", in_force="dispute")
    assert stayed.phase == "dispute" and stayed.reached is None
    assert stayed.entries["dispute"] == {"said": "family always helps", "status": "partial", "gap": "challenge"}


def test_the_possibilities_go_under_the_models_own_question_and_never_under_the_clients_line(abcde):
    """muhammad, 2026-10-22: framework replies carry the same mirror, question, possibilities as the chat
    before them. They answer the model's own question, so they are dropped when the client's line is sent."""
    options = "Do you feel trapped, overwhelmed by the responsibility, or worried about letting others down"
    stayed = walk.Walked({"belief": {"status": "missing", "tries": 1}}, "belief", None)
    own = "You're not sure what you told yourself. What was going through your mind?"
    text, _ = walk.reply_text(abcde, stayed, text=own, style="directive", thread_id=THREAD, feeling=None,
                              options=options)
    assert text == f"{own}\n\n{options}?"

    reached_missing = walk.Walked({"belief": {"status": "missing"}}, "belief", "belief", unjudged=True)
    sent, _ = walk.reply_text(abcde, reached_missing, text="Anything.", style="directive", thread_id=THREAD,
                              feeling=None, options=options)
    assert options not in sent, "the client's own line is not followed by possibilities written for another question"


def test_a_new_thought_or_feeling_brings_the_stages_already_passed_up_to_date(abcde):
    """muhammad, 2026-10-27: at D they say "I think I'm just a bad brother". The framework stays on D, and B, already
    passed, takes the new thought; a new feeling joins C. Stages ahead are judged when the walk reaches them."""
    from mani.chat import picture
    from mani.llm.schema import BeliefEntry, FeelingEntry, PictureUpdate

    stored = {
        "activate": {"said": "your brother is in hospital", "status": "done"},
        "belief": {"said": "work will stop you leaving", "status": "done"},
        "consequence": {"said": "you feel guilty.", "status": "done"},
        "dispute": {"said": "the deadline", "status": "partial", "gap": "challenge"},
    }
    before = {"beliefs": [{"belief": "work will stop you leaving", "kind": "thought"}], "feelings": [{"feeling": "guilty"}]}
    after = picture.merge(before, PictureUpdate(
        beliefs=[BeliefEntry(belief="you're a bad brother", kind="thought"),
                 BeliefEntry(belief="he cannot reach the bathroom alone", kind="happening")],
        feelings=[FeelingEntry(feeling="ashamed")],
    ))

    synced, notes = walk.from_picture(abcde, stored, before, after, in_force="dispute")
    assert synced["belief"] == {"said": "you're a bad brother", "status": "done"}
    assert synced["consequence"] == {"said": "you feel guilty, and you feel ashamed", "status": "done"}
    assert synced["activate"] == stored["activate"] and synced["dispute"] == stored["dispute"]
    assert notes == ["belief updated from the picture", "consequence updated from the picture"]
    assert stored["belief"]["said"] == "work will stop you leaving", "the stored entries are never changed in place"

    # On B itself, the stage in force takes their words from the reply, so nothing before it changes.
    assert walk.from_picture(abcde, stored, before, after, in_force="belief")[0] == stored
    # A turn that adds nothing to the picture changes nothing.
    assert walk.from_picture(abcde, stored, after, after, in_force="dispute") == (stored, [])


def test_a_turn_with_nothing_new_is_a_stall_and_talking_it_through_never_is():
    """muhammad, 2026-10-27: the framework steps out when it stops helping, and stays while they bring in something
    new. A turn that adds to the picture or to the stage's own words resets the count; a move clears it all."""
    before = {"dispute": {"said": "the deadline", "status": "partial", "gap": "challenge"}}
    once = walk.after_turn(before, before, "dispute", moved=False, shift="nothing_new", offered_exit=False)
    assert once["dispute"]["stalls"] == 1
    twice = walk.after_turn(once, once, "dispute", moved=False, shift=None, offered_exit=True)
    assert (twice["dispute"]["stalls"], twice["dispute"]["exit_offered"]) == (2, True)
    talked = walk.after_turn(twice, twice, "dispute", moved=False, shift="adds", offered_exit=False)
    assert talked["dispute"] == before["dispute"], "talking it through resets the stalls and the offer is read once"
    newer = {"dispute": {"said": "nobody told me", "status": "partial", "gap": "challenge"}}
    assert "stalls" not in walk.after_turn(once, newer, "dispute", moved=False, shift=None, offered_exit=False)["dispute"]
    assert walk.after_turn(twice, before, "dispute", moved=True, shift=None, offered_exit=False) == before
    assert walk.after_turn({}, {}, "belief", moved=False, shift="adds", offered_exit=False) == {}


def test_a_deeper_core_found_mid_framework_is_what_b_looks_at(abcde):
    """muhammad, 2026-10-28: B went to "I've ruined everything", the first thought, when what it led to was "I'm not
    capable of change". A core seen deeper takes B ahead of any other new thought."""
    from mani.chat import picture
    from mani.llm.schema import BeliefEntry, CoreEntry, PictureUpdate

    stored = {
        "activate": {"said": "you missed a workout", "status": "done"},
        "belief": {"said": "you've ruined everything", "status": "done"},
        "consequence": {"said": "you feel guilty", "status": "done"},
    }
    before = {"beliefs": [{"belief": "you've ruined everything", "kind": "thought"}]}
    after = picture.merge(before, PictureUpdate(
        beliefs=[BeliefEntry(belief="other people manage it", kind="thought")],
        core=CoreEntry(belief="you're not capable of change", feeling="shame", about="self"),
    ))
    synced, _ = walk.from_picture(abcde, stored, before, after, in_force="dispute")
    assert synced["belief"]["said"] == "you're not capable of change"


def test_the_stage_that_names_the_thought_starts_from_the_confirmed_core_in_both_frameworks():
    import pathlib

    from scripts.seed import parse_framework

    frameworks = pathlib.Path(__file__).parents[2] / "content/frameworks"
    b = parse_framework(frameworks / "abcde.md")["stages"]["belief"]["reach"]
    thought = parse_framework(frameworks / "thought_reframe.md")["stages"]["thought"]["reach"]
    assert "core belief" in b and "counts only when it is the core" in b
    assert "core belief" in thought and "not the first thought" in thought


def test_every_stage_is_confirmed_on_its_own_one_yes_at_a_time(abcde):
    """The client, 2026-10-29: Step 1 and Step 2 were said back in one reply, which skipped the yes to each. The
    start turn stores only the first stage, and a yes moves exactly one stage."""
    started = walk.start(abcde, [said("belief", "you matter less to them")], judged("known", "the pattern"))
    assert set(started.entries) == {"activate"} and "dropped update for belief" in started.notes
    moved = walk.advance(abcde, started.entries, None, "agreed", in_force="activate",
                         report=judged("known", "you matter less to them"))
    assert moved.reached == "belief" and moved.phase == "belief"


def test_something_meaningful_added_to_a_stage_said_back_is_explored_before_the_walk_moves_on(abcde):
    """The client meeting, 2026-11-03: A, B and C, already answered in the chat, went by with "yes, yes". A stage said
    back invites them to add; what they add is explored on that stage, counted, and the walk moves on once they agree."""
    known = {"activate": {"said": "you keep checking when you try to relax", "status": "known"}}
    first = walk.advance(abcde, known, [said("activate", "it's worst at night, when I'm alone")], "explore",
                         in_force="activate", report=judged("known", "if you don't check, it'll be your fault"))
    assert (first.phase, first.reached) == ("activate", None), "the stage stays while Mani explores it"
    assert first.entries["activate"] == {
        "said": "it's worst at night, when I'm alone", "status": "known", walk.EXPLORED: 1,
    }
    assert "belief" not in first.entries, "the stage ahead is judged only when the walk reaches it"
    moved = walk.advance(abcde, first.entries, None, "agreed", in_force="activate",
                         report=judged("known", "if you don't check, it'll be your fault"))
    assert (moved.phase, moved.reached) == ("belief", "belief")
    assert moved.entries["activate"] == {"said": "it's worst at night, when I'm alone", "status": "done"}


def test_a_stage_explores_as_long_as_each_turn_opens_a_new_part_and_keeps_what_it_opened(abcde):
    """muhammad, 2026-11-06: "the goal is not to reduce the number of questions, it is to make every question earn its
    place". Three questions at C are right when each opens a different part; none is asked twice."""
    entries = {"consequence": {"said": "I hold back in meetings", "status": "known"}}
    for turn, opened in enumerate((["feelings"], ["actions", "feelings"], ["in_the_moment"]), start=1):
        stayed = walk.advance(abcde, entries, None, "explore", in_force="consequence")
        assert stayed.phase == "consequence" and stayed.entries["consequence"][walk.EXPLORED] == turn
        entries = walk.covered(abcde, stayed.entries, "consequence", opened)
    assert entries["consequence"][walk.COVERED] == ["feelings", "actions", "in_the_moment"]
    assert walk.covered(abcde, entries, "consequence", ["not_a_part"]) == entries, "only the stage's own parts count"
    done = {"consequence": {"said": "x", "status": "done"}}
    assert walk.covered(abcde, done, "consequence", ["feelings"]) == done, "a stage left behind is never touched"


def test_explore_counts_only_on_a_stage_said_back_and_the_other_answers_move_as_before(abcde):
    partial = {"consequence": {"said": "I felt bad", "status": "partial"}}
    stays = walk.advance(abcde, partial, None, "explore", in_force="consequence")
    assert stays.phase == "consequence" and walk.EXPLORED not in stays.entries["consequence"]
    assert "stage answer invalid: explore" in stays.notes
    known = {"activate": {"said": "the birthday", "status": "known", walk.EXPLORED: 1}}
    for answer in ("agreed", "corrected", "answered"):
        update = [said("activate", "the group chat", "known", corrected=answer == "corrected")] \
            if answer != "agreed" else None
        moved = walk.advance(abcde, known, update, answer, in_force="activate", report=judged("missing"))
        assert moved.phase == "belief", answer
    assert walk.advance(abcde, known, None, "not_yet", in_force="activate").phase == "activate"
    assert "explore" not in walk.MOVES


def test_a_stage_not_said_back_answered_with_its_words_moves_whatever_the_reply_called_it(abcde):
    """The career chat, 2026-11-03: E waited for the path, they gave it, the reply called it explore (or agreed), the
    walk stayed on E, and the body check-in came twice. With words for the stage it is answered; without, nothing moves."""
    partial = {"effective": {"said": "missed promotions don't prove I'm not good enough", "status": "partial",
                             "gap": "path"}}
    for answer in ("explore", "agreed"):
        moved = walk.advance(abcde, partial, [said("effective", "talk to my manager about expectations")], answer,
                             in_force="effective")
        assert moved.phase == "somatic_ask", answer
        assert f"{answer} with words for a stage not said back read as answered" in moved.notes
        stays = walk.advance(abcde, partial, None, answer, in_force="effective")
        assert stays.phase == "effective" and f"stage answer invalid: {answer}" in stays.notes


def test_where_the_new_view_forms_is_flagged_in_both_frameworks(abcde):
    import pathlib

    from scripts.seed import parse_framework

    assert walk.new_view(abcde, "effective")
    assert not any(walk.new_view(abcde, s) for s in ("activate", "belief", "consequence", "dispute"))
    reframe = parse_framework(pathlib.Path(__file__).parents[2] / "content/frameworks/thought_reframe.md")["stages"]
    assert [s for s, body in reframe.items() if body.get("new_view")] == ["replacement"]


def test_a_stage_that_stays_asks_its_own_question_in_place_of_a_dropped_one(abcde):
    entries = {"effective": {"said": "x", "status": "partial", "gap": "path"}}
    assert walk.stay_question(abcde, entries, "effective", "directive") == "What would you like to do with that new way of seeing it?"


def test_e_reached_with_only_the_path_or_a_practice_to_ask_asks_the_new_belief_first(abcde):
    """The "can't say no" chat, 2026-11-03: E was reached as partial with the gap practice, so Mani wrote the new belief
    for them and asked where they could practise it. What they said in D is never the new belief."""
    stored = {"dispute": {"said": "my manager missed me when I was on leave", "status": "partial", "gap": "challenge"}}
    for gap in ("practice", "path"):
        moved = walk.advance(abcde, stored, [said("dispute", "they value my input", "known")], "answered",
                             in_force="dispute", report=judged("partial", "your value isn't only what you do", gap))
        assert moved.reached == "effective" and moved.first_gap, gap
        assert moved.entries["effective"]["gap"] == "belief"
        assert f"effective reached as partial ({gap}): asks belief first" in moved.notes
        text, notes = render(abcde, moved, text=(
            "Your manager missed having you around. What's one upcoming situation where you could pause first?"
        ))
        assert text == ("E is for Effective New Belief. Your manager missed having you around. "
                        "Knowing both sides of it, what would you tell yourself now about that thought?")
        assert "own question for a later part dropped" in notes

    asked = walk.advance(abcde, stored, [said("dispute", "they value my input", "known")], "answered",
                         in_force="dispute", report=judged("partial", "your value isn't only what you do", "belief"))
    assert not asked.first_gap and asked.entries["effective"]["gap"] == "belief"
    known = walk.advance(abcde, stored, [said("dispute", "they value my input", "known")], "answered",
                         in_force="dispute", report=judged("known", "I matter for more than what I do"))
    assert not known.first_gap and known.entries["effective"]["status"] == "known", "a view they formed still counts"


def test_only_the_stage_where_the_new_view_forms_asks_a_gap_first():
    from scripts.seed import FRAMEWORKS_DIR, parse_framework

    abcde = parse_framework(FRAMEWORKS_DIR / "abcde.md")["stages"]
    reframe = parse_framework(FRAMEWORKS_DIR / "thought_reframe.md")["stages"]
    assert {s: b["first_gap"] for s, b in abcde.items() if b.get("first_gap")} == {"effective": "belief"}
    assert {s: b["first_gap"] for s, b in reframe.items() if b.get("first_gap")} == {"replacement": ["thought", "believe", "step"]}
    for stages in (abcde, reframe):
        for stage, body in stages.items():
            if first := body.get("first_gap"):
                ids = {b.get("id") for b in body["if_unclear"]}
                assert set([first] if isinstance(first, str) else first) <= ids, stage


@pytest.fixture(scope="module")
def reframe() -> Framework:
    parsed = parse_framework(FRAMEWORKS_DIR / "thought_reframe.md")
    somatic = load_somatic_stages()
    return Framework(
        id=parsed["id"], name=parsed["name"], summary=parsed["summary"], body="b",
        phases=parsed["phases"] + list(somatic), stages={**parsed["stages"], **somatic},
        confirm_phrases=parsed["confirm_phrases"],
    )


def test_step_5_asks_for_the_thought_in_their_words_first_and_keeps_one_they_only_have_to_believe(reframe):
    """The same as E: what they said in Step 4 is the material, never the replacement thought. A thought they said
    themselves and only have to believe is kept, as the client's ready_when asks."""
    stored = {"alternative": {"said": "maybe they were just busy", "status": "partial"}}
    step = dict(in_force="alternative")
    for gap in (None, "other"):
        moved = walk.advance(reframe, stored, [said("alternative", "maybe they were just busy", "known")], "answered",
                             **step, report=judged("partial", "you matter to them even when they're busy", gap))
        assert moved.reached == "replacement" and moved.first_gap, gap
        assert moved.entries["replacement"]["gap"] == "thought"
        text, _ = walk.reply_text(reframe, moved, text="Maybe they were busy. Does that feel true to you?",
                                  style="directive", thread_id=THREAD, feeling=None)
        assert text.endswith("Knowing what you've looked at, what would you tell yourself now about that thought?")
        assert "Does that feel true" not in text
    believe = walk.advance(reframe, stored, [said("alternative", "maybe they were just busy", "known")], "answered",
                           **step, report=judged("partial", "I matter to them even when they're busy", "believe"))
    assert not believe.first_gap and believe.entries["replacement"]["gap"] == "believe"
    accurate = walk.advance(reframe, stored, [said("alternative", "there is no other explanation", "known")], "answered",
                            **step, report=judged("partial", "the concern is real", "step"))
    assert not accurate.first_gap and accurate.entries["replacement"]["gap"] == "step", "an accurate thought is never reframed"


def test_a_message_that_asks_something_never_moves_the_stage():
    """muhammad, 2026-11-05: "should I look at this thought or my numbness? Does one affect the other in any way" was
    read as an answer and the reply opened on Step 2."""
    for asked in ("should I look at this thought or my numbness? Does one affect the other in any way",
                  "does one affect the other", "What do you mean by that"):
        assert walk.held_by_question("answered", asked) == "not_yet", asked
        assert walk.held_by_question("agreed", asked) == "not_yet", asked
    assert walk.held_by_question("explore", "why does it hurt so much?") == "explore", "staying stays"
    assert walk.held_by_question("stop", "can we stop?") == "stop", "a wish to stop is still theirs"
    assert walk.held_by_question("answered", "the past 7 or 8 weeks") == "answered"
    assert walk.held_by_question("answered", "I think it's being blindsided again.") == "answered"


def test_the_last_stage_tells_the_reply_the_closing_choices_follow_while_the_body_check_in_is_paused():
    """muhammad, 2026-11-05: the model is told what code sends after its close, so it never promises a check-in."""
    from mani.models.rows import Framework

    paused = Framework(id="f", name="F", summary="s", body="b", phases=["offering", "a", "e", "somatic_closing"])
    full = paused.model_copy(update={"phases": ["offering", "a", "e", "somatic_ask", "somatic_closing"]})

    assert "Keep Chatting, Go to Library and Finish for Now after your text" in walk.next_line(paused, "e")
    assert "the body check-in after your text" in walk.next_line(full, "e")
