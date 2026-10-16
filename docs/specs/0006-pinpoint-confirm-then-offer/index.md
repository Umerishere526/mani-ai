# 0006. Pinpoint, confirm, then offer: the person's confirmation is the offer gate

**Date**: 2026-10-13
**Status**: In Progress

## Summary

Before any framework is offered, Mani works out three things: the problem, the core issue under it, and what is in the person's control. Then it checks that understanding with them, in its own words. Only a clear yes to that check leads to the offer, in the very next reply. Anything else keeps the conversation going.

Today a message count decides when an offer may come. That count is deleted. In its place, code remembers on the thread when Mani's last check was made. The framework offered is the active one closest to what they confirmed, which means ABCDE while it is the only one. No framework is named in code, so the other five can come back as content alone. Every turn is still one model call.

## Requirements

**User stories**:
- As a person talking to Mani, I want it to tell me what it understood and let me correct it before it suggests anything, so I know it really understood me.
- As a person who doesn't know what is in my control, I want Mani to accept that and not press me, so I still get help.
- As muhammad, I want to add the other five frameworks back by moving their content files, with no code change.

**Acceptance criteria**:
- **AC-1**: A reply can carry an `offer` field only on a `CHECK_OPEN` turn. No other shape has one, and an offer is rendered only when that turn's `check_answer` is `yes`. An `offer` filled with any other answer is dropped and logged.
- **AC-2**: The `check` field exists only in the CHATTING shape, once the problem, its core issue and what is in their control are all stored, on earlier turns (AC-17, AC-18), while no framework is live, and once the cooldowns in AC-5 and AC-6 have passed. The earliest check answers their 4th message (2026-10-16, spec 0007 AC-10: the reply that receives the control answer is an ordinary reply; updated 2026-10-13 after muhammad's live run: at their 2nd, Mani checked having asked about neither the core issue nor control).
- **AC-3**: A reply whose `check` has a non empty `problem` and `core_issue` sets `threads.check_at_message_count` to the count after this turn. Its fields are merged into `threads.understanding` (AC-9). The check's words are the model's text, sent as written after the usual repairs. A `check` missing either value is ignored, and `check unusable` is logged. A usable `check` whose text asks no question is logged as `check without a question`, and the reply still goes out. A `check` on a turn that starts a framework is ignored.
- **AC-4**: `CHECK_OPEN` is the turn right after a check: `check_at_message_count` equals `thread.message_count`, and no framework is live. On it, `check_answer = yes` makes the same reply the offer, rendered from the client's template (`repairs.offer_template`). The turn is one provider call.
- **AC-5**: On `CHECK_OPEN`, any other answer means no offer. That includes no, a null, a yes with an addition, and talking about something else. The reply follows what they said. The check is used either way. A new `check` field appears only once `COOLDOWN_AFTER_DECLINE` messages have passed since `check_at_message_count`. A yes whose offer cannot be rendered is logged with its reason and also uses the check.
- **AC-6**: After an offer, whatever its outcome (accepted, declined or completed), a later offer needs a new check that is confirmed.
  - The `check` field returns once `cooldown_for(outcome)` has passed since that offer row's `at_message_count`, read from `ctx.technique`.
  - The rule that refused to re-offer a framework they just finished is deleted.
  - A typed request for a set they declined still starts it at any time, including on a `CHECK_OPEN` turn.
- **AC-7**: A concern turn (screen or model) merges nothing into the understanding and renders no offer. A check that is open on a concern turn simply expires, because the next turn is no longer right after it.
- **AC-8**: The offered set comes from code, in this order:
  - `heading_toward`, when it is an active framework id;
  - otherwise the only active framework, when exactly one is active;
  - otherwise none: the offer is dropped and logged.

  `repairs.apply` uses this resolved id for both the template and the buttons. An empty `going_through` is filled from the stored `feeling`, and the offer is dropped only if both are empty.
- **AC-9**: `threads.understanding` holds `feeling`, `issue`, `core_issue` and `in_their_control`.
  - On a check turn, the `check` fields are merged first (`problem` as `issue`, then `core_issue`, `in_their_control`), and `understanding_update` after them, so their own words win.
  - Every key follows the existing merge rules (null keeps, one line, `LIMIT`).
  - All four are sent in the `understanding:` line of `[ctx]`.
  - With `AI_DEBUG_MODE` on, a turn returns them and `check_at_message_count`.
- **AC-10**: The following are deleted, and nothing references them:
  - `context.offer_window` with its `not_yet`, `open` and `due` values
  - `FIRST_OFFER_OPENS` and `FIRST_OFFER_DUE`
  - `pause_first_offer_window` (settings, `.env`, `tests/conftest.py`)
  - `offer_due` in `reply_checks.misses`
  - the `clarification_available` line and `context.clarification_used`
  - `greeting.CLARIFICATION_QUESTIONS`
  - the `clarification_already_used` parameter and `repairs._without_clarification`
  - the `finished_framework_id` rule in `repairs._offer_text`

  No code reads history text to find the check.
- **AC-11**: On the reply to the person's 5th message, if the thread has never had a check and this reply makes none, `no check by message 5` is added to `Turn.checks` and logged. This happens on that turn only, and nothing about it reaches `[ctx]`.
- **AC-12**: Changes to the framework content files:
  - `content/frameworks/abcde.md` `central_indication` is the client's selection line: a specific event tied to a troubling belief and the reaction to it, judged on the pinpointed problem and its core issue, never on the opening feeling.
  - Each file in `content/frameworks/paused/` carries its own cheat sheet line in `central_indication`.
  - No framework id appears in `mani/` code or in `mani_base.md`.
- **AC-13**: `scripts/seed.py` refuses to seed an active framework that lacks any of the following, and names what is missing:
  - `stages.offering.offer` for each style, containing a `going_through` slot
  - `keep_chatting` and `explain` for each style
  - `stages.offering.steps`
  - `intro`, and `ask` for each style, on every content stage
- **AC-14**: Prompt and `[ctx]` changes:
  - In `mani_base.md`, `before_the_check` replaces `before_an_offer`. It says to pinpoint the problem, then the core issue, then what is in their control (never pressed), then check in Mani's own words, using only their words.
  - `response_format.md` reasoning has "Check or not" in place of "Offer or not".
  - `[ctx]` sends a `check` line valued `may_check` or `open`, each with its meaning, and nothing otherwise.
- **AC-15**: A live run in all three styles, after muhammad's yes, of the client's sample conversation and of cheat sheet Example 1's ABCDE and Structured Problem Solving lines:
  - each reaches a check;
  - a yes gets the ABCDE offer;
  - a no keeps chatting;
  - no check invents a fact they did not give.
- **AC-17**: `understanding.merge` takes the steps in order, judged on the record as the turn began: `core_issue` only once `issue` was stored on an earlier turn, `in_their_control` only once both were. Each step therefore gets an exchange of its own, and none is filled from the opening message.
- **AC-19**: A stored check is sent as its parts in the client's order, each a sentence the model wrote: the problem, the core issue, what is in their control, what it comes down to, then its question on a line of its own (`repairs.check_text`). The model's free text is not sent. Live, the model opened every check with their control answer despite two prompt fixes; muhammad chose code ordering with model wording (2026-10-13).
- **AC-18**: `[ctx]` names the first missing step (`understanding_next: problem | core_issue | control`) with what to ask for it. A `check` field exists only once all three are stored (spec 0007, AC-10), so a check whose control comes only from the check cannot be filled; the `check before the three steps` log stays as a guard that can no longer fire.
- **AC-16**: These records are edited in place: the Decisions in force for the offer window, the fit rule and the running understanding, and the Conflicts rows in `docs/client/requirements.md` for the window and the fit rule.

## Decision

**Chosen option**: Option 2, the moment of Mani's last check, stored on the thread and marked by a typed reply field whose words are the model's own.

The offer exists only on the turn right after a check, and only with a yes. The message count window is deleted.

**Implementation skills**: `supabase-postgres` (`.claude/skills/supabase-postgres/`), for migration 023.

## Rationale

Reasoning and options: see [rationale.md](rationale.md).

## Feature design

**Data model sketch** (migration 023, on `public.threads`):

| Column | Type | Null | Rule |
|---|---|---|---|
| `check_at_message_count` | `integer` | yes | the `message_count` after the turn whose reply was Mani's latest check; null until the first check |

- `grant update (check_at_message_count) on public.threads to mani_service`, as migration 022 does. The owner reads it through the existing select policy.
- No backfill.
- `threads.understanding` is jsonb, so its two new keys need no migration.
- `Thread` (`mani/models/rows.py`) and the `threads` select (`mani/db/threads.py`) gain the column. `ThreadUpdates` gains `check_at_message_count`, written in its own update, like `understanding`.

**How state is read** (no stored state machine):
- *A check is open* when `check_at_message_count == thread.message_count` and no framework is live.
- *The check was used* on any later turn, whatever happened on the `CHECK_OPEN` turn.
- *Cooldown since the check*: `thread.message_count - check_at_message_count >= COOLDOWN_AFTER_DECLINE`.
- *Cooldown since an offer*: `thread.message_count - ctx.technique.at_message_count >= cooldown_for(ctx.technique.outcome)`, read from `ctx.technique` (the stored row, retired or not), never the turn's live variable.

**Moment and shapes** (`context.moment`, `schema.reply_for`):
- `moment` takes `check_open: bool`. Its order is CONCERN, then BODY, then, when no framework is live: `CHECK_OPEN` if `check_open`, else CHATTING. Then the live framework moments as today. `CHECK_OPEN` cannot coexist with OFFER_OPEN or IN_STAGES, because those need a live framework.
- The `CHECK_OPEN` shape is the core fields, plus `check_answer: Literal["yes", "no"] | None`, plus `offer` with the slots from `repairs.slots_for` (the first active template; active frameworks share one slot shape, which AC-13 enforces). It adds `offer_answer` when `declined_row`. In schema order, `check_answer` comes before `offer`, and both come before `text`.
- CHATTING gets `check` when `context.may_check(ctx)` holds, meaning their 2nd message or later, no framework live, not `check_open`, and both cooldowns passed. It never gets `offer`. With `declined_row` it keeps `offer_answer`.
- `schema.Check` holds `problem: str | None`, `core_issue: str | None` and `in_their_control: str | None` (null when not clear yet), with plain descriptions.
- `UnderstandingUpdate` gains `core_issue` and `in_their_control`, with the same wording rules as `issue`. `understanding.KEYS` gains both, and `understanding.from_check(check)` adapts a `Check` to an `UnderstandingUpdate` (`problem` becomes `issue`).

**`[ctx]`**: `offer_window` and `clarification_available` are deleted. A `check` line is sent only for these values:

| Value | Sent when | Meaning line says |
|---|---|---|
| `may_check` | `may_check(ctx)` | once the problem and its core issue are clear from their words, you may check your understanding, filling `check`; never add what they did not say |
| `open` | `CHECK_OPEN` | your last reply checked your understanding; set `check_answer`; only on a clear yes, offer the set closest to what they confirmed; otherwise follow what they said toward the root cause |

**Value sourcing**:

| Action | Value | Source |
|---|---|---|
| Choose the moment | `CHECK_OPEN` | `threads.check_at_message_count == threads.message_count`, no live `TechniqueState` |
| Show `check` | allowed | `_their_messages(ctx) >= 2`; not `check_open`; `check_at_message_count` and `COOLDOWN_AFTER_DECLINE`; `ctx.technique.at_message_count` and `outcome` through `cooldown_for` |
| Write the check | `check_at_message_count` | `ctx.thread.message_count + 2` (the existing `count_after`) |
| Read the answer | yes or not | the reply's `check_answer`; null counts as not |
| Offer which set | framework id | `reply.heading_toward` if in `config.registry` (active only); else the single id when `len(config.registry.ids) == 1`; else none |
| Fill the offer | `going_through` | `reply.offer.going_through`; else `ctx.thread.understanding["feeling"]` |
| Log late | `no check by message 5` | `_their_messages(ctx) == 5`, `check_at_message_count` null, no usable `check` this turn |
| Merge understanding | four keys | `understanding.merge(stored, from_check(reply.check))`, then `merge(..., reply.understanding_update)`; skipped when guarded |

**Key invariants**:
- An offer is rendered only on a `CHECK_OPEN` turn whose `check_answer` is `yes`, for an active framework.
- Code never reads the person's or Mani's text to find or judge a check.
- No state can leave a thread unable to check again: every check is used on the next turn, and the cooldowns always expire.
- One provider call per chat turn.

**Security model**:
- `check_at_message_count` is written only by `mani_service`, in the turn's transaction. `authenticated` has no grant, so a person can't open their own check through PostgREST.
- It holds no words.
- The understanding keeps its rules: never logged, only in its own thread's `[ctx]`, deleted with the thread.

**Configuration**: `PAUSE_FIRST_OFFER_WINDOW` is removed from `mani/config.py`, `backend/.env` and `tests/conftest.py`. Nothing new is added.

**Critical test scenarios**:
- Happy path, verifies **AC-3** and **AC-4**: a usable check at their message 2 stores the count. A yes at message 3 makes that reply the ABCDE offer with buttons. Two turns, one call each.
- Partial yes, verifies **AC-5**: `check_answer` null at message 3 gives no offer. There's no `check` field at messages 4 to 5, and it returns at the exact cooldown boundary (an off by one test).
- Floor, verifies **AC-2**: the reply to message 1 has no `check` field.
- Re-offer after finishing, verifies **AC-6**: after ABCDE completes and its cooldown passes, a new confirmed check offers ABCDE again.
- Dropped offer, verifies **AC-5** and **AC-8**: a yes with a null `heading_toward` and one active set still offers it. An empty `going_through` uses the stored feeling. With neither, the offer is dropped, the next turn is CHATTING, and a later check is possible.
- Concern, verifies **AC-7**: a concern on a `CHECK_OPEN` turn merges nothing and renders no offer, and the turn after is CHATTING.
- Declined set asked for, verifies **AC-6**: a typed request for the declined set on a `CHECK_OPEN` turn starts it, and its `check` is ignored.
- Seed, verifies **AC-13**: a framework missing `explain` for one style, or an offer template with no `going_through` slot, is refused, with the field named.

## Build plan

Tracer Bullet: the thinnest end to end check first, then the deletions, then the content.

1. Migration 023 (one column, grant), applied locally and confirmed live. `Thread`, the select, `ThreadUpdates` and `threads.apply`. Satisfies **AC-3**, **AC-4**.
2. Schema: `Check`, `check_answer`, `Moment.CHECK_OPEN`, the `reply_for` shapes and field order, the two understanding keys, `understanding.KEYS` and `from_check`. Satisfies **AC-1**, **AC-2**, **AC-9**.
3. `context`: `may_check`, the `check_open` input to `moment`, the `check` line and its meanings. `offer_window`, the first offer constants, `clarification_available` and `clarification_used` deleted. Satisfies **AC-1**, **AC-2**, **AC-5**, **AC-6**, **AC-10**, **AC-14**.
4. Orchestrator and repairs:
   - Write the check, merge in order, and read `check_answer`.
   - Render the offer only on a yes, for the AC-8 resolved id.
   - Ignore a check on a turn that starts a framework.
   - `reply_checks`: drop `offer_due`; add `check unusable`, `check without a question` and `no check by message 5`.
   - Delete from `repairs`: the clarification strip and parameter, and the finished framework rule.
   - Delete `greeting.CLARIFICATION_QUESTIONS` and the pause setting.
   - Debug fields.

   Satisfies **AC-1** and **AC-3** to **AC-11**.
5. Content:
   - `mani_base.md` `before_the_check` and the offers lines
   - `response_format.md` "Check or not"
   - `abcde.md` `central_indication` and `offering.purpose`
   - the paused files' `central_indication`
   - the seed contract check
   - reseed

   Satisfies **AC-12**, **AC-13**, **AC-14**.
6. Tests: unit and integration for the scenarios above. Window and clarification tests rewritten or deleted, never skipped. `scenarios.json` gains the client's sample and the Example 1 lines with check expectations, and `scenario_check.py` reads them. Satisfies **AC-1** to **AC-13**.
7. Records: Decisions in force edited in place, the Conflicts rows, the journal Superseded lines, and the PORT-STATUS turn description. Satisfies **AC-16**.
8. Live run after muhammad's yes. Satisfies **AC-15**.

## Consequences

**Positive**:
- The offer gate is a fact the person gave, not a guess from a count, so the count's tuning stops.
- No stored state can strand a thread: every check is used on the next turn.
- The check is where Mani shows it understood, which answers Lolly's 2026-10-13 message.
- Adding a framework later is a content change, and the seed catches an incomplete one.

**Negative / tradeoffs**:
- One more exchange before an offer, at their 3rd message at the earliest, which presses on R5. The check has to replace a question, and the live run must show it does.
- With only ABCDE active, a confirmed practical problem still gets ABCDE. muhammad accepted this; the client must be told.
- A yes whose offer could not be rendered costs a check, so Mani must check again after the cooldown.
- The check's wording is the model's, so its quality rests on the prompt and is measured only live. A model that never checks only logs.

**Neutral**:
- `scenarios.json` "earliest and latest offer" expectations change meaning, from a counted message to after a check.
- The two clarification lines go. Neither appears in a client document in the repo, and the check covers what they did.
- Someone who types past the style buttons reaches the floor one message later (`_their_messages` assumes the tap), as today.

## Follow-up

- [ ] Tell Lolly about the check flow (it comes from a meeting with no transcript) and that her sample conversation gets ABCDE for now.
- [ ] When a paused framework comes back, rewrite its file to the ABCDE document's format until the seed accepts it.
