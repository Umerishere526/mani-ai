# 0005. Questions follow what they said, from a running understanding kept by code

**Date**: 2026-10-13
**Status**: In Progress

## Summary

Mani's questions should build on what the person just said and keep their feeling and their issue in view. Today the feeling they open with is said once and then lost, and a checklist steers the questions instead. Each reply will now report a small record of their feeling word and their issue. Code stores it on the thread and sends it back on the next turn, so it holds past the 20 message history. One short question rule replaces the checklist and the bans that kept their feeling out of the questions. Every turn is still one model call.

## Requirements

**User stories**:
- As someone talking to Mani, I want each question to follow from what I just told it, so I feel listened to rather than run through a form.
- As someone who said how I feel at the start, I want that feeling to stay in view, in the questions and in the offer, so the framework is about what I actually came with.
- As muhammad, I want to see what Mani understands on every turn in the chat tester, so I can tell at once when the feeling or the issue drops out.

**Acceptance criteria**:
- **AC-1**: Every reply shape, in every moment (`schema.reply_for`), carries `understanding_update` with `feeling` and `issue`, each nullable, declared after `reasoning` and before `text`. Code merges it into `threads.understanding`: null, empty or whitespace only keeps what is stored; a value has its whitespace collapsed to single spaces, is cut to 200 characters, and replaces the stored one. The write lands in the same transaction as the rest of the turn.
- **AC-2**: From the turn after something is stored, the thread's `[ctx]` carries an `understanding:` line (feeling and issue, disarmed) with its `means` line, in that thread only. It is still sent when every message that set it is older than the 20 message window.
- **AC-3**: `feeling` is only a word the person used for how they feel, stored in the form that reads after "feeling" ("frustrated", "anxious"). It stays null until they name one, and a later message naming a different one replaces it.
- **AC-4**: They move to a different issue, or correct the feeling or the issue: the new value replaces the stored one.
- **AC-5**: In a live run of the frustrated chat (the scenario below) and the client scenarios, in all three styles: each question follows from their previous answer; the feeling they named comes back inside at least one question or in the offer; nothing they said is restated to them as a statement (R3).
- **AC-6**: When `understanding.feeling` is set, the ABCDE offer's slot holds it as a short noun phrase ("the thoughts behind your frustration"), never their judgment of someone else. Their worry fills the slot only when they named no feeling.
- **AC-7**: On the start turn, A's `missing` line fills its slot from `understanding.feeling` after this turn's merge. The reply field `feeling` from spec 0004 no longer exists. With no stored feeling, A is the client's `ask` for the style and `slot empty` is logged, as today.
- **AC-8**: `thread_summaries.current_issue` is gone. Migration 022 drops it, the summary prompt and its schema no longer ask for it, Conversation Context has no "Current issue" line, and the exercise pick after a framework is given `understanding.issue`.
- **AC-9**: The prompt carries one positive question rule, in `mani_base.md` `rules`, word for word: "Each question follows from their last answer and keeps the feeling and issue they came with in view. Their feeling word may come back inside a question, never as a statement about them." Removed: `before_an_offer`'s "Build every question from what they actually said."; the "Finding the fit" section and the composer code behind it; `to_find_out` in `abcde.md` and its two composer tests; `reflecting`'s "Never hand their own words or feelings back to them, and never comment on a feeling; they already know it."; `response_format.md`'s "Am I saying back their own words or feelings, or commenting on them, instead of asking? Then leave it out." The two files together have fewer words than before.
- **AC-10**: Every turn is still one model call (`test_a_turn_costs_exactly_one_provider_call`).
- **AC-11**: On a concern turn (the screen's `blocks_framework` or the model's `crisis`), nothing is merged and the stored record is unchanged, as spec 0003 AC-12 holds for every reply field. A crisis turn makes no model call, so there is nothing to merge. The stored text never appears in a log line, a note or a Sentry event.
- **AC-12**: With `AI_DEBUG_MODE` on, a turn returns `understanding` (the record after the merge), and the chat tester shows it under "What Mani knows", above the stage ledger.
- **AC-13**: The Decision in force "Questions before an offer ask for what is still missing" is edited in place; a Decision in force "The running understanding" is added; the stage store decision no longer mentions the yes turn's `feeling`. `scripts/scenarios.json` holds the frustrated chat as a scenario.

## Decision

**Chosen option**: Option 3: a running understanding the model reports and code merges and stores, plus one positive question rule in place of the checklist and the feeling bans.

The reply reports only what this message names or changes. Code merges it into a JSON column on the thread, sends it back in `[ctx]` every turn, and is the only reader for A's slot and the exercise pick. The model still writes every question and fills the offer slot, now reading the stored feeling.

**Implementation skills**: `supabase-postgres` (`.claude/skills/supabase-postgres/`)

## Rationale

Reasoning and options: see [rationale.md](rationale.md).

## Feature design

**Data model sketch**:

| Table | Column | Type | Null | Notes |
|---|---|---|---|---|
| `threads` | `understanding` | `jsonb` | not null, default `'{}'` | `check (jsonb_typeof(understanding) = 'object')`. One per thread. |
| `thread_summaries` | `current_issue` | (dropped) | | No backfill: there is no production data yet (R10 deployment is owed). |

`understanding` holds, both keys optional:

| Key | Type | Rule |
|---|---|---|
| `feeling` | string, at most 200 characters | Their own word for how they feel, in the form that reads after "feeling". |
| `issue` | string, at most 200 characters | What they are dealing with, in their words. |

Migration 022 (`022_thread_understanding.sql`) adds the column, grants `update (understanding)` on `public.threads` to `mani_service` only (the backend's role, as `vague_streak` in migration 002; a grant to `authenticated` would let the person write their own `[ctx]` through PostgREST), and drops `thread_summaries.current_issue`. The grant is asserted in `tests/sql/test_grants.sql`, and both columns are updated in `backend/docs/database-schema-reference.md`.

**Loading**: `rows.Thread` gains `understanding: dict` with `default_factory=dict`. It is selected only in the turn context query (`_TURN_CONTEXT_SQL`), never in `threads.COLUMNS`, so the thread list never carries it. The jsonb codec in `db/pool.py` returns a dict.

**Reply field** (`mani/llm/schema.py`): `UnderstandingUpdate`, as `understanding_update` in `_CORE` so every moment has it, declared in `Reply` after `reasoning` and `style` and before `text` (generation follows declaration order in `Reply`):

| Field | Type | Description sent to the model |
|---|---|---|
| `understanding_update.feeling` | string or null | Their own word for how they feel, only when this message names it or changes it, in the form that reads after "feeling", such as "frustrated". Never one they did not use. Null otherwise. |
| `understanding_update.issue` | string or null | What they are dealing with, in their words, only when this message first makes it clear or moves to another. Null otherwise. |

**Merge** (`mani/chat/understanding.py`, a new module beside `walk.py`, pure functions):
- `merge(stored, update) -> dict`: per key, null, empty or whitespace only keeps the stored value; otherwise whitespace (newlines included) collapses to single spaces, the value is cut to 200 characters with no ellipsis, and it replaces the stored one. Collapsing newlines also closes a `[ctx]` line injection that `context.disarm` does not cover.
- `render(stored) -> str | None`: the `[ctx]` value, passed through `context.disarm`, or None when empty.

**Where the merge runs** (`orchestrator.py`): right after `schema.as_reply`, unless the turn is guarded (`assessment.blocks_framework or model_concern`). The merged record is passed down to `_walked` (A's slot, still gated on `start`, because `walk.reply_text`'s missing branch renders for any missing stage) and to `_offer_exercise`. Paths with no model reply never merge: `_handle_crisis`, `_open_in_style`, and the duplicate retry.

**Write**: `threads.ThreadUpdates.understanding: dict | None`, set only when the merged record differs from the stored one (`{}` is empty); `__bool__` includes `understanding is not None`; `threads.apply` writes it with its own update.

**[ctx] line** (`context.py` `_MEANING`), sent only when the stored record is not empty:

```
understanding: feeling: frustrated; issue: client keeps changing the requirements
  means: what they have told you so far, kept for you. In understanding_update report only what their message names or changes.
```

`_SEED` (the start turn text in `context.py`) drops "and in feeling their own word for how they feel".

**Offer slot**: only the three placeholder texts in `abcde.md` `offering.offer` (directive, supportive, reflective) change, to name the source: "their feeling from understanding as a short noun phrase that reads naturally after ..., such as \"your frustration\"; what is worrying them only when they named no feeling". The client's sentences around the slot do not change. The `keep_chatting` slots and `central_indication` keep their text.

**State transitions**: none. The record lives as long as the thread: no reset when a framework starts, finishes or is declined. It is deleted with the thread row.

**API surface**: no new endpoint.

| Surface | Change | Auth | Errors |
|---|---|---|---|
| `POST /v1/threads/{id}/messages` (`send`) | `Turn.understanding` is always set (as `stage_trace` is); `TurnOut.understanding: dict \| None` carries it only when `AI_DEBUG_MODE` is on, wired in `routers/messages.py`. | bearer, owner via RLS (unchanged) | unchanged |
| `client.choose_exercise` | Parameter `current_issue` becomes `issue`, given `understanding.issue`. | internal | unchanged |

**Value sourcing**:

| Action | Value produced or displayed | Source |
|---|---|---|
| Merge, every unguarded turn | the stored record | `threads.understanding` from `_TURN_CONTEXT_SQL`, plus `reply.understanding_update` |
| Write | the merged record | `ThreadUpdates.understanding`, written by `threads.apply` only when changed |
| `[ctx]` | `understanding:` line | the stored record as loaded at the start of the turn; this turn's merge is what the next turn sees |
| Questions | following their last answer | the model, from the conversation, the `[ctx]` line and the rule in AC-9 |
| Offer | `going_through` slot | the model, from the `[ctx]` feeling and their message, steered by the placeholder text in `abcde.md` |
| Start turn, A missing | the feeling word in the slot | `understanding.feeling` after this turn's merge, through `walk._mid_sentence`; null falls back to `activate.ask[style]` |
| Exercise pick | the issue | `understanding.issue` after this turn's merge |
| Debug turn, chat tester | `understanding` | `Turn.understanding`, through `TurnOut` under `AI_DEBUG_MODE` |
| Scenario check | feeling and offer slot side by side | `Turn.understanding` and the offer text, printed per conversation (and in `Exchange`) for a person to read; no automatic match, since a word stem match would be a phrase list |

**The frustrated chat scenario** (`scripts/scenarios.json`), a new group `names_a_feeling_first`:
- `about`: "They open with a feeling and then describe what is behind it. The feeling stays in view in the questions and fills the offer."
- `expect`: `{"offer_from": 3, "offer_by": 5}`
- one conversation, `frustrated_client_changes`, `source`: "muhammad's Directive tester run, thread 4ec47e15, 2026-10-13, the person's lines word for word", `lines`:
  1. "i am frustrated"
  2. "my work"
  3. "my client keeps changing the requirements and when i do make the changes he say that he does not like that and want to go to previous iternation"
  4. "the complete back and forth, we are just moving in circles"
  5. "that they need to decide on what they want before tell me to go back again and again"

**Key invariants**:
- Null or blank in an update never erases a stored value.
- No stored string is longer than 200 characters or holds a newline.
- The record is written only by code, after the reply, only through `threads.apply` in the turn's transaction, and never on a guarded turn.
- No gate reads `understanding`: the offer window, the walk's step and the safety screen stay keyed on database state as before (spec 0003).
- Code reads no meaning from the stored words: it stores, renders and places them, never matches them.

**Security model**: the column is on `threads`, so the owner only reaches it through the existing RLS policies. Only `mani_service` may update it, so the person cannot write it directly. It is special category health data: never logged, never in a note, never in Sentry (`send_default_pii=False` already holds), sent only in its own thread's `[ctx]`, disarmed, and never stored from a concern turn. The debug field is off unless `AI_DEBUG_MODE` is on.

**Configuration required**: none.

**Critical test scenarios**:
- Happy path: a scripted chat stores the feeling on turn 1 and the issue on turn 2; turn 3's `[ctx]` carries both; verifies **AC-1**, **AC-2**.
- Memory: store a feeling, then 25 messages with null updates; `[ctx]` still carries it; verifies **AC-2**.
- Merge rules (unit): null and blank keep, a value replaces, a newline collapses, 300 characters cut to 200; verifies **AC-1**, **AC-4**.
- Start turn: a feeling stored two turns before the yes, A renders `missing` with it; no feeling, A renders `ask` and logs `slot empty`; verifies **AC-7**.
- Concern turn: a guarded reply with an update leaves the record unchanged; verifies **AC-11**.
- Logs from a scripted run contain none of the stored strings; verifies **AC-11**.
- Grants: `authenticated` cannot update `understanding`, `mani_service` can (`test_grants.sql`); verifies **AC-1**.
- One call: `test_a_turn_costs_exactly_one_provider_call` still passes; verifies **AC-10**.
- Composer: the Framework Index has no "Finding the fit"; Conversation Context has no "Current issue"; verifies **AC-8**, **AC-9**.
- Live (muhammad's yes): the frustrated chat, 3 runs x 3 styles, then every client scenario once per style; verifies **AC-3**, **AC-5**, **AC-6**.

## Build plan

Tracer Bullet: the record goes through every layer first (column, reply, merge, `[ctx]`), then its readers, then the prompt, then the proof.

1. Migration `022_thread_understanding.sql`: the column, its check, the `mani_service` grant, and the drop of `thread_summaries.current_issue`; the grant assertion in `test_grants.sql`; `database-schema-reference.md`. Add `understanding` to `rows.Thread` and to `_TURN_CONTEXT_SQL` only. Remove `current_issue` from `ThreadSummary`, `summaries.py`, the `Extraction` schema, `summarize.existing_context` and the "# The current issue" section of `summarization.md`. Satisfies **AC-1**, **AC-8**.
2. `mani/chat/understanding.py` with `merge` and `render`, and its unit tests. Satisfies **AC-1**, **AC-4**.
3. Schema: `UnderstandingUpdate` and `understanding_update` in `_CORE`, declared after `reasoning` and `style`, with the descriptions above. Satisfies **AC-1**, **AC-3**.
4. Orchestrator: the merge after `as_reply` on unguarded turns, passed to `_walked` and `_offer_exercise`; `ThreadUpdates.understanding`, its `__bool__` term and its write in `threads.apply`; no new provider call. Satisfies **AC-1**, **AC-10**, **AC-11**.
5. `[ctx]`: the `understanding` line and its `means` in `context.build`. Integration tests for the happy path, the 25 message memory and the concern turn. Satisfies **AC-2**, **AC-11**.
6. Readers: A's `missing` slot reads the merged `understanding.feeling`; remove `feeling` from `Reply`, from `_STAGES`, from `_SEED` and from `walk.reply_text`'s caller; the exercise pick takes `understanding.issue`; Conversation Context drops "Current issue". Rewrite the tests that read the removed fields: `test_schema.py`, `test_composer.py`, `test_turn.py`, `test_walk.py`, `test_client.py`. Satisfies **AC-7**, **AC-8**.
7. Prompt: the rule into `rules`; the four cuts; the "Finding the fit" block in `composer.py`, `to_find_out` in `abcde.md` and the two tests that read it; the three offer slot placeholders in `abcde.md`, with `test_repairs.py` and `test_abcde_content.py` updated to the new placeholder text. Reseed. Satisfies **AC-6**, **AC-9**.
8. Debug: `Turn.understanding`, `TurnOut.understanding` under `AI_DEBUG_MODE` in `routers/messages.py`, and the chat tester shows it under "What Mani knows". Satisfies **AC-12**.
9. Scenario: the frustrated chat group in `scripts/scenarios.json`; `scenario_check.py` prints the stored feeling beside the offer slot, and `Exchange` carries it. Satisfies **AC-13**, prepares **AC-5**, **AC-6**.
10. Docs: Decisions in force edited and added, R4 and R6 notes in `docs/client/requirements.md`, the scope row, a journal note. Satisfies **AC-13**.
11. Live run, only with muhammad's yes: the frustrated chat 3 runs x 3 styles; if it passes, every client scenario once per style. Record output tokens and latency per turn against the R2 numbers. Satisfies **AC-3**, **AC-5**, **AC-6**.

## Consequences

**Positive**:
- The feeling and the issue have one home that every turn rereads, so they survive the 20 message window, and code can place the feeling in A without asking the model again.
- The checklist that steered questions toward ABCDE's needs is gone, and with it a second copy of the fit rule beside `central_indication`.
- One record for "their issue" in place of two (`current_issue` lagged 20 messages behind).

**Negative / tradeoffs**:
- Each reply writes a few more output tokens (about 15 to 30), at effort `low`, which adds a little latency against R2. Measured in step 11.
- Whether questions really follow their answers is still the model's judgment, checked only by a live run; no unit test can hold AC-5.
- A model that reports a wrong feeling or issue stores it, and it then steers later turns until they correct it; nothing clears a value except a newer one. `feeling` is limited to their own word to keep that rare.
- A feeling named only in a concern turn is not stored; the next turn has to hear it again.
- Spec 0004's `feeling` field and its tests are removed and rewritten.

**Neutral**:
- Migration 022: check no other branch holds a 022 before merging (journal: duplicate migration versions after a merge). Reset the local database and run both seeds after it.
- The memory fold keeps working from the prose summary; it never read `current_issue`.
- What each answer added is not stored: before an offer it is all in the history window, inside a framework `stages_known` holds it, and past the window the summary prose carries it.

## Follow-up

- [ ] Spec 0004 is edited with this spec: its `feeling` field and A's `missing` source now point here.
- [ ] If the live run shows the prompt cuts alone fixed the frustrated chat, record that in the journal; the record still stays for R6 past the window and for A's slot.
- [ ] The Decision in force line "why stage questions are not made about feeling: reason unknown" was kept on purpose (muhammad, 2026-10-13); it still waits for muhammad's reason.
