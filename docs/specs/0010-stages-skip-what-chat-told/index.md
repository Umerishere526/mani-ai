# 0010. A stage ledger: frameworks skip what the chat already told

**Date**: 2026-10-08, amended 2026-10-09 (three times)
**Status**: In Progress
**Decision record**: [rationale.md](rationale.md) (context, premise notes, options considered, rationale)

## Summary

A framework's stages become what Mani needs to learn, not steps to walk one by one. In the same one model call, the model reports every stage of the running framework as missing, partial or known (statuses only, never the person's words), the code stores that ledger in one new column, and the stage Mani asks is the first one not yet known. Any stage counts as known once the conversation makes it clear, before or after the offer, in any order, and whoever asked, so a stage told out of order is never asked again. A stage still not known after 3 answers is passed and left behind, so it is asked at most 4 times, and the ending cap now starts at `closing`, so no framework can hold the thread from any stage. Each chat call's row in `admin.llm_calls` keeps the statuses the model reported and the stage the code stored, and the chat tester shows both, so a run can be read after it ends.

## Requirements

**User stories**:
- As a person who already told Mani what happened and what it meant, I want the questions to start where my story left off, so I am not asked again what I just said.
- As a person who told only part of a stage, I want to be asked only for the part still missing.
- As a person stuck on one question, I want Mani to move on rather than keep me there.
- As muhammad, I want the stage order kept by stored statuses and a number in `tuning`, not by matching words, so it can change with a reseed.
- As muhammad, I want to see what the model reported of each stage on every turn and which stage the code then stored, so I can tell a misjudged stage from a code fault after the run ends.

**Acceptance criteria**:

- **AC-1**: Migration `021_technique_state_stage_ledger.sql` adds `stage_ledger jsonb not null default '{}'::jsonb` to `public.thread_technique_state`, with `check (jsonb_typeof(stage_ledger) = 'object')`. The column is named `stage_ledger`, never `known`, because hosted still carries a `known` column from the reverted migration 012. No grant changes: `mani_service` already holds table wide insert and update, `authenticated` keeps select only, and `scripts/test_db.sh` still passes. `rows.TechniqueState` gains `stage_ledger: dict[str, LedgerEntry]` (default empty) and the `threads.apply` upsert writes it. The retire update leaves it as stored.
- **AC-2**: `mani/chat/techniques.py` gains `StageStatus` (`missing`, `partial`, `known`, `passed`), `Registry.ledger_stages(framework_id)` (the framework's phases after `offering` and before its last own phase, in order: for ABCDE `activating_event, belief, consequences, dispute, effective_new_belief`), and `Registry.stage_from_ledger(framework_id, ledger)`, which returns the first ledger stage whose status is neither `known` nor `passed`, or the last own phase (`closing`) when there is none. A stage absent from the stored ledger is `missing`.
- **AC-3**: The reply's `state` gains `stages: list[{stage: str, status: str}] | None`, typed loosely like `style` so an off list value costs the entry, never the turn. `guards.check` takes the running framework's ledger stages (from the registry, for `current_framework_id`, or for the tapped framework on a tap accept) and:
  - drops `stages` whole, with a note, whenever it ignores `state` (technique not in the registry, or not the running framework); otherwise it keeps them on every turn, from `closing` on too, where the orchestrator ignores them (AC-6) and AC-17 still records them;
  - normalises each `status` as it does `style` (stripped, lowercased), keeps an entry only when `stage` is a ledger stage and `status` is `missing`, `partial` or `known` (the model never writes `passed`), and drops any other entry with a note giving the reason only; for a stage listed twice the last entry wins;
  - no longer clamps a step before the last own phase, and no longer sets `framework_id` to None because of the step: before `closing`, `framework_id` is kept whenever `state.technique` is valid.

  `Checked` gains `stages: dict[str, StageStatus] | None`. The orchestrator, not the guard, sets `checked.phase` before `closing` (AC-4), with `dataclasses.replace`, before the ending and button block (`orchestrator.py` around lines 481 to 494), so a turn that completes the ledger (recorded phase `closing`) drops its buttons like any ending turn.
- **AC-4**: One explicit running turn branch in the orchestrator, ahead of the tap accept branch (around line 572), writes the row on every turn where the framework is accepted (stored, or `accepted_this_turn`) and the turn is not a safety concern turn. Its `framework_id` is the stored row's (or, when `accepted_this_turn`, the accepted one); `outcome` accepted, `at_message_count` and `ending_from` carried from the stored row as the decided branch does today, `library_offered_since` false. Before `closing` it writes:
  - the starting ledger: `{}` when `accepted_this_turn` and the framework differs from the stored row's or the stored row was declined or offered; else the stored ledger, with keys that are not ledger stages dropped;
  - updated by each kept reported entry, in either direction, except that a stored `passed` stays `passed`;
  - then, unless `accepted_this_turn` or the stored phase is `offering`, the stored phase's `turns` increased by one, and that stage set to `passed` when it is not `known` and its `turns` reach `stage_turn_cap`;
  - `phase` set to `stage_from_ledger` of the result, whatever `state.step` reported.

  "Accepting" means `accepted_this_turn` (a tap, a free text `state.accepted`, or a declined offer asked for again); a stored `offering` with an accepted outcome (left by a concern turn, AC-8) is also handled as accepting. The row is written even when the reply carries no `state` or no `stages` (hold and count), so a model that drops the field still reaches the cap; this replaces the tap accept branch's `phase="offering"` write. Notes (ids only) record: a stage moved back, a stage passed by the cap, `stages` absent on a running turn before `closing`, and a reported `step` that is a ledger stage, differs from the stage the ledger gives, and is not on the accepting turn.
- **AC-5**: On the accepting turn, the reply judges every ledger stage against everything said before the offer, and the stored stage after it is the first one not known. On a turn where an offer is open and not answered (including the "asked about the offer" path), the row keeps `phase` `offering` and `stage_ledger` `{}`, and reported `stages` are ignored. The offer writes `{}`, and a decline writes `{}`.
- **AC-6**: From `closing` on (the stored phase is the last own phase or an ending phase), the ledger is frozen: reported `stages` are ignored, `state.step` moves through `closing`, `somatic_checkin` and `somatic_practice` with the existing clamp, and a reported step before `closing` holds the stored phase. The running turn branch writes the row on these turns too, so a null `state` holds the phase.
- **AC-7**: `ending_from` is set to `count_after` on the first recorded phase from `closing` on, not only `somatic_checkin`, and is carried as today; the running turn branch also sets it when the stored phase is already `ending_open` and `ending_from` is null. The two sites change from `in ENDING_PHASES` to `Registry.ending_open`: the pre call cap (`orchestrator.py` around line 237, on the stored phase) and the `ending_from` start (around line 555, on the recorded phase). A framework stuck on `closing` then retires after `ending_turn_cap` too.
- **AC-8**: On a safety concern turn, nothing the reply reports about stages is applied and no turn is counted, so the framework resumes exactly where it was. A tap on Try it during a concern turn still records the acceptance as today (outcome accepted, phase `offering`, ledger `{}`), because the person pressed it; the next turn that is not a concern turn is handled as the accepting turn (AC-4).
- **AC-9**: `[ctx]` carries `stage_ledger: <id> <status>, ...` over every ledger stage in order (absent ids as `missing`) while an offer is waiting (`offer_waiting`) and while a framework runs before `closing`, and `stage: <stored phase>`. On a tap accept `stage` is the first ledger stage (the stored ledger is `{}`). `next_stage` leaves `[ctx]`, `CTX_KEYS` and `response_format.md`, and `test_prompts_name_what_exists.REMOVED` lists it; `stage_ledger` joins `CTX_KEYS` and `response_format.md`'s `ctx` section. There is no `stage_last_try` key (muhammad, 2026-10-09): the cap is set one lower instead (AC-12). `framework_stages`, `framework_starting` and `current_phase` stay. From `closing` on, `stage_ledger` is not sent.
- **AC-10**: Every stage on each framework's `Stages:` line is joined by ` > `; no line carries a ` | `. In all six `content/frameworks/*.md` files the one ` | ` becomes ` > ` (abcde before `dispute`, thought_reframe before `facts`, structured_problem_solving before `options`, act_choice_point before `matters`, behavioral_activation before `choose`, dbt_stop before `pause`), so no line grows. `scripts/seed.py` loses `STAGES_DIVIDER`, the comment above its check, and both refusals (not exactly one ` | `, no stage on one side); it splits the line on ` > ` alone and still matches the ids against `phases` and the 420 character cap. A stray ` | ` is still refused, by the `phases` match, because the two stages it joins parse as one. `test_seed_frameworks.py` loses its four divider cases and the `"Stages: activating_event | belief"` case (with no divider it no longer fails to parse), and its fixture lines use ` > `.
- **AC-11**: `mani_base.md` `in_a_framework` and `response_format.md` (`ctx.stage_ledger`, `ctx.offer_waiting`, `ctx.framework_starting`, `ctx.stage_lines`, `fields.state`, `layers.Framework Index`) carry the wording in *Feature design*. No prompt says "never skip a stage", and none says a stage counts only in the person's own words or names a `|`. Neither file gains a line, and no line grows except `fields.state`, whose stages sentence muhammad reworded (14 characters longer). The prompt contract tests pass.
- **AC-12**: `content/prompts/tuning.md` `windows` gains `stage_turn_cap: 3` with a comment saying it is the turns any one stage may take across every visit before it is passed, and that the stage is asked once more than that, because the reply on the turn that passes it was written while `[ctx]` still named it (so asked `stage_turn_cap` + 1 times, 4 at the cap of 3), and `WindowTuning` gains `stage_turn_cap: _count(2, 20)` with no default. `WindowTuning` is strict (`extra="forbid"`), so the code, the tuning key and the reseed ship in one change, as `ending_turn_cap` did. The client may change it with a reseed.
- **AC-13**: Real model evals, run only with muhammad's yes:
  - after the accepting turn of the ABCDE example (event, meaning and effect told before the offer), the stored stage is `dispute`, and the reply asks what supports the belief or what questions it;
  - inside a running ABCDE (started on `activating_event`, as the stall scenario starts), with the event told and its meaning vague, the stored stage is `belief` and the reply asks only for what it came to mean;
  - out of order: with A, B and both sides of D told before the offer (one side in answer to Mani's own question, as in the "left out of meetings" chat) and C not told, the stored stage after the accepting turn is `consequences`, and once C is answered it is `effective_new_belief`, with no D question in between;
  - before `closing`, in no transcript does Mani ask a stage the stored ledger holds as `known`, unless the person corrected or took back that answer (from `closing` on the ledger is frozen, AC-6);
  - a free text yes ("yeah let's do it") lands on the same stage as a tap;
  - negative: with A, B and C told and only one side of D (what makes the belief seem true, nothing that questions it), the stored stage stays `dispute` and the reply asks only for the missing side; a guess of Mani's that the person did not confirm does not make a stage known.

  `scripts/eval_replies.py` gains a per turn `expect_stage` (the stored phase after that turn), reported as a finding when it differs.
- **AC-14**: A seeded framework (the seed appends the ending ids to every one; a registry without them is out of scope) holds the thread for at most ledger stages × (`stage_turn_cap` + 1) of the person's messages after the accepting one and before `closing` (each stage passes at `stage_turn_cap` counted turns, or one more when it was known at the cap and then moved back), then at most `ending_turn_cap` after it, from any stage, whatever the model reports. Safety concern turns are not counted (AC-8), since the framework is paused on them.
- **AC-15**: The whole `pytest` passes with pristine output and the integration count checked, after a reseed. `backend/PORT-STATUS.md` gets a "Decisions in force" line for the ledger (any stage skips once the conversation makes it clear, in any order) and edits the ending cap line in place to say it starts at `closing`; `backend/docs/database-schema-reference.md` documents `stage_ledger` and that it differs from hosted's leftover `known`, and the two `admin.llm_calls` columns of AC-16; the client list gets a line saying stages already clear are skipped.
- **AC-16**: Migration `026_llm_calls_reported_stages.sql` adds two nullable columns to `admin.llm_calls`: `reported_stages jsonb` with the constraint `llm_calls_reported_stages_is_object check (jsonb_typeof(reported_stages) = 'object')`, named as 021 names its check, and `stage text`. Both are null on every call that is not a chat turn's and on every chat turn with nothing to record (AC-17). No index (rows are read by `thread_id`, already indexed) and no grant changes: the row is written on the admin connection that already inserts it and sets `message_id`, and `authenticated` still holds no select on `admin.llm_calls` (`test_grants.sql`).
- **AC-17**: The chat call's row records, in the same update that sets `message_id`:
  - `reported_stages`: the stages `guards.check` kept from the reply, as `{"<stage id>": "<status>"}`, whether or not the turn applied them (an offer turn or a concern turn ignores them, AC-5 and AC-8); null when the guard kept none (`checked.stages` is None or empty). Never an entry the guard dropped, so no unchecked model value is stored;
  - `stage`: the `phase` of the technique row this turn wrote (`updates.technique.phase`, including `offering` on an offer); null when the turn wrote no technique row. So three kinds of turn record stages with `stage` null, by design: a concern turn (the guard kept them, nothing was applied), a turn that retires the framework (the ending or the ending cap; no row is written though a phase was computed), and a decline (the row is written with `phase` None).

  `orchestrator.Turn` gains `reported_stages: dict[str, str] | None = None` and `stage: str | None = None` (neither sent to a client), set only at the main chat `Turn` (`orchestrator.py` around line 632, where `checked` and `updates` are in scope); the other `Turn` sites make no chat call and leave them None. `routers/messages.py` passes them to `link_call`, which, like `llm_calls.attach_message`, takes them as keyword arguments defaulting to None, so existing callers and the `test_link_call.py` fakes keep working. `attach_message` sets `message_id`, `reported_stages` and `stage` in one `update`. When every link retry fails, the turn's stages are lost with the link, as the link is today. No server log line records them (the existing notes still log a missing ledger and a step that differs).
- **AC-18**: The chat tester, only when `CHAT_TESTER_DEV_MODE` is set and "Show developer details" is on:
  - the caption under the title adds the stored ledger after `framework: <id> · stage: <phase>`, one `<stage id> <status>` per ledger stage, with `(<turns>)` after the status when `turns` is above 0 and absent ids shown as `missing`, in the order of that framework's `admin.frameworks.phases` (jsonb keeps no key order, so `framework_debug_state` also reads `phases` and returns `stage_ledger`). When the row has no phase, no ledger line is shown, as the caption shows no stage today;
  - each `chat` purpose call in the "recent calls" list adds `reported: <stage id> <status>, …  → <stage>` when either column is set, `→ –` when `stage` is null; other purposes show no stage line. Ids are ordered by the current framework's `phases` where they appear in it, and any other ids follow, sorted (`llm_calls` holds no `framework_id`, so an older call may name a framework no longer running);
  - the tester's bare `asyncpg` connection has no jsonb codec, so `stage_ledger` and `reported_stages` are decoded with `json.loads` when they arrive as text, as `client.py` already does for `memory`;
  - the newest call may show no stages until the next rerun, because `link_call` writes them after the reply is delivered. Accepted.

  Ids only, never message text. Checked by eye in a run; the chat tester has no test suite for its screens.

**Not in this spec**:
- Getting a framework on the shortlist from plain phrasing (feature 13, which reverses spec 0007's no closest fit).
- Crisis, the safety screen and the model's `crisis` field (feature 10).
- Storing or showing any of the person's words per stage. The ledger and the two `llm_calls` columns hold ids, statuses and counts only.
- Showing the ledger in the API or either frontend. The chat tester reads the database directly as a developer tool (AC-18).
- How a question is shaped (feature 23, its own spec). This spec changes only these prompt sentences: line 2 of `in_a_framework` loses its "The stages after the | …" sentence, `fields.state` defines `known`, and `layers.Framework Index` loses its `|` sentence. Feature 23 owns "in your style and their words, about their situation, never bare" (line 1 of `in_a_framework`), "say what you now understand, name what is still missing in fresh words" (line 2), and "built from what they have told you, in their words, … never bare" (`ctx.stage_lines`). None of those sentences is touched by both, so either spec can be built first.

## Decision

**Chosen option**: a stage ledger reported by the model in the turn's one call, stored as statuses in `thread_technique_state.stage_ledger`, with the code choosing the stage, passing a stage after `stage_turn_cap` turns, and the ending cap starting at `closing`.

The model judges what the conversation has made clear; the code keeps order, counts and caps. Before `closing` the ledger decides the stage; from `closing` on, `state.step` and the existing clamp run the ending unchanged. Every stage is judged the same way: there is no class of stage that needs the person's own words. What the model reported and the stage stored are kept on the call's `admin.llm_calls` row.

**Implementation skills**: `supabase-postgres` (`.claude/skills/supabase-postgres/`) for migrations 021 and 026.

## Rationale

Reasoning and options: see [rationale.md](rationale.md).

## Feature design

**Data model** (migrations 021 and 026; the rest is unchanged):

| Table | Column | Type | Rule |
|---|---|---|---|
| `public.thread_technique_state` (PK `thread_id`, 1:1 with `threads`) | `stage_ledger` | `jsonb not null default '{}'` | `check (jsonb_typeof(stage_ledger) = 'object')` |
| | its shape | `{"<stage id>": {"status": "missing"\|"partial"\|"known"\|"passed", "turns": <int ≥ 0>}}` | keys are ledger stages of the row's framework; checked in code before writing. Written as a plain dict through the pool's jsonb codec (`mani/db/pool.py`), a new dict each turn since `Row` is frozen; keys that are not ledger stages (after a reseed changes `phases`) are ignored on read and dropped on write |
| | `ending_from` (existing) | `integer`, nullable | now set from `closing` on |
| `admin.llm_calls` (PK `id`, N:1 with `threads` by `thread_id`) | `reported_stages` | `jsonb`, nullable | `check (jsonb_typeof(reported_stages) = 'object')`; shape `{"<stage id>": "missing"\|"partial"\|"known"}`, only entries the guard kept |
| | `stage` | `text`, nullable | the phase the turn stored; a phase id from the framework's `phases`, set by code |

**State transitions**:

- Per stage: `missing` ↔ `partial` ↔ `known`, in any direction as the model reports. Any of these → `passed` when the stage is not `known` and its `turns` reach `stage_turn_cap`. `passed` is final.
- Per framework: `offering` → accepted → the first stage not known or passed (recomputed every turn) → `closing` when all are known or passed → `somatic_checkin` → `somatic_practice` → retired (by `ending`, the ending cap, or a crisis turn). A move back may return the stage to an earlier one before `closing`; from `closing` on, it cannot.

**Interface changes** (no HTTP change):

| Where | Before | After |
|---|---|---|
| `Reply.state` | `technique`, `step`, `accepted` | adds `stages: [{stage, status}]`; `step` counts only from `closing` on |
| `[ctx]` while running or an offer waits | `stage`, `next_stage`, `framework_stages` | `stage_ledger`, `stage`, `framework_stages` |
| Stored stage | the model's step, at most one forward per turn | `stage_from_ledger` before `closing`; the clamped step after |
| Stuck stage | no limit | passed after `stage_turn_cap` (3) turns, so asked at most 4 times |
| Ending cap | from `somatic_checkin` | from `closing` |
| Stages line | ` > ` and one ` \| ` before the work stages | ` > ` only |
| `admin.llm_calls` chat row | cost, latency, `message_id` | adds `reported_stages`, `stage` |
| `orchestrator.Turn`, `link_call`, `attach_message` | carry and set `message_id` | also `reported_stages`, `stage` |
| Chat tester (dev mode) | `framework · stage` | adds the stored ledger, and each call's reported stages and stage |

**Prompt wording**: task 1 shipped the `[ctx]` lines (`stage_ledger`, `offer_waiting`, `framework_starting`, `stage_lines`) and the `fields.state` stages sentence as reviewed by muhammad; they stay as they are in `content/prompts/` except for these three edits, all cuts or a reword of the same length (chosen by muhammad, 2026-10-09):

1. `mani_base.md` `in_a_framework`, line 2: delete its second sentence, and keep the rest word for word. The line becomes:

   ```yaml
     - A stage they already answered, before or after the offer, is not asked again unless they corrected or took back what they said. Take the part of their answer the stage needs and offer nothing else meanwhile. Staying is not repeating, so say what you now understand, name what is still missing in fresh words, and after two tries come at it from a different angle. A stage marked passed is left without a word. Never ask them to confirm what they just said, or explain the method.
   ```

   The sentence deleted: "The stages after the | are the ones you work through together, and count only when they worked them out in their own words in this conversation, never from your words or a guess."

2. `response_format.md` `fields.state`: in the stages sentence, "known when they have said what it asks" becomes "known when the conversation makes clear what it asks". The sentence becomes: "stages is every stage on stage_ledger with its status after their latest message, known when the conversation makes clear what it asks, partial when only part, missing otherwise."

3. `response_format.md` `layers.Framework Index`: delete "The stages after the | on its Stages line are the ones you work through together."

Line 1 of `in_a_framework`, and "say what you now understand …" in line 2, are left for feature 23 (see *Not in this spec*).

**Value sourcing**:

| Action | Value | Source |
|---|---|---|
| Running turn | which stages are on the ledger | `Registry.ledger_stages`: `admin.frameworks.phases` between `offering` and the phase before `techniques.ENDING_PHASES[0]` |
| Running turn | each stage's status this turn | the reply's `state.stages`, kept by `guards.check`; else the stored `stage_ledger` |
| Running turn | which stage's turn to count | the stored `thread_technique_state.phase` (the stage the person was answering) |
| Running turn | the cap | `tuning.windows.stage_turn_cap` |
| Running turn | the stored stage | `Registry.stage_from_ledger` of the updated ledger |
| Running turn | whether this is the accepting turn | `accepted_this_turn` in the orchestrator (a tap, `state.accepted` on a waiting offer, or a declined offer asked for again), or a stored `offering` with an accepted outcome |
| Running turn | which framework the row is for | the stored row's `framework_id`; on `accepted_this_turn`, the accepted one |
| Running turn | the starting ledger | `{}` when accepting a framework other than the stored row's, or one stored as offered or declined; else the stored `stage_ledger` |
| Running turn | whether the ledger is frozen | `Registry.ending_open(framework_id, stored phase)` |
| Running turn | whether it is a concern turn | `assessment.blocks_framework or model_concern`, as today |
| `[ctx]` | `stage_ledger`, `stage` | the stored row, in `Registry.ledger_stages` order, absent ids shown as `missing` |
| Running turn | whether a stage is known | the model's judgement of the whole conversation, any stage alike, reported in `state.stages`; no stage needs the person's own words |
| `llm_calls.reported_stages` | its value | `checked.stages` from `guards.check`, as `{id: status.value}`; null when None or empty |
| `llm_calls.stage` | its value | `updates.technique.phase`, the row the turn passes to `threads.apply`; null when `updates.technique` is None |
| `llm_calls` update | which row | `Turn.llm_call_id`, as `link_call` uses today |
| Chat tester caption | ledger and its order | `thread_technique_state.stage_ledger`, ordered by `admin.frameworks.phases` for the row's `framework_id`, absent ids as `missing` |
| Chat tester recent calls | each call's stages | `admin.llm_calls.reported_stages` and `stage`, ordered by the same `phases` |
| `ending_from` | its value | `count_after` on the first recorded phase where `ending_open` is true; carried after |
| Ending cap | turns since `closing` | `(message_count - ending_from) // 2` against `ending_turn_cap` |
| Offer, decline | the ledger | `{}` |

**Key invariants**:
- The ledger never holds a word the person or the model wrote: only stage ids from `phases`, the four statuses and integer counts. The same holds for `llm_calls.reported_stages` and `stage`, which hold only what the guard kept and what the code stored.
- No stage is judged by a different rule from another: no Stages line carries a divider, and no prompt rule makes a stage count only in the person's own words. The "in their words" inside four Stages descriptions is cut by spec 0017 (E8), so it no longer reads as a rule about the person's own words.
- The stored stage before `closing` is always `stage_from_ledger` of the stored ledger.
- `passed` is written only by the code and never changes after.
- Each ledger stage's `turns` only grows while the framework runs and reaches at most `stage_turn_cap` + 1, so the counted turns before `closing` are bounded by ledger stages × (`stage_turn_cap` + 1).
- From `closing` on, no reported value changes the ledger.
- A concern turn changes nothing in the row.

**Security model**: no change in who may read or write what. `stage_ledger` is written only by `mani_service` inside the turn's transaction, under RLS like the rest of the row; `authenticated` can select its own row and holds no insert or update (`test_grants.sql`). The ledger carries no health content, only ids and statuses. `llm_calls.reported_stages` and `stage` are written on the admin connection that already writes the row (`pool.as_admin`, whose named uses include writing the call log), in the `admin` schema the Data API does not expose; `authenticated` and `anon` hold no privilege on `admin.llm_calls`. Log notes carry ids and reasons, never message text or a model supplied value that failed validation.

**Configuration required**: no new env var. `stage_turn_cap` is a `tuning` value in seeded content.

**Critical test scenarios** (scripted model unless marked):
- `Registry.ledger_stages` and `stage_from_ledger` for ABCDE: empty ledger gives `activating_event`; A, B, C known gives `dispute`; B partial gives `belief`; all known or passed gives `closing`; a test registry with no ending ids uses its last phase. Verifies **AC-2**.
- Guards: entries for `closing`, `offering`, an unknown id, status `passed`, status `Done` are dropped with a note; valid entries are kept; a reported step is ignored before `closing`. Verifies **AC-3**.
- Integration, accepting turn: stored `offering`, tapped Try it, scripted `stages` with A, B, C known, step `activating_event` → stored phase `dispute`, ledger turns all 0, note about the step. Verifies **AC-4**, **AC-5**.
- Integration, partial and count: stored `belief` partial, reply keeps it partial → phase `belief`, `turns` 1; on the `stage_turn_cap`th such turn → `belief` passed, phase `consequences`, note. Verifies **AC-4**, **AC-14**.
- Integration, move back: stored `dispute` with `belief` known, reply reports `belief` partial → phase `belief`, note. A stored `passed` reported as `missing` stays `passed`. Verifies **AC-4**.
- Integration, no ledger: running on `consequences`, reply `state` null → row written, phase `consequences`, `turns` 1, note. Verifies **AC-4**.
- Integration, concern: running on `belief`, concern message → row unchanged, `turns` unchanged. Verifies **AC-8**.
- Integration, frozen: stored `closing`, reply reports `belief` missing and step `belief` → phase `closing`, ledger unchanged. Verifies **AC-6**.
- Integration, ending cap from closing: first recorded `closing` sets `ending_from`; a thread 24 messages past it on `closing` retires before the call, 22 does not. Verifies **AC-7**.
- Offer and decline write `{}`; a ledger on the offer turn, or on a turn that asks about the offer, is not stored. Verifies **AC-5**.
- Integration, free text yes: offer waiting, scripted `state.accepted` true with A, B, C known → stored phase `dispute`; the `[ctx]` sent carried `stage_ledger` and `offer_waiting`. A declined offer asked for again starts from `{}`. Verifies **AC-4**, **AC-5**, **AC-9**.
- Integration, wrong technique: running ABCDE, reply `state.technique` `dbt_stop` with stages → `stages` dropped, held and counted, note. Verifies **AC-3**, **AC-4**.
- Integration, concern tap: Try it tapped on a concern turn → accepted, `offering`, `{}`; the next turn is handled as accepting. Verifies **AC-8**.
- Integration, ledger completes: stored `effective_new_belief`, reply reports it known with an offer button → phase `closing`, `ending_from` set, buttons dropped. Verifies **AC-3**, **AC-7**.
- `[ctx]` on a running ABCDE before `closing` carries `stage_ledger` in order and no `next_stage`; on `closing` no `stage_ledger`; contract tests pass. Verifies **AC-9**, **AC-11**.
- Seed: the six Stages lines, joined by ` > ` only, seed; a line with a ` | ` left in is refused by the `phases` match. Verifies **AC-10**.
- Out of order, every framework: for each of the six seeded frameworks, parsed from `content/frameworks/` into a registry, a ledger with every stage known except the second gives the second stage, and with that one known too gives `closing`. Verifies **AC-2**, **AC-10**.
- Integration, out of order: running ABCDE on `consequences`, scripted `stages` with A, B, D known and C known → stored phase `effective_new_belief`, `dispute` never stored as the phase. Verifies **AC-4**.
- Integration, call row: a running turn whose scripted reply reports A known and B partial, and an off list entry, gives `Turn.reported_stages` `{"activating_event": "known", "belief": "partial"}` and `Turn.stage` `belief`; after `link_call`, the `admin.llm_calls` row holds both and its `message_id`. A turn with no running framework and no offer leaves both null. Verifies **AC-16**, **AC-17**.
- `attach_message` sets `message_id`, `reported_stages` and `stage` in one update; `test_link_call.py`'s fakes take the two new arguments and its retry tests still pass. Verifies **AC-17**.
- Real model (muhammad's yes): the four ABCDE scenarios (the example, a vague meaning inside a running ABCDE, out of order, one side of D only) and a stall scenario with `expect_stage`. Verifies **AC-13**, **AC-14**.

## Build plan

Tracer Bullet: the first task takes the ABCDE example through every layer (content, seed, schema, guard, orchestrator, database, `[ctx]`), so the accepting turn landing on `dispute` is proven before the counting and the backstops are added. Task 2 is its own thin slice through content, seed, prompts, schema, orchestrator, database and the chat tester, so the next run can be read turn by turn before the counting lands. The code is the same for every framework, so the content changes go into all six files at once; the other frameworks get their own eval scenarios after ABCDE is proven. One commit per task is fine; the whole `pytest` stays green after each.

1. Tracer, the ABCDE example end to end: migration 021, `LedgerEntry` and `stage_ledger` on `rows.TechniqueState` and the upsert, `StageStatus`, `Registry.ledger_stages` and `stage_from_ledger`, `state.stages` on the reply schema, the guard (AC-3), the running turn branch in the orchestrator applying the ledger on every accepting path (tap, free text, a declined offer asked for again) and after, without counting yet, offer and decline writing `{}`, `[ctx]` `stage_ledger` (also while an offer waits) with `next_stage` removed and the `offer_waiting` wording, the ` | ` in all six Stages lines and the seed rule, the prompt drafts (stop for muhammad's review of the wording), reseed. Unit and integration tests for each. Satisfies **AC-1**, **AC-2**, **AC-3**, **AC-5**, **AC-9**. Built 2026-10-08; its ` | `, seed rule and own words wording are taken out again by task 2, which now carries **AC-10** and **AC-11**.
2. Any stage skips once clear, and the ledger readable: the three prompt edits in *Feature design*, the ` | ` back to ` > ` in all six Stages lines, `STAGES_DIVIDER` and its two refusals out of `scripts/seed.py`, the four divider cases out of `test_seed_frameworks.py`; migration 026, `Turn.reported_stages` and `Turn.stage`, `link_call` and `attach_message` carrying them, `routers/messages.py` passing them; the chat tester's caption and recent calls (`framework_debug_state` and `recent_call_costs` read the new values and `phases`). Show muhammad the prompt diff before the reseed, then reseed, and run the chat tester once to check the caption by eye. Unit and integration tests for each, including the six framework out of order test, and `test_link_call.py` with the new keyword arguments. Satisfies **AC-10**, **AC-11**, **AC-16**, **AC-17**, **AC-18**.
3. Counting and the backstops: `stage_turn_cap` in `tuning` (code, key and reseed together), the turn count and `passed`, writing the row when no ledger came back, the concern turn changing nothing (and a concern tap accept handled as accepting next turn), the ledger frozen from `closing`, `ending_from` set at `closing` and both cap sites reading `ending_open`. Integration tests for each. Satisfies **AC-4**, **AC-6**, **AC-7**, **AC-8**, **AC-12**, **AC-14**. Built 2026-10-09, with the cap at 3 after the second amendment.
4. Evals: `expect_stage` in `scripts/eval_replies.py`, scenarios for the ABCDE example, a partial stage, out of order (A, B and D told), one side of D only, and a stall in `eval_conversations.yaml`, then one per other framework with its intake told before the offer. Ask muhammad before any real run; with a yes, run the ABCDE ones first and read them with `--verbose`, and optionally a three run baseline before and after (about 0.06 dollars each) to see the output token change. Satisfies **AC-13**, **AC-14**.
5. Close out: `PORT-STATUS.md` (a decision line for the ledger, the ending cap line edited in place, the client list), `docs/database-schema-reference.md` (`stage_ledger` and the two `llm_calls` columns), a journal note, reseed, and the whole `pytest` with the integration count checked. Satisfies **AC-15**.

## Consequences

**Positive**:
- The three places that pulled the stage back (the clamp, "never skip a stage", the one skip on accepting) are replaced by one rule, so the better Mani understands before the offer, the shorter the framework.
- A partial stage is visible to the model, so it asks only the missing part.
- Every framework is bounded from any stage, which closes the gap the journal found before `closing`.
- No words are stored: the ledger is not health content.
- One rule for every stage, with nothing in the Stages lines, the seed or the prompts to keep in step with it.
- A run can be read turn by turn after it ends: what the model reported and what Mani was then told to ask sit on each call's row, so a skipped or repeated stage can be traced to the model or the code.

**Negative / tradeoffs**:
- The model may move a stage back, so a model slip can still ask a stage again; only a correction should do it, and only notes and evals show when it does not. muhammad chose this over making known final.
- Whether a stage is clear is the model's judgement alone, for every stage. A model that reads a guess, or one side of a two sided stage, as clear skips a question the person never worked through: on ABCDE, a `dispute` marked known from one side would go straight to `effective_new_belief`. `partial`, the evals and the `llm_calls` columns are the only checks, and the columns only show it after the fact.
- Two more columns on `admin.llm_calls`, and they ride on `link_call`: a turn whose link fails after every retry loses its stages too. A resent message caught before the call records none; one caught only when its message pair is written (`pair.was_duplicate`) still links its call row and records its stages, under the same last write wins race noted below.
- Every running turn costs about 30 more output tokens (the list of stages) and about 15 more `[ctx]` tokens; the cached prompt grows by about 100 words.
- The reply on the turn that passes a stage was written before the count, so it asks that stage once more (the 4th ask with the cap at 3), and the answer to it cannot mark the stage `known`: it stays `passed`. The stage asked next is the same either way, since both are skipped. That answer also counts as the next stage's first turn, because it arrives once the next stage is stored, so in a stall that runs on, a stage after a passed one is asked at most 3 times (muhammad, 2026-10-09, accepted over a `stage_last_try` line in `[ctx]`).
- Every counted turn is charged to the stored stage, including a turn where Mani asked something else (a question about the method, a reply with no `state`), so a stage can pass after fewer real asks than the cap allows.
- A passed stage leaves a hole: the framework goes on without that answer, and the stages after it may have less to build on. Because `passed` is final, a correction to a passed stage cannot reopen it, and Mani may hold an answer the person later took back. The same holds for any correction from `closing` on, where the ledger is frozen.
- Two different messages racing on one thread already end in last write wins for `phase`; the ledger and its counts inherit the same race. Nothing new, but a lost count is possible.

**Neutral**:
- A framework running at deploy starts with `{}`; its first reply reports the whole ledger from the conversation, and at worst one stage is asked once more. No compatibility code (muhammad, 2026-10-08).
- The stages a framework's Starts when needs are always known on the accepting turn, since it is not offered before. So a stage partial before the offer can only be one after them (for ABCDE, C, D or E); a partial A or B is seen only inside a running framework.
- Hosted must take migration 021 alongside the open reconciliation of 011 to 017; `stage_ledger` does not collide with the leftover `known`. Migration 026 goes with it.

## Follow-up

- [ ] Tell the client: Mani no longer walks every stage. Any stage the conversation has already made clear is skipped, in any order and whoever asked, and a stage asked 4 times is left behind. E is still reached only once B, C and D are clear, so ABCDE's "does not skip directly from the event to a balanced belief" holds as long as the model judges D fairly.
- [ ] `stage_turn_cap` may change on the client's requirement; it is a reseed.
- [ ] Watch the notes for moves back that were not corrections. If they appear, revisit making `known` final.
- [ ] Watch `llm_calls.reported_stages` for a two sided stage (ABCDE's `dispute`, ACT's `situation`, problem solving's `facts`) marked known when only one side was told. If it happens, the cut in `fields.state` is the place to look first.
