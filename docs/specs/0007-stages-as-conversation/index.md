# 0007. Each stage is a conversation: the walk moves on substance, the understanding keeps moving, and the check waits a turn

**Date**: 2026-10-16
**Status**: Approved 2026-10-16 (the four decisions below as recommended, plus decisions 5 to 10 under "Decisions taken")

## Summary

Lolly's review of 2026-10-16 ([message](../../client/messages/2026-10-16-two-styles-abcde-feedback.md), R17) found ABCDE run as a questionnaire: ask, answer, next letter; "I don't know" moved the walk on; a rejected new belief ended the framework; the body check-in followed either way. It also found one skipped answer before the framework: the reply that received the control answer summarised instead of engaging it.

All of it is in our code, not in the model. `walk.advance` moves on any answer in `MOVES` and lets a stage go after a second `not_yet`; the content's `ready_when` for C, D and E accepts a yes, a technicality or nothing; `context.may_check` lets the check ride on the reply that receives the control answer. This spec changes what moves a stage (the purpose met, in substance, in their words), removes every automatic move, gives the model a way to help when they are stuck, lets the person stop, makes the core issue a reading that keeps moving, and puts the check one turn after control.

The somatic cadence (R18) is a separate change after this one.

## Decisions muhammad is asked to make

1. **B to E are not stored ahead of the walk.** muhammad asked for stages judged from the first message. The journal records that exact design failing twice ([transcript-is-the-memory-2026-10-13](../../../mani-vault/Journal/transcript-is-the-memory-2026-10-13.md): "the seed of every stage at the yes went stale twice"). The reason it failed (a 20-message window, so the early guess was all the model had) is gone: the whole thread is in view and each stage is judged from it when reached. What muhammad wants recorded from the opening, the event that started it, is kept as `understanding.event` (AC-9). **Recommended: keep judging B to E when reached; record only the event ahead.**
2. **The check comes the turn after control is stored** (AC-10), so the reply that receives the control answer is an ordinary forward reply. One more exchange before the offer, against R5; it is the exchange Lolly's points 2 and 3 ask for. **Recommended: yes.**
3. **Stall limit 4**: after four replies on one stage Mani offers to keep going, skip, or stop (AC-2). No automatic move at any count.
4. **Stopping records the run as declined**, not completed (AC-3), so the next check waits six messages, not forty five.

## Decisions taken (muhammad, 2026-10-16)

The four above, as recommended. On top of them, from muhammad's instructions of the same day, weighed against Lolly's three messages:

5. **No letter line and no fixed script; the stage is shown in the side ledger** (muhammad, 2026-10-16, revising his first answer of the day). A stage's reply is Mani's own sentence built from their words: the say-back of a known stage, the question for a gap, the question for a missing stage. "A is for Activating Event." is not said; the chat tester's "What Mani knows" ledger shows each stage's letter, name and status at the side, as the apps will. The client's `confirm`, `missing` and `ask` lines are sent only as the logged fallback when Mani's text asks nothing. Overrides Lolly's point 4 of 2026-10-16, the ABCDE document and R12's letter line, and the Decision in force of 2026-10-13 ("Each stage opens with its letter and name"); the client must be told (Conflicts).
6. **A stage moves on substance and on their agreement.** `answered` and `corrected` store their words and never move the walk; the next reply says back what Mani now has for the stage and asks whether that is right; `agreed` moves it, and only while the stored status is known or possible with no gap. A yes to the say-back of a partial stage stays, and the gap is asked (Lolly's 6C). This is Lolly's 7.1 ("an answer is not completion") with muhammad's confirm-then-move flow on top.
7. **Mani's readings and distinctions are built only from their words**, inside the framework and in `when_stuck` help: never a new fact, person, motive, feeling or advice.
8. **A changed feeling is confirmed before it is stored.** When their message shows a feeling different from the stored one, code keeps the new word as pending (`understanding.feeling_asked`) and the reply asks whether it has changed; the next reply's `feeling_answer` stores it on a yes, and a no clears it. The first feeling, with nothing stored, is stored outright. In the opening chat and inside a stage alike.
9. **A change is corrected in place, named, and clarified before anything moves.** A correction to an earlier stage keeps the earlier words in the entry's `was`, and the walk holds the stage in force this turn while Mani names the change in one sentence and asks one question to be sure of it. A change to the issue, the event or the core issue, inside the framework or after it, keeps the earlier value in `understanding.history`, and the reply names it and asks one question; a finished framework stays finished. No walk backwards.
10. **The somatic cadence (R18) is built after this spec's live run, in the same pass**, as spec 0008: the client's introduction, then, where a body sensation is recorded, that sensation named before the five choices; an ambiguous sensation ("my eyes are burning") is asked about before any exercise.

### Acceptance criteria added

- **AC-13** (decision 5): `walk.reply_text` sends no `intro` letter line and uses Mani's own text first for every status it opens a stage with, confirmed, partial and missing; the client's line is taken only when that text asks nothing, logged as before ("confirm text unusable", "gap asks nothing", "missing asks nothing"). A's `missing` line no longer takes precedence over Mani's own question. The chat tester's ledger shows each stage's title and status beside the chat. `walk.CONFIRM_ASK` and `walk.reach_line` ask for the say-back in Mani's own words and say the stage moves only on their yes; "ask next_stage_ask as written" is gone.
- **AC-14** (decision 6): `walk.advance`: `answered` and `corrected` on the stage in force store the words and stay (`reached` is None, note "<stage> answered: said back for their yes", `tries` unchanged); `agreed` moves only when the stored entry is known or possible with no `gap`, otherwise it stays with the gap asked; `let_go` moves; `stopped` stays (AC-3). `walk.next_line` says each of these. The `stage_answer` description matches.
- **AC-15** (decision 8): `understanding.merge` holds a changed feeling as `feeling_asked` instead of storing it, stores it on `feeling_answer` yes (the old word appended to `history.feeling`), clears it on no, and replaces it when a newer word arrives while pending. `Reply.feeling_answer` exists only while a change is pending (`schema.reply_for(feeling_asked=True)`). `[ctx]` carries `feeling_change: <stored> -> <pending>` with its meaning on the turn after. `mani_base.understanding_them` says the reply asks about the change in one question. `test_a_changed_feeling_waits_for_their_yes` in `tests/unit/test_understanding.py`; an integration test for the two turns.
- **AC-16** (decision 9): `walk.merge` keeps the replaced words in `was` (the last three) on a correction; `walk.advance` holds the stage in force when an earlier stage was corrected this turn (note "earlier stage corrected: clarified before moving", `tries` unchanged); `understanding.merge` keeps every replaced value of `issue`, `event` and `core_issue` in `history` (the last three per key), carried through every merge and never rendered as a step. `mani_base.in_a_framework` and `ending` say: name the change in one sentence from their words and ask one question about it.
- **AC-17**: records as AC-12, and the Decision in force of 2026-10-14 on the client's `ask` edited in place.
- **AC-18** (decision 10): spec 0008 for R18, written after this spec's live run.

## Requirements

**User stories**:
- As a person in ABCDE, I want Mani to stay with me when I don't know, and help me look, rather than move to the next letter.
- As a person who rejects the new belief Mani offered back, I want it to keep working with me, and to let me stop if I want to.
- As a person whose answer reveals something new, I want the next reply to engage it, not summarise me.
- As muhammad, I want every one of these to be code or content I can point at, and tests that hold them.

**Acceptance criteria**:

- **AC-1**: No stage is ever let go by code. `walk.advance` moves only on `agreed`, `answered`, `corrected` or `let_go`, each still checked by `_counts`. A `not_yet` increments `tries` without bound. The second-try move and `context._TWO_TRIES` are deleted, with their prompt lines.
- **AC-2**: `walk.STALL_LIMIT = 4`. Once a stage's `tries` is at least 4 before the turn, `walk.next_line` opens with "They have stayed on <stage> for <tries> replies. Your text offers the choice: keep going with it, skip it (answer let_go), or stop the questions here (answer stopped)." Nothing moves without their answer.
- **AC-3**: `stopped` joins `StageAnswer`. On it the walk stays (`Walked.stopped` is true, entries unchanged, note `<stage> stopped by them`). The orchestrator records the run as `DECLINED` with phase null at this turn's count (the decline path), keeps `stages_known`, and sends the model's text with Chat More and Go to Library. On a start turn, or beside a body answer at the closing, `stopped` is ignored.
- **AC-4**: A stage may carry `when_stuck`, sent in `[ctx]` as `stage_when_stuck` and `next_stage_when_stuck`. `abcde.md` gives one for `dispute` and `effective`. `mani_base.any_stage` "they say they don't know" points to it and says it is never a reason to move on.
- **AC-5**: `consequence` is known only when they tied both a feeling and an action or avoidance to the belief; with one of the two it is partial with gap `feeling` or `doing`, and `_gap_line` renders the client-style question for the gap with B's words in it.
- **AC-6**: `dispute.ready_when` asks for substance: what supports the belief and what might challenge it both looked at, and the belief pulled apart from the conclusion they draw from it where the two are joined. "Not knowing for sure" is no longer enough on its own.
- **AC-7**: `effective`: a new belief they offer is reported partial with gap `fits`; the text says it back and asks whether it fits for them; known once they said it does. A rejected belief or "not sure" stays. The clause "or have looked at the belief and have no different one" leaves `ready_when` (the newer client message beats the ABCDE document; recorded under Conflicts).
- **AC-8**: `mani_base.in_a_framework` says: a stage is answered when `stage_ready_when` is met by what they said, never by a yes, an I don't know or a plan; there is no count; each letter builds on the one before and B's belief is named in their words in D and E; a skip is `let_go`, a stop is `stopped`. `response_format` reasoning step for the stage matches.
- **AC-9**: `understanding` gains `event`: the specific event or moment they describe that seems to have started this, kept from the first message it appears in, shown in `[ctx]`, never a step. `core_issue` is described to the model as its reading from what is happening and how they feel, revised whenever a later answer changes it, before or after the check and inside the framework; an `understanding_update.core_issue` on an `IN_STAGES` turn replaces the stored one.
- **AC-10**: `context.may_check` is false while any of the three steps is missing. The `once_control_is_answered` meaning is deleted. The earliest check answers their 4th message. Spec 0006 AC-2 and AC-18 are edited in place.
- **AC-11**: `scenarios.json` carries Lolly's two conversations of 2026-10-16 (her lines and her stage answers) under a group of their own, and the live run in three styles goes through `review-chat-change` before this is called done.
- **AC-12**: Records in the same change: Decisions in force (the two-tries entry edited in place, new entries for the stall limit and stop, the check turn), R17 status and measurements, Conflicts rows, the journal note, and a Superseded line on the journal note that argued for two tries.

## Build plan

`docs/superpowers/plans/2026-10-16-stages-as-conversation.md`, task by task.

## Consequences

**Positive**:
- Completion means the stage's purpose was met, judged from their words. Nothing a bare yes or an I don't know can do moves the walk.
- The person, not a counter, ends a stage or the framework.
- Lolly's skipped-answer finding has a single cause and a single fix.

**Negative / tradeoffs**:
- One more exchange before the offer (AC-10), and more exchanges inside a framework by design. R5 is pressed on; her message asks for exactly this.
- Whether the help at D and E produces her "aha" is the model's work. The content gives it the distinctions; only live runs show it uses them.
- A person who says "I don't know" four times is offered a stop; that is her point 7.5, but it is new behaviour she has not seen.

**Neutral**:
- `stages_known` stores `tries` past 2 now. The ledger view is unchanged.
- `reply_checks.check_too_early` can no longer fire; left as is until the next cleanup.

## Follow-up

- [ ] R18, the somatic cadence, as spec 0008 once this is live (decision 10).
- [ ] Tell Lolly that the check now comes one turn after control, and that E's "no different belief" exit is gone.
- [ ] If muhammad wants B to E judged ahead after all, that is a new spec: the running judgement must be re-made every turn, never seeded once.
