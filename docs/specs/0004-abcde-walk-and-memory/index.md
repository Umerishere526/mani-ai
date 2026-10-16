# 0004. The ABCDE walk names each letter and remembers what they said

**Date**: 2026-10-13
**Status**: In Progress

> Changed 2026-10-14: a stage reached as missing, B to E (and A with no feeling word), is asked with Mani's own question, the client's `ask` as written with what it refers to in their words; the client's `ask` is the logged fallback ("missing asks nothing"), and a stage reached unjudged still gets the client's line (thread 425f6a55; Decision in force on Mani's voice, PORT-STATUS). AC-6 and the render tables below are edited to match.

> Changed 2026-10-14: the stage the walk reaches is judged in its own field, `next_stage` (known, possible, partial with a `gap`, or missing), on every turn that can start or move the walk, from the whole conversation about the issue they confirmed, before or after the check; a move with no judgement is logged as "reach unjudged" (thread 4b93d612; Decision in force "Inside a framework…", PORT-STATUS).

> Changed 2026-10-13: a stage already answered is confirmed in Mani's own words after the client's letter line; A's client confirm line and `confirm_phrases` are only the fallback (Decision in force "Inside a framework…", PORT-STATUS).

## Summary

Once someone says yes to ABCDE, Mani walks them through it one stage per reply. Each stage opens with its letter and name ("B is for Belief."). A stage they already talked about is said back in their words and confirmed once, and only a missing one is asked. What they said for each stage is now stored in the database by code (a small JSON record on the thread), so Mani still has it after it leaves the 20 message history, and every turn is still one model call.

## Requirements

**User stories**:
- As the client, I want each ABCDE step introduced by its letter and name as it is reached, so that the person understands what A, B, C, D and E stand for (R12).
- As a person using Mani, I want what I already explained to be remembered once the framework begins, so that I am never asked to repeat it (R6).
- As muhammad, I want what is known per stage held by code, not rebuilt by the model every turn, so that the memory costs no second call and no higher effort (R2).

**Acceptance criteria**:
- **AC-1**: The first reply on each content stage (`activate`, `belief`, `consequence`, `dispute`, `effective`) opens with that stage's `intro` line from `abcde.md`, word for word ("A is for Activating Event."), placed by code. Nothing comes before it. A later reply on the same stage has no intro line. A letter line the model writes itself is stripped.
- **AC-2**: The walk moves at most one stage per turn, and code decides it.
  - The reply's `stage_answer` for the stage in force: `agreed`, `answered`, `corrected` or `let_go` moves to the next phase in `framework.phases`. `not_yet`, null, or an answer that fails the validity rules stays.
  - The second `not_yet` in a row on one stage moves on as `let_go` (the code backstop).
  - No stage is ever skipped. Leaving `effective` enters the body route.
- **AC-3**: The framework starts when the row is `accepted` with phase `offering` (from a typed yes, a Try it tap, Try it after Tell me more, or a yes to a declined offer). That turn's `next_stage` judges the first stage, which the walk reaches, from the whole conversation (changed 2026-10-13: every stage was seeded here, and the seed went stale; changed 2026-10-14: from `stage_updates` to `next_stage`). Code clears any earlier entry for this framework, stores it, and only then renders the first stage. Each later stage is judged in `next_stage` on the turn the walk reaches it. On a turn where the offer is not accepted, `stage_updates` and `next_stage` are dropped.
- **AC-4**: Reaching a stage whose stored status is `known`, or `possible` (A only):
  - For `activate`, the reply is the intro line, then the client's `activate.confirm[style]` line with the stored `said` in its slot, word for word.
  - For `belief` to `effective` (`known` only), the reply is the intro line, then the model's one sentence naming their stored words, then one phrase from `confirm_phrases`.
- **AC-5**: Reaching a stage whose stored status is `partial`, the reply is the intro line, then the model's question for only the missing part.
- **AC-6**: Reaching a stage judged missing:
  - For `belief` to `effective`, the reply is the intro line, then Mani's own question: the stage's client `ask[style]` as written, with what it refers to in their words. When the model's text asks nothing, the client's `ask[style]`, logged `missing asks nothing`.
  - For `activate`, the reply is the intro line, then `activate.missing[style]` with their feeling word in its slot when they named one, otherwise Mani's own question, falling back to `activate.ask[style]`.
  - A stage reached with no judgement (`next_stage` null) gets the client's line, as before 2026-10-14. (The feeling word now comes from `threads.understanding.feeling`, [spec 0005](../0005-questions-follow-what-they-said/index.md).)
- **AC-7**: The confirm phrase comes from `confirm_phrases` ("Is that right?", "Do we have this right?", "Did I get that right?", "Does that sound right?"). It is `confirm_phrases[(h(thread_id) + stage_index) % 4]`, where `h` is a stable hash and `stage_index` is the stage's position in `framework.phases`. So the same thread always gets the same phrase, and two neighbouring stages never get the same one. A has no pool phrase; its client line carries its own question.
- **AC-8**: After a confirm:
  - A plain no (`not_yet`) keeps the stage. The reply is the model's text alone, which says it misunderstood and asks what would be more accurate.
  - A no that carries new words (`corrected`) replaces the stored words, and the walk moves on.
  - New words given while on a stage replace that stage's stored words.
  - A correction to an earlier stage replaces that stage's words, and the walk stays where it is.
- **AC-9**: What they said per stage is stored in `thread_technique_state.stages_known` and merged by code under the invariants below. Each turn of a running framework, `[ctx]` carries the stored words and status of every content stage. A stage said more than 20 messages ago is still confirmed when reached, never asked again: the model sees the whole thread within its budget (Decision in force "The transcript is the memory within a thread", 2026-10-13).
- **AC-10**: The store is kept when a run retires and is deleted with the thread. On a guarded turn (the safety screen or a model reported crisis), nothing is merged, stepped or rendered, and nothing is written to the store or the phase.
- **AC-11**: Every turn is still one chat call at effort `low` (`test_a_turn_costs_exactly_one_provider_call` stays green).
- **AC-12**: Logs name stage ids, statuses, `stage_answer` values, ignored updates, and each named fallback, never the person's words.
- **AC-13**: These go:
  - `reply_checks.with_ledger_step` and `ledger_stage`, the per turn `stages_known` ledger and `state` in the stage moments, and the `TechniqueState` and `StageKnown` reply models when nothing else uses them.
  - The skip walk (`context._WALK_THE_STAGES`, `stage_note`, `later_stage` lines).
  - The rules "skip it without a word" and "never say a stage's letter or name" (`mani_base.md` `in_a_framework`).
  - The ledger and skip lines in `response_format.md`.
  - The test that no letter or name reaches `[ctx]`.
  - Anything else these leave unused.
  
  The debug `ledger_view` and the chat tester's "What Mani knows" read the store.
- **AC-14** (added 2026-10-15, both client framework documents, section 6): when they say they want to stop, just talk, or that it is not helping, the reply's `stage_answer` is `stop`. The walk ends where it is, the row is recorded `declined` with no phase, the store is kept, no body check-in and no exercise follow, and the model's text goes. Asking for the set again later starts it afresh. The same walk runs Thought Reframe, whose Try it opens with its `offering.begin` line in a paragraph of its own before Step 1's intro.

## Decision

**Chosen option**: Option 2: a stage store owned by code, with a one stage walk that code steps.

The reply reports only what changed this turn and how they answered the stage in force. Code merges that into a JSON column on the thread's technique row, moves the step at most one stage, and renders the letter line, the client's lines and the confirm phrase. The model writes only the sentence that names their words, the question for a partial stage, or the follow up after a no, and code falls back to fixed text when that does not fit.

**Implementation skills**: `supabase-postgres` (`.claude/skills/supabase-postgres/`)

## Rationale

Reasoning and options: see [rationale.md](rationale.md).

## Feature design

**Scope of the walk**: the store is keyed by framework and works for any framework. The walk described here (one stage per reply, letter lines, render table) runs for stages that have an `intro`, which today is ABCDE only. ABCDE is the only active framework (Decision in force "Only ABCDE is offered").

**Data model sketch** (confirmed 2026-10-13, plus `tries` from the cross check):

| Table | Change |
|---|---|
| `public.thread_technique_state` (one row per thread, PK `thread_id`) | add `stages_known jsonb not null default '{}'::jsonb` |

```
{
  "<framework_id>": {
    "<stage_id>": { "said": "<their short words>", "status": "known | possible | partial | done", "tries": 0 }
  }
}
```

- `said` holds their short words, never Mani's, and at most 200 characters (longer is cut at a word boundary). For `activate` it is a phrase that fits after "You mentioned" ("being left out of meetings at work"), because it fills the client's slot.
- `known` means their words answer the stage, so confirm it once. `possible` is for `activate` only: the event is likely, but they never said it started this, so confirm it once. `partial` means half of it is there, so ask only the gap. `done` means it was agreed, answered, corrected or let go in the walk. A stage that is absent is missing, so ask it.
- The status order, lowest first: `partial`, `possible`, `known`, `done`.
- `tries` counts `not_yet` answers in a row on the stage in force, and resets when the walk moves.
- The existing table grant (`007_backend_writes_prompt_state.sql`: insert and update to `mani_service`) covers the new column. The RLS select policy and the delete cascade (`005`) are unchanged. Adding a column with a constant default rewrites no rows.

**Reply shape** (`schema.reply_for`): `stage_updates`, `stage_answer` and `feeling` replace `stages_known` and `state` wherever `_STAGES` is used today: IN_STAGES, OFFER_OPEN, CHATTING on a declined row, and BODY on the closing stage. They are declared in that order, before `text`.

| Field | Type | Meaning |
|---|---|---|
| `stage_updates` | list of `{stage, said, status, corrected}` or null | Only the stages whose words were learned or changed this turn. `status` is `known` or `partial`, or `possible` for `activate`. `corrected` is true when they said earlier stored words are wrong. |
| `next_stage` | `{status, said, gap}` or null | The stage the walk reaches if it moves this turn (A on a start): `known`, `possible` (A only), `partial` with `gap` the id of its missing part's `if_unclear` line, or `missing`. Applied only when the walk moves; null on a move is logged as "reach unjudged". Not in BODY on the closing stage, which the body route follows. Added 2026-10-14. |
| `stage_answer` | `agreed`, `answered`, `corrected`, `let_go`, `not_yet` or null | How their message answers the stage in force. `agreed`: yes to a confirm. `answered`: gave what the stage needs, with an update for it. `corrected`: a no with new words, with an update for it. `let_go`: move on without words (asked twice already, or the question made them uneasy). `not_yet`: a plain no, unclear, or "I don't know" still being helped. Null on the start turn. |
| `feeling` | string or null | Their own word for how they feel. Read only on the start turn, for `activate.missing`. Removed by [spec 0005](../0005-questions-follow-what-they-said/index.md), which keeps the feeling in `threads.understanding`. |
| `text` | string | What `[ctx]` asks for in each branch (below). |

**Validity of `stage_answer`** (structural, no phrase lists): `agreed` counts only when the stage in force was reached as a confirm (its stored status was `known` or `possible`). `answered` and `corrected` count only with an update for the stage in force. Anything else is treated as `not_yet` and logged as `stage answer invalid: <value>`.

**Content added to `abcde.md`**:
- An `intro` on each content stage, holding the client's line: "A is for Activating Event.", "B is for Belief.", "C is for Consequences.", "D is for Dispute.", "E is for Effective New Belief."
- `activate.confirm[style]` and `activate.missing[style]`. These move out of `activate.if_unclear` (the "possible event" and "named how they feel" entries) with their slots unchanged. The same confirm line serves `known` and `possible`, since muhammad chose to confirm a known event too.
- `confirm_phrases` at framework level, with the four phrases in AC-7.
- The body text at the end of the file is reworded to say a stage already answered is confirmed once.

**`[ctx]` in a running framework** (`context.build`):
- Keep: `active_framework`, `framework_stages`, the stage in force with its lines and `ask`, and `_TWO_TRIES`.
- Add: every content stage's stored `said` and status (`said` passed through `context.disarm`), and a start flag on the start turn.
- Add a two branch `text` line that code computes from the stored status before this turn's merge. For example: "If you answer agreed, answered, corrected or let_go, the next stage is belief, which is known: write one sentence naming their words, no question. If not_yet, write the follow up for this stage." When `tries` is 1, the not_yet branch also moves on, so both branches name the next stage.
- Remove: `stage_note`, `next_stage` beyond what the branch line needs, the `later_stage` lines, and the skip walk.

On a turn where a yes is possible (OFFER_OPEN, or CHATTING on a declined row), `[ctx]` also carries the content stage ids with their `listen_for`, marked "if they say yes", so the start turn can seed.

**Turn sequence** (one call, then code, in this order, after `repairs.apply`):
1. Guarded turn: stop. No merge, step, render or write (AC-10).
2. Start turn (the row is `accepted` with phase `offering`, whether accepted this turn or left there by an earlier turn): clear this framework's entry, merge the updates, set the step to `activate`.
3. Otherwise merge `stage_updates` (invariants below) and decide the step: a valid move answer, or a second `not_yet`, moves one phase; anything else stays and adds one to `tries`. The stage left becomes `done`.
4. Render (tables below), then strip any `^[A-E] is for` the model wrote, and apply the fallbacks.
5. Write the phase through the existing technique write. Write `stages_known` with its own `update public.thread_technique_state set stages_known = $1`, only when the merge changed it, and never in the shared upsert, so a new offer row cannot wipe it.

**Render table**, for a stage just reached (the start turn or a move):

| Stored status of the stage reached | Reply text | Fallback when the model's text does not fit |
|---|---|---|
| `known` or `possible`, `activate` | `intro` + `activate.confirm[style]` with `said` | `activate.ask[style]` when the slot cannot render |
| `known`, other | `intro` + model `text` + confirm phrase | sentences ending in "?" are dropped; if none is left, "You mentioned {said}." |
| `partial` | `intro` + model `text` | the stage's `ask[style]` when the text has no "?" |
| missing, `activate` | `intro` + `activate.missing[style]` with `feeling` | when `feeling` is null, the model's question, then `activate.ask[style]` |
| missing, other | `intro` + the model's question about their situation | the stage's `ask[style]` when the text has no "?" (`missing asks nothing`) |
| unjudged | `intro` + the client's line as above | none |

When the step stays, the reply is the model's `text` with no intro. Leaving `effective` runs the body route as today (below). Each fallback is logged by name (`naming asks`, `gap asks nothing`, `missing asks nothing`, `slot empty`).

**The closing stage and the body route**: after the move into `effective`, the next turn's moment is BODY (on the closing), which carries the same stage fields plus `body`. A `body` value that fits the transition table of spec 0003 wins, and `stage_answer` is then ignored and logged. Otherwise a move answer sets the phase to `somatic_checkin`, and the client's check in question is placed as `with_the_check_in` does today. `not_yet` stays on `effective` with the model's text.

**State transitions** (the `phase` column): `offering` → `activate` (the start turn) → `belief` → `consequence` → `dispute` → `effective` → `somatic_checkin` → `somatic_practice` → retired (`phase` null). Each arrow takes one turn. After a guarded turn the walk resumes on the same stage, with the model's text and no intro.

**API surface**: no new endpoint. `POST` turn responses keep their shape.
- `Turn.ledger` (debug only, `AI_DEBUG_MODE`) is built from the store after the merge, and the phase after the step. Its rows keep their fields (`stage`, `title`, `status`, `known`, `action`, `asking`). Status is the stored one, `missing` for a stage at or before the step with no entry, and `not_reached` after it. `asking` is the stage after the step.
- `Turn` gains `stage_trace` (stage ids and statuses only, no words), so `scenario_check` can see what was stored.
- The chat tester's `LEDGER_ICONS` and caption change to the new statuses.

**Value sourcing**:

| Action | Value produced or displayed | Source |
|---|---|---|
| Letter line | "B is for Belief." | `abcde.md` stage `intro` |
| Whether to show the letter line | first reply on the stage | the step moved this turn, or it is the start turn (code) |
| Start turn | yes or no | the row: `outcome = accepted` and `phase = offering` |
| The step | the stage asked | `phase` + valid `stage_answer` + `tries` (code) |
| A known or possible | the event in their words | `stages_known.<fw>.activate.said` |
| A known or possible | the client's line | `activate.confirm[style]` |
| A missing | their feeling word | `threads.understanding.feeling` after the start turn's merge ([spec 0005](../0005-questions-follow-what-they-said/index.md)) |
| A missing, no feeling word | the question | the model's `text`, falling back to `activate.ask[style]` |
| B to E known | the sentence naming their words | the model's `text`, guided by the branch line, with the "You mentioned {said}." fallback |
| B to E known | the confirm phrase | `confirm_phrases`, by the AC-7 formula |
| B to E missing | the question about their situation | the model's `text`, falling back to stage `ask[style]` |
| Partial | the gap question | the model's `text`, falling back to `ask[style]` |
| After a no | the follow up | the model's `text` |
| What the model writes | which branch | the `[ctx]` branch line, computed from the stored status before the merge |
| Style | Directive, Supportive or Reflective | `threads.conversation_style` (`resolve_style`) |
| Stored words in `[ctx]` | every stage's `said` and status | `stages_known.<fw>` |
| Reach | what was said for the stage reached | `next_stage` on the turn the walk reaches it, from the whole thread about the issue they confirmed, before or after the check |

**Key invariants**:
- Stage in force: an update replaces `said` (the latest words win), and its status never drops below what is stored.
- Other stages and the start turn: an update with a higher status replaces `said` and `status`. An equal or lower one is ignored and logged, unless `corrected` is true, in which case it replaces `said` and keeps the higher status.
- `done` and `tries` are set only by code.
- Updates for a stage id that is not one of the running framework's content stages, `possible` on any stage but `activate`, or an empty `said` are ignored and logged.
- The step never moves more than one phase per turn and never moves backwards.
- A new start of a framework clears that framework's entry, so an old run's `done` stages are never shown again.
- The store is keyed by framework id, so another framework in the same thread never reads ABCDE's words.
- The intro line, the client lines, the confirm phrase and the fallbacks come only from content or code, never from the model.

**Security model**: The store holds a person's own words about their mental state.
- It sits on a table only the backend writes (`mani_service`, migration 007).
- The owner can read it through the existing RLS select policy, as they can read their messages.
- It is deleted with the thread and the account (migration 005).
- It is never logged.
- It is sent to the provider only in that thread's own `[ctx]`, disarmed like any user derived text.

**Configuration required**: none.

**Critical test scenarios** (scripted model built from the real reply schema):
- Nothing known: yes, then A to E in five replies, each opening with its letter line and Mani's own question about their situation, then the body check in. Verifies **AC-1**, **AC-2**, **AC-6**.
- Seeded: the event and the belief said before the offer, then yes. A is the client's confirm line with the event. "yes" leads to B with their belief and the formula's confirm phrase. "yes" leads to C's ask. Run it for a typed yes, a Try it tap and a yes to a declined offer. Verifies **AC-3**, **AC-4**, **AC-7**.
- A row left `accepted` at `offering` by a crisis turn: the next turn is the start turn. Verifies **AC-3**.
- Plain no on B: no letter line, stays on B, `tries` is 1. Then their new words with `answered` lead to C, and B is `done` with those words. Verifies **AC-8**.
- Two `not_yet` on B lead to C as `let_go`. Verifies **AC-2**.
- `agreed` on a stage reached as an ask is treated as `not_yet` and logged. Verifies **AC-2**, **AC-12**.
- A correction to A while on D updates A's words, and the step stays D. Verifies **AC-8**, **AC-9**.
- Memory past the window: the belief is stored at the start turn, then 25 messages pass with no updates. Reaching B still renders the confirm. Verifies **AC-9**.
- Merge: a lower status update for another stage is ignored and logged without words. Verifies **AC-9**, **AC-12**.
- Fallbacks: a question where a naming sentence was expected, a partial reply with no question, and a model written "C is for" are each replaced and logged. Verifies **AC-1**, **AC-4**, **AC-5**.
- A new offer row written after a retire leaves `stages_known` intact. Verifies **AC-10**.
- A guarded turn while on C leaves the store and the phase unchanged. Verifies **AC-10**.
- E answered at the closing, in BODY, moves to the check in; a `body` value at the closing wins over `stage_answer`. Verifies **AC-2**.
- One call per turn. Verifies **AC-11**.
- The confirm phrase is stable per thread and differs between neighbouring stages. Verifies **AC-7**.

## Build plan

Tracer Bullet: a thin walk through every layer first, then memory, then corrections and cleanup.

1. Migration `020_thread_stages_known.sql` adds the column. `TechniqueState` (rows.py) gains `stages_known`, which is loaded in `db/threads.py`, with its own update statement (not the shared upsert). Satisfies **AC-9**, **AC-10**.
2. Schema: `stage_updates`, `stage_answer` and `feeling` replace `stages_known` and `state` in `_STAGES`, with field descriptions to match. Satisfies **AC-2**, **AC-3**.
3. Content: add the `intro` lines, `activate.confirm`, `activate.missing` and `confirm_phrases` to `abcde.md`, reword its body, and reseed. Satisfies **AC-1**, **AC-4**, **AC-6**, **AC-7**.
4. The thin thread:
   - the start turn from the row;
   - the code owned step (one phase, validity rules, the `tries` backstop) in the orchestrator, after `repairs.apply` and skipped when guarded, with the phase written from it;
   - the render for missing stages (intro plus Mani's question, the client's ask as the fallback);
   - BODY at the closing.
   
   An integration test walks A to E. Satisfies **AC-1**, **AC-2**, **AC-6**, **AC-10**, **AC-11**.
5. The merge as a pure function with unit tests, seeding on the start turn (including the "if they say yes" stage lines on OFFER_OPEN and declined CHATTING), and the stored words and branch line in `[ctx]`. Satisfies **AC-3**, **AC-9**, **AC-12**.
6. The known, possible and partial render, A's client confirm line, the confirm phrase formula, and the fallbacks. Satisfies **AC-4**, **AC-5**, **AC-7**.
7. Corrections at the current and an earlier stage, and the plain no. Satisfies **AC-8**.
8. Cleanup:
   - Remove everything AC-13 lists. `repairs.apply`'s stage transition checks, `Registry.clamp` and `validate_transition` and `Framework.may_skip` go if nothing else calls them (confirm each).
   - Rebuild `ledger_view` on the store, add `Turn.stage_trace`, and update the chat tester's ledger icons.
   - Rewrite the tests this breaks: `test_schema`, `test_composer` (field order), `test_abcde_content` (no letter test), `test_chat_context` (stage_note, later_stage, `_SELF_EXPLAINED`), `test_repairs` (state transitions), `test_techniques` (clamp), `test_reply_checks` (ledger), `test_queries` (`TechniqueState` row), and every `test_turn` reply built with `state` or `stages_known`.
   
   Satisfies **AC-13**.
9. `scripts/scenario_check.py`: flag a stage reply that does not open with its intro, and a stage asked whose stored status was `known` or `possible` (read from `stage_trace`). Run `repeats()` on the sent text. Satisfies **AC-1**, **AC-4**.
10. Docs, in the same change:
    - Rewrite three Decisions in force in place in `backend/PORT-STATUS.md`: "The chat never names a stage" (inside "Only ABCDE is offered"), "Inside a framework, a stage their words already answer is skipped", and "The stage ledger".
    - Add a Superseded line to `stages-are-skipped-not-confirmed-2026-10-09.md`.
    - Update the R6 and R12 rows and the R12 conflict row in `docs/client/requirements.md`.
    - Mark the stale in stage rows of spec 0003.
    
    Satisfies **AC-13**.

## Consequences

**Positive**:
- What they said survives the history window and costs no second call. The model stops rebuilding the ledger every turn, so output tokens drop on stage turns.
- The letter line, A's lines, the confirm phrases and the fallbacks are exact, because code sends them.
- The step and the question can no longer disagree, which removes the bug where the stored step named a stage never asked.

**Negative / tradeoffs**:
- A person who explained everything before the offer spends one turn confirming each known stage, up to five confirms. This departs from the client's Situation 1 (a known event is named and the walk goes on) and pushes against R5. It is recorded as a conflict, and the client is to be told.
- One stage per reply is slower than the skipping walk it replaces.
- What they just said gets no acknowledgement when the walk moves on: the reply is the letter line and the next question (muhammad, 2026-10-13, following the client's examples and R3).
- A wrong `agreed` or `answered` that passes the validity rules still moves on for good. Only reading transcripts catches it.
- On turns where code sends the client's text (A with their feeling word, or a stage left unjudged), the model's `text` is written and thrown away. That is a small output cost.
- Seeding five stages in one low effort call can over report (five confirms) or under report (repeats, breaking R6). Only a live seeded run shows which.
- The store is new sensitive data on the thread.

**Neutral**:
- `stages_known` is keyed by framework, so a paused framework can use it when it returns. It gets letter lines only if its stages get an `intro`.
- Turns in one thread are already serialized by `pg_advisory_xact_lock` (`orchestrator.py:318`), so reading, merging and writing the store inside the turn is safe.

## Migration plan

**Strategy**: no migration needed beyond adding the column. Existing rows get `{}`. A run in progress at deploy time continues from its `phase` with an empty store, so a stage they already said is asked once more for that run only.
**Rollback**: revert the commit. The column can stay, since nothing else reads it.

## Follow-up

- [ ] Tell the client: a known stage is confirmed once with a short phrase ("Is that right?"), one stage per reply, which departs from the document's Situation 1.
- [ ] A live seeded run of the four client scenarios in all three styles before shipping (muhammad's yes; it spends the client's credit). It checks how seeding over or under reports.
