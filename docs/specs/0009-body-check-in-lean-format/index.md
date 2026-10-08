# 0009. The body ending as short rules, ended by a reply field

**Date**: 2026-10-08
**Status**: In Progress
**Decision record**: [rationale.md](rationale.md) (context, premise note, options considered, rationale)

## Summary

The end of a framework becomes a few short rules in `mani_base.md`: Mani asks how they feel, offers a short body check (with an apology when they feel worse), guides it one step per turn with steps it picks, and asks again how they feel. The model ends the framework with one new reply field, `ending`: `choice` shows Chat More / Go to Library and the exercise card, and `keep_talking` shows nothing while Mani stays with their situation. All the code that rewrites the reply or reads words to decide the ending is deleted, and a new column caps the ending at 12 turns in case the model never ends it. Scripted tests prove it, with no real model run, by muhammad's choice.

## Requirements

**User stories**:
- As a person finishing a framework, I want Mani to ask how I feel and offer a short body check that fits me, one step at a time, so I settle before deciding what next.
- As a person who still feels bad at the end, I want Mani to stay and talk with me, not hand me a menu.
- As muhammad, I want the ending written as rules in seeded content, with no code that edits the reply or matches words, so the ending changes with a reseed.

**Acceptance criteria**:

- **AC-1**: The `ending:` section of `content/prompts/mani_base.md` is the one home of the ending's rules (wording drafted in *Feature design*, reviewed by muhammad before the reseed). It says, with no line to be given word for word:
  - on the framework's last own stage, ask how they feel now, about themselves or what they came with; they decide whether it helped, and Mani never says it worked or summarises;
  - on `somatic_checkin`, reflect their answer and offer a short body check in their typed reply; when they feel bad or worse, first say sorry, invite them to say what happened so Mani can help unpack it, and say there is something small to go through together; the check is offered whatever they answer;
  - on `somatic_practice`, one step per reply, waiting for their answer, steps chosen from the allowed list to fit what they said, as many as feel complete, then ask how they feel now;
  - with pain, trouble breathing or feeling faint, no breathing steps: stop and stay with them;
  - when it eased and came back, it often comes in waves, that is not danger or failure, and they can do it again;
  - set `ending` when the ending is over, as AC-4 says.
- **AC-2**: `content/prompts/somatic.md` is deleted. `scripts/seed.py` appends `ENDING_PHASES` (`("somatic_checkin", "somatic_practice")`, defined in `mani/chat/techniques.py`) after each framework's own phases and writes `stages` as `{}` for every framework. `SOMATIC_FILE`, `_FENCED_YAML`, `load_somatic_stages` and the `load_prompts` skip go. Phase ids are unchanged, so a thread already in the ending carries on.
- **AC-3**: `[ctx]` carries no stage block. `context._stage_lines` renders only `stage: <id>` and `next_stage: <id>`; the twelve `stage_*` and `next_stage_*` block keys leave `CTX_KEYS`, and `response_format.md` `stage_lines` drops its body check in sentences and says that on the last own stage and the two ending stages, the `ending` section says what to do. Spec 0007's `CTX_KEYS` contract test passes. `context.py` imports nothing from `ending.py`.
- **AC-4**: `Reply` gains `ending: str | None`, declared after `state`. `response_format.md` `fields.ending` says: `choice` when the ending is over and they feel okay or better (also when they decline the body check feeling okay); `keep_talking` when it is over and they still feel bad (also when they decline feeling bad); null on every other turn. `buttons` says the ending carries no buttons from the model, and Chat More and Go to Library are added for you.
- **AC-5**: `Registry.ending_open(framework_id, phase) -> bool` is true when the framework's phases contain the first `ENDING_PHASES` id and `phase` is the phase just before it (its last own phase) or an ending phase; false for an unknown framework, a null phase, or a framework with no ending ids (a test registry, or a database not yet reseeded). `guards.check` takes `ending_open: bool = False` (so `tests/evals/test_negative_set.py`'s call is unchanged), passed by the orchestrator as `ending_open(...)` of the stored phase and only for an accepted framework. It keeps `ending` only when:
  - `ending_open` is true;
  - the value, stripped and lowercased, is `choice` or `keep_talking`;
  - the clamped reported phase, if any, does not move past the stored phase (a reply that offers the body check or starts its steps is not also the end).

  Otherwise it drops it with a note (`ignored ending: <reason>`). `Checked` gains `ending: str | None`, and a kept `ending` makes the turn retiring for the technique button guard. On a safety concern turn the orchestrator sets `ending` to None, as it does `framework_id` and `phase`, so the framework pauses rather than ends.
- **AC-6**: On a kept `choice`, the framework retires on this turn: `updates.retire_technique` is true and the `new_offer`, `_decided_framework` and tapped branches write nothing, so the reported state never overwrites the retirement. The reply's buttons are exactly Chat More and Go to Library (library `home`), `library_offered_since` is set, and the exercise card is picked as on today's retiring turn. A tapped Chat More on the next turn is an ordinary turn: the framework is already retired, so no extra handling is needed.
- **AC-7**: On a kept `keep_talking`, the framework retires the same way, the reply has no buttons and no exercise card, and `library_offered_since` is set, so the next turn's `[ctx]` shows `conversation_phase: talking` and no `library_pending`. With no Chat More button in the window, the after framework questions are not sent either; that is intended, since Mani stays with their situation.
- **AC-8**: After `guards.check`, on every turn whose stored phase or clamped `checked.phase` is the last own phase or an ending phase, and on every retiring turn (cap, `choice`, `keep_talking`), every button the model sent is dropped with a note. The only ending buttons are AC-6's, written by the code.
- **AC-9**: Migration `020_technique_ending_from.sql` adds `ending_from integer` (nullable, `check (ending_from >= 0)`) to `public.thread_technique_state`, and in the same migration sets it to the thread's `message_count` for every row whose phase is `somatic_checkin` or `somatic_practice`, so threads already in the ending are capped too. `rows.TechniqueState` and the `threads.apply` upsert carry it; the turn context query reads the whole row (`to_jsonb`), so it needs no change. It is set to `count_after` on the first reply recorded in an ending phase, then carried from the stored row (a step back to the last own phase keeps it, so the cap cannot be reset), and set to null only by the retire update (`set phase = null, ending_from = null`). No grant changes: `mani_service` already holds table wide insert and update, and `scripts/test_db.sh` still passes.
- **AC-10**: `ENDING_TURN_CAP = 12` in `mani/chat/orchestrator.py`. When an accepted framework's stored phase is an ending phase, `ending_from` is set, and `(message_count - ending_from) // 2 >= ENDING_TURN_CAP`, the turn retires the framework before the model call, so `[ctx]` shows nothing running and the guard is told the turn is retiring. The reply has no buttons and no exercise card, and `library_offered_since` is set. A log line names the thread id and the cap, never message text. The three retiring paths are: the cap (before the call, no handoff, no card), `choice` (after the call, handoff and card) and `keep_talking` (after the call, neither).
- **AC-11**: `mani/chat/ending.py` and `tests/unit/test_ending.py` are deleted. `_body_route_step`, `_awaiting_place`, `_offered_handoff`, `_ASKS_WHAT_NEXT`, `_HANDOFF_LABELS`, the check in insertion, the returning reply swap, the `is_final` retirement before the call and `Registry.is_final` are gone. Nothing under `backend/mani/chat/` reads a framework's `stages`, and no code matches words in a reply or a message to drive the ending. `rows.Framework.stages` and `config_tables.FRAMEWORK_COLUMNS` keep reading the column for the admin side until it is dropped, and the stale comment above `rows.Framework.stages` says it is empty. The `context.resolve_style` docstring and the `context.build` comment that mention a somatic stage's `ask` are corrected. `CHAT_MORE_LABEL`, `GO_TO_LIBRARY_LABEL` and `_handoff()` stay.
- **AC-12**: A crisis turn (which makes no model call and locks the thread) retires a framework whose `ending_open` is true, with no buttons, so a locked thread never holds a framework mid ending. `test_a_framework_completing_on_a_crisis_turn_is_still_retired` is rewritten to start from a stored ending phase, and the comment in `_handle_crisis` says what it now retires.
- **AC-13**: The whole `pytest` passes with pristine output and the integration count checked (not skipped), after a reseed. `test_prompts_name_what_exists.REMOVED` gains `stage_purpose`, `stage_listen_for`, `stage_ready_when`, `stage_boundaries`, `stage_if_unclear` and `stage_ask`. Nothing is run against a real model (muhammad, 2026-10-08), but the eval files match the new flow:
  - `validators.missing_handoff` and `tests/evals/test_style_findings.py` key on the ending phase ids instead of the literal `"somatic"` (which matched no real phase). The rule: a reply that moves the framework from an ending phase to retired carries both handoff buttons or neither;
  - `panic_somatic_once` starts at `closing` and its turns become: "it is better i guess", "yes", "ok", "I can see my desk, a lamp and the window", "I feel calmer for a second, then it comes back", "still not great honestly".

  `backend/PORT-STATUS.md` (the body route paragraph, the `ending.py` mention, the open "Body route" item, a new "Decisions in force" line), `backend/docs/specs/README.md` (its `somatic.md` line) and `backend/docs/database-schema-reference.md` (the new column, and that it differs from hosted's leftover `ending` column) are updated in the same change.

**Not in this spec**:
- Moving `CHAT_MORE_LABEL` and `GO_TO_LIBRARY_LABEL` into seeded content (muhammad kept them as constants). `ENDING_TURN_CAP` moves into spec 0008's `tuning` row when 0008 is built.
- The exercise pick: unchanged, and not told anything about the body check.
- Crisis handling, the safety screen and the model's `crisis` field. Feature 10.
- Dropping the now unused `admin.frameworks.stages` column.

## Decision

**Chosen option**: the ending as rules in `mani_base.md`, a closed `ending` field on the reply as the only signal that it is over, code that attaches the two handoff buttons and retires, and a counted turn cap as the backstop.

Python keeps the state machine (phase ids, order, retirement, the cap) and the buttons; the model keeps every word and every judgement about how the person feels.

## Feature design

**The ending section** (draft for `mani_base.md`, replacing its two `ending:` lines; muhammad reviews it before the reseed):

```yaml
ending:
  - On the last stage, ask how they feel now, about themselves or what they came with. They decide whether it helped. Never tell them it worked or summarise what you did together.
  - Then reflect their answer and offer a short body check, a few small steps to notice and settle the body. If they feel bad or worse, first say you are sorry, invite them to tell you what happened so you can help them unpack it, and say you have something small you can go through together. If they already know what they will do next, or say no, do not push.
  - In the body check, give one step per reply and wait for their answer before the next. Choose the steps that fit what they told you, from slow breaths in through the nose for four and out through the mouth for six, a hand on the chest or the stomach while breathing slowly, feet pressed into the floor, three things they can see, two things they can hear, one slow breath out, and gentle attention to where they feel it. Stop when it feels complete, then ask how they feel now.
  - If they mention pain, trouble breathing or feeling faint, give no breathing step. Stop, stay with them and ask what would help.
  - If it eased and came back, say it often comes in waves, that it coming back is not danger or failure, and that they can do it again.
  - When the ending is over, set ending, as its field says. If they still feel bad, stay with what they are going through.
```

**Data model** (migration 020; the rest is unchanged):

| Table | Column | Type | Rule |
|---|---|---|---|
| `public.thread_technique_state` | `ending_from` | `integer`, nullable | `check (ending_from >= 0)`; the thread message count when the ending began; null outside the ending |
| `admin.frameworks` | `phases` | `text[]` | each framework's own phases, then `somatic_checkin`, `somatic_practice` |
| `admin.frameworks` | `stages` | `jsonb` | `{}` for every framework, read by nothing |

**State transitions**: `offering` → accepted → each own phase → last own phase (how do you feel) → `somatic_checkin` (the offer of the body check) → `somatic_practice` (the steps) → retired. Retirement comes from a kept `ending` (from the last own phase on, so a decline or an answer that needs no check can end it there), from the cap, or from a crisis turn while the ending is open. Skipping a phase is still clamped, and holding or stepping back is still allowed. A safety concern pauses the ending as it pauses any stage.

**Interface changes** (no HTTP change):

| Where | Before | After |
|---|---|---|
| `Reply` schema | no `ending` | `ending: str \| None`, `choice` or `keep_talking` |
| `[ctx]` on ending turns | `stage_*` and `next_stage_*` blocks with the client's scripts | `stage` and `next_stage` ids only |
| Ending buttons | place buttons, then Chat More / Go to Library, chosen by reading the reply | none, then Chat More / Go to Library on `choice` only |
| Retirement | the turn after `somatic_practice`, unless the last reply had place buttons | the turn the model sets `ending`, or the cap |

**Value sourcing**:

| Action | Value | Source |
|---|---|---|
| Ending turn | what to ask, offer, which steps, how many | the `ending` section of `mani_base.md`, in the cached system prompt |
| Ending turn | where they are | `[ctx]` `stage`, `next_stage`, `framework_stages` from `thread_technique_state.phase` and `admin.frameworks.phases` |
| Ending turn | how they feel | the model's judgement from the conversation, reported as `ending` |
| `guards.check` | `ending_open` | `Registry.ending_open(framework_id, stored phase)`, passed only when the outcome is `accepted` |
| `guards.check` | whether the reply moves forward | the clamped reported phase's index against the stored phase's, in `framework.phases` |
| Crisis turn | whether to retire | `Registry.ending_open` of the stored phase |
| `choice` | the buttons | `_handoff()` (`CHAT_MORE_LABEL`, `GO_TO_LIBRARY_LABEL`, library `home`) |
| `choice` | the exercise card | `_offer_exercise`, unchanged |
| `choice`, `keep_talking`, cap | `library_offered_since` | set through `ThreadUpdates.library_offered` |
| `ending_from` | its value | `count_after` on the first reply recorded in an ending phase; carried from the stored row after that; for rows already in the ending, `threads.message_count` at migration 020 |
| Cap | turns in the ending | `(ctx.thread.message_count - technique.ending_from) // 2` against `ENDING_TURN_CAP` |
| Seed | the ending phase ids | `techniques.ENDING_PHASES` |

**Key invariants**:
- No code adds, removes or replaces a sentence of the model's reply, including in the ending.
- No code reads the words of a reply or a message to decide the ending's buttons, state or retirement.
- A framework in its ending retires within `ENDING_TURN_CAP` of the person's messages.
- Chat More / Go to Library appear only with a kept `choice`, both together.
- `ending_from` is null on every retired row, and once set it is never moved forward while the framework stays accepted, so the cap cannot be reset.
- A reply that moves the phase forward never ends the framework.

**Security model**: no change in who may read or write what. `ending_from` is written only by `mani_service` under RLS, like the rest of the row, and `authenticated` still holds no insert or update on the table (`test_grants.sql`). Logs carry ids and the cap, never message text. The pain, breathing and faint rule moves from a scripted reply to a model rule; the safety screen and the crisis lock are untouched.

**Configuration required**: none new.

**Critical test scenarios** (scripted model, no real run):
- Seed: each framework's `phases` ends with the two ending ids, `stages` is `{}`, and a prompts directory without `somatic.md` seeds. Verifies **AC-2**.
- `[ctx]` on `closing`, `somatic_checkin` and `somatic_practice` carries `stage` and `next_stage` and no `stage_*` block line; the contract test passes. Verifies **AC-3**.
- `Registry.ending_open`: true on `closing`, `somatic_checkin` and `somatic_practice` of a seeded framework; false on a mid framework stage, a null phase, an unknown id, and a registry whose phases have no ending ids. Verifies **AC-5**.
- Guards: `choice` and ` Keep_Talking ` are kept while the ending is open; `choice` on a mid framework stage, on no framework, `done`, and `choice` with a reported phase past the stored one (stored `closing`, reported `somatic_checkin`) are dropped with a note; a kept `ending` drops a technique button. Verifies **AC-4**, **AC-5**.
- Integration, crisis: a crisis message on a thread stored in `somatic_practice` locks it and leaves the framework retired. Verifies **AC-12**.
- Integration, choice: a thread on `somatic_practice`, the model scripted with `ending: choice` and its own buttons, stores phase null and `ending_from` null, returns exactly Chat More and Go to Library and an exercise, and the next turn has no `library_pending`. Verifies **AC-6**, **AC-8**.
- Integration, keep talking: the same with `keep_talking` returns no buttons and no exercise, and the next turn's `[ctx]` says `talking` with no `library_pending`. Also from `somatic_checkin` (a decline). Verifies **AC-7**.
- Integration, concern: `ending: choice` on a turn the screen flags as a concern leaves the phase as stored and adds no buttons. Verifies **AC-5**.
- Integration, ending_from: the first reply reported in `somatic_checkin` stores `ending_from` equal to the thread's count; a later `somatic_practice` reply keeps it; a step back to the last own phase keeps it; retirement clears it. Migration 020 against a row already in `somatic_practice` sets it to the thread's count. Verifies **AC-9**.
- Integration, precedence: on a kept `choice` with `state` reporting `somatic_practice`, the stored row has phase null, not `somatic_practice`. Verifies **AC-6**.
- Integration, cap: a thread with `ending_from` 24 messages behind retires before the call, the scripted model sees no `active_framework`, and the reply has no buttons or exercise. At 22 messages behind it does not. Verifies **AC-10**.
- No module under `mani/` defines `_body_route_step` or imports `mani.chat.ending`; `REMOVED` finds no `stage_*` block key in any prompt. Verifies **AC-11**, **AC-13**.

## Build plan

Tracer Bullet: the first task threads the `choice` path through every layer (content, seed, `[ctx]`, schema, guard, orchestrator, database) and removes the old route it replaces, so the new path is proven before the other endings and the backstop are added. One commit per task is fine; the whole `pytest` stays green after each.

1. Tracer, `choice` end to end: draft the `ending` section and `fields.ending` (stop for muhammad's review of the wording), delete `somatic.md` and the seed merge (`ENDING_PHASES` in `techniques.py`, `stages` `{}`), trim `_stage_lines`, `CTX_KEYS` and `stage_lines`, add `Reply.ending`, `Registry.ending_open`, the guard (with the forward move rule) and `Checked.ending`. In the orchestrator, retire on `choice` after the call, with retirement winning over the state branches (AC-6), `_handoff()`, `library_offered` and the exercise, and drop the model's buttons on ending turns after `guards.check`. Delete `_body_route_step`, the check in insertion, the returning reply swap, the pre call `is_final` retirement, `_awaiting_place`, `_offered_handoff`, `_ASKS_WHAT_NEXT`, `_HANDOFF_LABELS`, `Registry.is_final` (and its tests in `test_techniques.py`, around lines 109 to 124), `ending.py` and `test_ending.py`. In `test_turn.py`, rewrite `_retire_abcde_on` (around line 545) to script `ending: choice`, then its callers (around lines 624, 643, 665, 718, 781 and 898) and the tests around lines 453 and 488, which relied on retiring the turn after `somatic_practice`. Rewrite the ending cases in `test_chat_context.py` and the seed tests, and add the `ending_open` and guard cases. Reseed. Satisfies **AC-1**, **AC-2**, **AC-3**, **AC-4**, **AC-5**, **AC-6**, **AC-8**, **AC-11**.
2. `keep_talking` and the pauses: retire with no buttons and no card and set `library_offered`, the safety concern clearing `ending`, and the crisis turn retiring an open ending (AC-12, rewriting the crisis test around line 891 and the `_handle_crisis` comment). Integration tests for each, including a decline from `somatic_checkin`. Satisfies **AC-5**, **AC-7**, **AC-12**.
3. The backstop: migration 020 with its fill of rows already in the ending, `ending_from` through `rows.TechniqueState` and the upsert, cleared by the retire update, and `ENDING_TURN_CAP` retiring before the call as a retiring turn for the guard. Run `scripts/test_db.sh` and the integration tests for both. Satisfies **AC-9**, **AC-10**.
4. Close out: `REMOVED`, `missing_handoff` and `test_style_findings.py` on the ending phase ids, `panic_somatic_once` with its new turns, any ending reference left in `eval_replies.py`, `PORT-STATUS.md`, `backend/docs/specs/README.md`, `docs/database-schema-reference.md`, reseed, and the whole `pytest` with the integration count checked. Satisfies **AC-13**.

## Consequences

**Positive**:
- The last code that edited the model's reply is gone, along with three regexes, a place matcher and the button reading. The ending changes with a reseed.
- The ending's rules sit in the cached system prompt. Each ending turn stops paying for the uncached stage blocks, which carried all three styles' practices.
- A person who still feels bad is not handed a menu, and the Library is not pushed at them afterwards.
- A thread can no longer be stuck in its ending.

**Negative / tradeoffs**:
- The client's documents end every framework with a body check, worded per style, and a fixed practice per place. This flow offers the check rather than running it, and drops the per style lines, the four places and their practices. That is muhammad's design and wording permission (2026-10-05); the client has not seen it.
- The model judges how they feel, picks the steps, decides when the practice is complete and when the ending is over. It may give two steps in one reply, stop early, run long, or end with `choice` for someone who still feels low. Nothing measures this until feature 11: it ships on scripted tests alone.
- A model that never sets `ending` holds the framework, and blocks new offers, for up to 12 of the person's messages. A model that sets it too early cuts the practice short. The forward move rule catches an `ending` on the reply that offers the check or starts the steps, but nothing structural catches `choice` on the practice's last "how do you feel now?" reply, before they answer.
- The cooldown before a new offer still counts from their yes to the framework, so after `keep_talking` an offer can come about 20 messages later. Offer timing belongs to spec 0008's `tuning` and is left as it is.
- A crisis turn now retires a framework in its ending, which before only happened after the practice.
- The every turn cached prompt grows by about six lines.
- `library_offered_since` now means "no Library offer is owed", set also when it was not offered. The column name no longer says exactly what it holds.
- A new migration on a hosted database that is already seven migrations away from this code (PORT-STATUS, "Open engineering").

**Neutral**:
- `CHAT_MORE_LABEL` and `GO_TO_LIBRARY_LABEL` stay in Python, so feature 7 meets "no code reads `when` text" but not "nothing hardcoded" for those two labels.
- `ENDING_TURN_CAP` is a Python constant until spec 0008 moves it into `tuning`.
- `admin.frameworks.stages` stays as an empty object, read by nothing.
- Spec 0008's line references in `context.py`, `orchestrator.py` and `test_turn.py` go stale once this is built first.

## Migration plan

**Strategy**: migrate, seed, then deploy.
**Phases**:
1. Apply `020` to hosted (after muhammad's yes). Old code ignores the column.
2. Seed hosted. Old code then finds empty `stages`: it inserts no check in and no practice, and still retires after `somatic_practice`, so the ending is plainer for those minutes but never fails.
3. Deploy. Threads in the ending when `020` ran were filled by it. One that entered the ending between `020` and the deploy has `ending_from` null, which the next reply recorded in an ending phase sets.

**Rollback**: revert the code, restore `somatic.md` and the old `mani_base.md` from git, and reseed. The column can stay, because old code never reads it.
**Risks**: deploying before the seed leaves the new code with the old two line `ending` rule and no `ending` field description, so the model rarely sets `ending` and the cap ends every ending. Keep the order.

## Follow-up

- [x] Spec 0008: `ending_turn_cap` (12, allowed 2 to 50) added to the `tuning` table under `windows`, `ENDING_TURN_CAP` to the names it removes, and its "Not in this spec" list trimmed to the two labels.
- [ ] Move `CHAT_MORE_LABEL` and `GO_TO_LIBRARY_LABEL` into the `replies` row once spec 0008 has built it.
- [ ] Measure under feature 11, after muhammad's yes: `panic_somatic_once` in all three styles, one ending where they feel worse, and how often the cap fires (one step per reply, a fitting step count, `choice` versus `keep_talking`).
- [ ] Drop `admin.frameworks.stages` in its own migration.
- [ ] Tell the client the ending now offers the body check and lets Mani choose the steps, since their documents describe a fixed check and fixed practices.
- [ ] `.claude/BACKEND.md` names `ending.py` as the body ending. For `/sync`.
- [x] Scope feature 7's Done when line updated to this flow.

## Rationale

Reasoning and options: see [rationale.md](rationale.md).
