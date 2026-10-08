# 0010. A stage ledger: frameworks skip what the chat already told

**Date**: 2026-10-08
**Status**: In Progress
**Decision record**: [rationale.md](rationale.md) (context, premise notes, options considered, rationale)

## Summary

A framework's stages become what Mani needs to learn, not steps to walk one by one. In the same one model call, the model reports every stage of the running framework as missing, partial or known (statuses only, never the person's words), the code stores that ledger in one new column, and the stage Mani asks is the first one not yet known. Stages after a `|` on each framework's Stages line (the work stages, like examine or a balanced belief) count only when the person worked them out in their own words in this conversation. A stage asked 4 times without an answer is passed and left behind, and the ending cap now starts at `closing`, so no framework can hold the thread from any stage.

## Requirements

**User stories**:
- As a person who already told Mani what happened and what it meant, I want the questions to start where my story left off, so I am not asked again what I just said.
- As a person who told only part of a stage, I want to be asked only for the part still missing.
- As a person stuck on one question, I want Mani to move on rather than keep me there.
- As muhammad, I want the stage order kept by stored statuses and a number in `tuning`, not by matching words, so it can change with a reseed.

**Acceptance criteria**:

- **AC-1**: Migration `021_technique_state_stage_ledger.sql` adds `stage_ledger jsonb not null default '{}'::jsonb` to `public.thread_technique_state`, with `check (jsonb_typeof(stage_ledger) = 'object')`. The column is named `stage_ledger`, never `known`, because hosted still carries a `known` column from the reverted migration 012. No grant changes: `mani_service` already holds table wide insert and update, `authenticated` keeps select only, and `scripts/test_db.sh` still passes. `rows.TechniqueState` gains `stage_ledger: dict[str, LedgerEntry]` (default empty) and the `threads.apply` upsert writes it. The retire update leaves it as stored.
- **AC-2**: `mani/chat/techniques.py` gains `StageStatus` (`missing`, `partial`, `known`, `passed`), `Registry.ledger_stages(framework_id)` (the framework's phases after `offering` and before its last own phase, in order: for ABCDE `activate, belief, consequence, examine, balanced`), and `Registry.stage_from_ledger(framework_id, ledger)`, which returns the first ledger stage whose status is neither `known` nor `passed`, or the last own phase (`closing`) when there is none. A stage absent from the stored ledger is `missing`.
- **AC-3**: The reply's `state` gains `stages: list[{stage: str, status: str}] | None`, typed loosely like `style` so an off list value costs the entry, never the turn. `guards.check` takes the running framework's ledger stages (from the registry, for `current_framework_id`, or for the tapped framework on a tap accept) and:
  - drops `stages` whole, with a note, whenever it ignores `state` (technique not in the registry, or not the running framework);
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
- **AC-9**: `[ctx]` carries `stage_ledger: <id> <status>, ...` over every ledger stage in order (absent ids as `missing`) while an offer is waiting (`offer_waiting`) and while a framework runs before `closing`, and `stage: <stored phase>`. On a tap accept `stage` is the first ledger stage (the stored ledger is `{}`). When the stored stage's `turns` equal `stage_turn_cap − 1`, `[ctx]` also carries `stage_last_try: yes`. `next_stage` leaves `[ctx]`, `CTX_KEYS` and `response_format.md`, and `test_prompts_name_what_exists.REMOVED` gains it; `stage_ledger` and `stage_last_try` join `CTX_KEYS` and `response_format.md`'s `ctx` section. `framework_stages`, `framework_starting` and `current_phase` stay. From `closing` on, neither new line is sent.
- **AC-10**: Each framework's `Stages:` line carries exactly one ` | ` in place of the ` > ` before its first work stage:

  | Framework | Before the `\|` | After the `\|` (work stages, then `closing`) |
  |---|---|---|
  | abcde | activate, belief, consequence | examine, balanced |
  | thought_reframe | thought, significance | facts, alternative, reframe |
  | structured_problem_solving | problem, facts, control, outcome | options, compare, select, first_action |
  | act_choice_point | situation, present, pull | matters, toward, action |
  | behavioral_activation | stopped, matters | choose, manageable, begin, barrier |
  | dbt_stop | stop | pause, observe, proceed |

  No line grows. `scripts/seed.py` refuses a Stages line without exactly one ` | ` or with no stage on either side, and still matches the ids against `phases`. `test_seed_frameworks.py` covers both refusals.
- **AC-11**: `mani_base.md` `in_a_framework` and `response_format.md` (`ctx.stage_ledger`, `ctx.stage_last_try`, `ctx.offer_waiting`, `ctx.framework_starting`, `ctx.stage_lines`, `fields.state`, `layers.Framework Index`) carry the drafted wording in *Feature design*, reviewed by muhammad before the reseed. No prompt says "never skip a stage". The prompt contract tests pass.
- **AC-12**: `content/prompts/tuning.md` `windows` gains `stage_turn_cap: 4` with a comment saying it is the turns any one stage may take across every visit before it is passed, and `WindowTuning` gains `stage_turn_cap: _count(2, 20)` with no default. `WindowTuning` is strict (`extra="forbid"`), so the code, the tuning key and the reseed ship in one change, as `ending_turn_cap` did. The client may change it with a reseed.
- **AC-13**: Real model evals, run only with muhammad's yes:
  - after the accepting turn of the ABCDE example (event, meaning and effect told before the offer), the stored stage is `examine`, and the reply says the earlier stages back in a clause and asks what supports the belief;
  - with the event told and its meaning vague, the stored stage is `belief` and the reply asks only for what it came to mean;
  - before `closing`, in no transcript does Mani ask a stage the stored ledger holds as `known`, unless the person corrected or took back that answer (from `closing` on the ledger is frozen, AC-6);
  - a free text yes ("yeah let's do it") lands on the same stage as a tap.

  `scripts/eval_replies.py` gains a per turn `expect_stage` (the stored phase after that turn), reported as a finding when it differs.
- **AC-14**: A seeded framework (the seed appends the ending ids to every one; a registry without them is out of scope) holds the thread for at most (ledger stages × `stage_turn_cap`) of the person's messages before `closing`, then at most `ending_turn_cap` after it, from any stage, whatever the model reports. Safety concern turns are not counted (AC-8), since the framework is paused on them.
- **AC-15**: The whole `pytest` passes with pristine output and the integration count checked, after a reseed. `backend/PORT-STATUS.md` gets a "Decisions in force" line for the ledger and edits the ending cap line in place to say it starts at `closing`; `backend/docs/database-schema-reference.md` documents `stage_ledger` and that it differs from hosted's leftover `known`; the client list gets a line saying stages already told are skipped.

**Not in this spec**:
- Getting a framework on the shortlist from plain phrasing (feature 13, which reverses spec 0007's no closest fit).
- Crisis, the safety screen and the model's `crisis` field (feature 10).
- Storing or showing any of the person's words per stage. The ledger holds ids, statuses and counts only.
- Showing the ledger in the API or either frontend.

## Decision

**Chosen option**: a stage ledger reported by the model in the turn's one call, stored as statuses in `thread_technique_state.stage_ledger`, with the code choosing the stage, passing a stage after `stage_turn_cap` turns, and the ending cap starting at `closing`.

The model judges what the person has told; the code keeps order, counts and caps. Before `closing` the ledger decides the stage; from `closing` on, `state.step` and the existing clamp run the ending unchanged.

**Implementation skills**: `supabase-postgres` (`.claude/skills/supabase-postgres/`) for migration 021.

## Rationale

Reasoning and options: see [rationale.md](rationale.md).

## Feature design

**Data model** (migration 021; the rest is unchanged):

| Table | Column | Type | Rule |
|---|---|---|---|
| `public.thread_technique_state` (PK `thread_id`, 1:1 with `threads`) | `stage_ledger` | `jsonb not null default '{}'` | `check (jsonb_typeof(stage_ledger) = 'object')` |
| | its shape | `{"<stage id>": {"status": "missing"\|"partial"\|"known"\|"passed", "turns": <int ≥ 0>}}` | keys are ledger stages of the row's framework; checked in code before writing. Written as a plain dict through the pool's jsonb codec (`mani/db/pool.py`), a new dict each turn since `Row` is frozen; keys that are not ledger stages (after a reseed changes `phases`) are ignored on read and dropped on write |
| | `ending_from` (existing) | `integer`, nullable | now set from `closing` on |

**State transitions**:

- Per stage: `missing` ↔ `partial` ↔ `known`, in any direction as the model reports. Any of these → `passed` when the stage is not `known` and its `turns` reach `stage_turn_cap`. `passed` is final.
- Per framework: `offering` → accepted → the first stage not known or passed (recomputed every turn) → `closing` when all are known or passed → `somatic_checkin` → `somatic_practice` → retired (by `ending`, the ending cap, or a crisis turn). A move back may return the stage to an earlier one before `closing`; from `closing` on, it cannot.

**Interface changes** (no HTTP change):

| Where | Before | After |
|---|---|---|
| `Reply.state` | `technique`, `step`, `accepted` | adds `stages: [{stage, status}]`; `step` counts only from `closing` on |
| `[ctx]` while running or an offer waits | `stage`, `next_stage`, `framework_stages` | `stage_ledger`, `stage`, `stage_last_try` on the last try, `framework_stages` |
| Stored stage | the model's step, at most one forward per turn | `stage_from_ledger` before `closing`; the clamped step after |
| Stuck stage | no limit | passed after `stage_turn_cap` turns |
| Ending cap | from `somatic_checkin` | from `closing` |

**Prompt wording** (drafts; muhammad reviews before the reseed):

`mani_base.md`, the first two `in_a_framework` lines become:

```yaml
in_a_framework:
  - The stage you are on is named in [ctx]. Ask what that stage asks on its Stages line, in your style and their words, about their situation, never bare and never bringing in anything they did not give. If it is partial, ask only for what is still missing.
  - A stage they already answered, before or after the offer, is not asked again unless they corrected or took back what they said. The stages after the | are the ones you work through together, and count only when they worked them out in their own words in this conversation, never from your words or a guess. Take the part of their answer the stage needs and offer nothing else meanwhile. Staying is not repeating, so say what you now understand, name what is still missing in fresh words, and after two tries come at it from a different angle. A stage marked passed is left without a word. Never ask them to confirm what they just said, or explain the method.
```

`response_format.md`:

```yaml
  stage_ledger: each stage before the last, in order, with what you know of it. missing, partial, known, or passed when it was left after too many tries.
  stage_last_try: this is the last try at stage. If it is still not known after their message, leave it without a word and ask the next stage not known in this reply.
  offer_waiting: your last reply offered and they typed instead of tapping. Take it as the answer to the offer, as offers says, and set state.accepted. If it is a yes, do what framework_starting says.
  framework_starting: they just said yes. Judge every stage on stage_ledger against all they told you before, in state.stages, and ask the first one not known. If earlier ones are known, say them back in a clause, in their words, never asking them to confirm.
  stage_lines: stage is the first stage on stage_ledger not known or passed, by id, and what each asks is on the Stages line in the Framework Index. Ask its question in your own words and the conversation style, built from what they have told you, in their words, as its words on the Stages line describe it, never bare. While stage is offering, your offer is still open and offer_waiting says how to take what they typed. On the last stage of the questions, and on somatic_checkin and somatic_practice, the ending section says what to do.
```

`fields.state` gains, after its `step` sentence: "stages is every stage on stage_ledger with its status after their latest message: known when they have said what it asks, partial when only part, missing otherwise. Move one back only when they corrected or took back what they said, and never write passed. From the last stage on it is null." `layers.Framework Index` says the stages after the `|` are worked through together.

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
| `[ctx]` | `stage_last_try` | the stored stage's `turns` against `stage_turn_cap − 1` |
| Running turn | whether the ledger is frozen | `Registry.ending_open(framework_id, stored phase)` |
| Running turn | whether it is a concern turn | `assessment.blocks_framework or model_concern`, as today |
| `[ctx]` | `stage_ledger`, `stage` | the stored row, in `Registry.ledger_stages` order, absent ids shown as `missing` |
| Which stages are work stages | the ` \| ` position | each framework's Stages line, read by the model only; no code reads the split |
| `ending_from` | its value | `count_after` on the first recorded phase where `ending_open` is true; carried after |
| Ending cap | turns since `closing` | `(message_count - ending_from) // 2` against `ending_turn_cap` |
| Offer, decline | the ledger | `{}` |

**Key invariants**:
- The ledger never holds a word the person or the model wrote: only stage ids from `phases`, the four statuses and integer counts.
- The stored stage before `closing` is always `stage_from_ledger` of the stored ledger.
- `passed` is written only by the code and never changes after.
- Each ledger stage's `turns` only grows while the framework runs, so the total before `closing` is bounded by ledger stages × `stage_turn_cap`.
- From `closing` on, no reported value changes the ledger.
- A concern turn changes nothing in the row.

**Security model**: no change in who may read or write what. `stage_ledger` is written only by `mani_service` inside the turn's transaction, under RLS like the rest of the row; `authenticated` can select its own row and holds no insert or update (`test_grants.sql`). The ledger carries no health content, only ids and statuses. Log notes carry ids and reasons, never message text or a model supplied value that failed validation.

**Configuration required**: no new env var. `stage_turn_cap` is a `tuning` value in seeded content.

**Critical test scenarios** (scripted model unless marked):
- `Registry.ledger_stages` and `stage_from_ledger` for ABCDE: empty ledger gives `activate`; A, B, C known gives `examine`; B partial gives `belief`; all known or passed gives `closing`; a test registry with no ending ids uses its last phase. Verifies **AC-2**.
- Guards: entries for `closing`, `offering`, an unknown id, status `passed`, status `Done` are dropped with a note; valid entries are kept; a reported step is ignored before `closing`. Verifies **AC-3**.
- Integration, accepting turn: stored `offering`, tapped Try it, scripted `stages` with A, B, C known, step `activate` → stored phase `examine`, ledger turns all 0, note about the step. Verifies **AC-4**, **AC-5**.
- Integration, partial and count: stored `belief` partial, reply keeps it partial → phase `belief`, `turns` 1; four such turns → `belief` passed, phase `consequence`, note. Verifies **AC-4**, **AC-14**.
- Integration, move back: stored `examine` with `belief` known, reply reports `belief` partial → phase `belief`, note. A stored `passed` reported as `missing` stays `passed`. Verifies **AC-4**.
- Integration, no ledger: running on `consequence`, reply `state` null → row written, phase `consequence`, `turns` 1, note. Verifies **AC-4**.
- Integration, concern: running on `belief`, concern message → row unchanged, `turns` unchanged. Verifies **AC-8**.
- Integration, frozen: stored `closing`, reply reports `belief` missing and step `belief` → phase `closing`, ledger unchanged. Verifies **AC-6**.
- Integration, ending cap from closing: first recorded `closing` sets `ending_from`; a thread 24 messages past it on `closing` retires before the call, 22 does not. Verifies **AC-7**.
- Offer and decline write `{}`; a ledger on the offer turn, or on a turn that asks about the offer, is not stored. Verifies **AC-5**.
- Integration, free text yes: offer waiting, scripted `state.accepted` true with A, B, C known → stored phase `examine`; the `[ctx]` sent carried `stage_ledger` and `offer_waiting`. A declined offer asked for again starts from `{}`. Verifies **AC-4**, **AC-5**, **AC-9**.
- Integration, wrong technique: running ABCDE, reply `state.technique` `dbt_stop` with stages → `stages` dropped, held and counted, note. Verifies **AC-3**, **AC-4**.
- Integration, concern tap: Try it tapped on a concern turn → accepted, `offering`, `{}`; the next turn is handled as accepting. Verifies **AC-8**.
- `[ctx]` with the stored stage at `turns` 3 and the cap 4 carries `stage_last_try: yes`; at 2 it does not. Verifies **AC-9**.
- Integration, ledger completes: stored `balanced`, reply reports it known with an offer button → phase `closing`, `ending_from` set, buttons dropped. Verifies **AC-3**, **AC-7**.
- `[ctx]` on a running ABCDE before `closing` carries `stage_ledger` in order and no `next_stage`; on `closing` no `stage_ledger`; contract tests pass. Verifies **AC-9**, **AC-11**.
- Seed: six Stages lines with one ` | ` seed; zero or two ` | `, or none before it, are refused with the reason. Verifies **AC-10**.
- Real model (muhammad's yes): the two ABCDE scenarios and a stall scenario with `expect_stage`. Verifies **AC-13**, **AC-14**.

## Build plan

Tracer Bullet: the first task takes the ABCDE example through every layer (content, seed, schema, guard, orchestrator, database, `[ctx]`), so the accepting turn landing on `examine` is proven before the counting and the backstops are added. The code is the same for every framework, so the ` | ` goes into all six lines in the first task; the other frameworks get their own eval scenarios after ABCDE is proven. One commit per task is fine; the whole `pytest` stays green after each.

1. Tracer, the ABCDE example end to end: migration 021, `LedgerEntry` and `stage_ledger` on `rows.TechniqueState` and the upsert, `StageStatus`, `Registry.ledger_stages` and `stage_from_ledger`, `state.stages` on the reply schema, the guard (AC-3), the running turn branch in the orchestrator applying the ledger on every accepting path (tap, free text, a declined offer asked for again) and after, without counting yet, offer and decline writing `{}`, `[ctx]` `stage_ledger` (also while an offer waits) with `next_stage` removed and the `offer_waiting` wording, the ` | ` in all six Stages lines and the seed rule, the prompt drafts (stop for muhammad's review of the wording), reseed. Unit and integration tests for each. Satisfies **AC-1**, **AC-2**, **AC-3**, **AC-5**, **AC-9**, **AC-10**, **AC-11**.
2. Counting and the backstops: `stage_turn_cap` in `tuning` (code, key and reseed together), the turn count, `passed` and `stage_last_try`, writing the row when no ledger came back, the concern turn changing nothing (and a concern tap accept handled as accepting next turn), the ledger frozen from `closing`, `ending_from` set at `closing` and both cap sites reading `ending_open`. Integration tests for each. Satisfies **AC-4**, **AC-6**, **AC-7**, **AC-8**, **AC-12**, **AC-14**.
3. Evals: `expect_stage` in `scripts/eval_replies.py`, scenarios for the ABCDE example, a partial stage and a stall in `eval_conversations.yaml`, then one per other framework with its intake told before the offer. Ask muhammad before any real run; with a yes, run the ABCDE ones first and read them with `--verbose`, and optionally a three run baseline before and after (about 0.06 dollars each) to see the output token change. Satisfies **AC-13**, **AC-14**.
4. Close out: `PORT-STATUS.md` (a decision line for the ledger, the ending cap line edited in place, the client list), `docs/database-schema-reference.md`, a journal note, reseed, and the whole `pytest` with the integration count checked. Satisfies **AC-15**.

## Consequences

**Positive**:
- The three places that pulled the stage back (the clamp, "never skip a stage", the one skip on accepting) are replaced by one rule, so the better Mani understands before the offer, the shorter the framework.
- A partial stage is visible to the model, so it asks only the missing part.
- Every framework is bounded from any stage, which closes the gap the journal found before `closing`.
- No words are stored: the ledger is not health content.

**Negative / tradeoffs**:
- The model may move a stage back, so a model slip can still ask a stage again; only a correction should do it, and only notes and evals show when it does not. muhammad chose this over making known final.
- The work stage rule is the model's judgement; no code can check "their own words". Evals are the only check.
- Every running turn costs about 30 more output tokens (the list of stages) and about 15 more `[ctx]` tokens; the cached prompt grows by about 100 words.
- A passed stage leaves a hole: the framework goes on without that answer, and the work stages after it may have less to build on. Because `passed` is final, a correction to a passed stage cannot reopen it, and Mani may hold an answer the person later took back. The same holds for any correction from `closing` on, where the ledger is frozen.
- Two different messages racing on one thread already end in last write wins for `phase`; the ledger and its counts inherit the same race. Nothing new, but a lost count is possible.

**Neutral**:
- A framework running at deploy starts with `{}`; its first reply reports the whole ledger from the conversation, and at worst one stage is asked once more. No compatibility code (muhammad, 2026-10-08).
- Hosted must take migration 021 alongside the open reconciliation of 011 to 017; `stage_ledger` does not collide with the leftover `known`.

## Follow-up

- [ ] Tell the client: Mani no longer walks every stage. A stage already told is skipped, a stage asked 4 times is left behind, and the work stages still need the person's own words, so ABCDE's "does not skip directly from the event to a balanced belief" holds.
- [ ] `stage_turn_cap` may change on the client's requirement; it is a reseed.
- [ ] Watch the notes for moves back that were not corrections. If they appear, revisit making `known` final.
