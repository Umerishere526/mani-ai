# 0004. Require a thinking level on every model call

**Date**: 2026-10-07
**Status**: In Progress
**Decision record**: [rationale.md](rationale.md) (context, options considered, rationale)

## Summary

Every model call the backend makes will name its own thinking level (how hard a reasoning model thinks before it answers, billed as output tokens) in its own prompt row. The config default `REASONING_EFFORT` goes away, so no call runs on a level nobody chose. The exercise pick and the voice translation get their own prompt rows, since they are the two calls that have none today. A missing or unknown level is refused when seeding, when an admin edits a prompt, and right before a call goes out. Every call stays on `high`, so nothing changes in what the model is asked or what it costs; feature 11 tunes the levels from measurements.

## Requirements

**User stories**:
- As muhammad, I want every model call to name its own thinking level in its prompt row, so that the cost and latency of each call is a choice I can see and tune, not an environment default.
- As muhammad, I want a missing or wrong level to be refused where it is written, so that a portal edit or a stale seed cannot quietly change what a call costs.

**Acceptance criteria**:
- **AC-1**: Each of the five model calls reads its thinking level from its own active prompt row's `model_parameters.reasoning_effort` and sends it to models that read one: chat turn and its redrafts from `mani_base`, summary from `summarization`, memory fold from `memory_fold`, exercise pick from `exercise_select`, voice translation from `voice_translation`. No call reads a level from anywhere else.
- **AC-2**: `Settings` has no `reasoning_effort` field, `.env.example` has no `REASONING_EFFORT`, and `chain` has no default level to fall back to. A leftover `REASONING_EFFORT` in someone's `.env` is ignored and changes nothing.
- **AC-3**: `python scripts/seed.py` stops with an error naming the file, and writes nothing, when any call prompt (a name in `CALL_PROMPTS`) has no `reasoning_effort` or one outside `low`, `medium`, `high`, `xhigh`, `max`, whatever its `model_id`. It also stops when a name in `CALL_PROMPTS` has no file in `content/prompts/`. Layer prompts (`response_format`, `title_generation`) and `somatic.md` need no level.
- **AC-4**: `POST /admin/prompts` and `PATCH /admin/prompts/{id}` refuse, with the standard `invalid_request` error (422) and no change saved, any write after which a row named in `CALL_PROMPTS` has no valid level. The check runs on the row as it would be after the edit, so replacing `model_parameters` without the level, or renaming a layer row to a call name, is refused. A level that is not a string, and `model_parameters` that is null or not an object, count as no valid level (422, never 500). The same routes also refuse renaming a call row to a name outside `CALL_PROMPTS` and setting `is_active` false on a call row, since either one breaks the call. Edits to layer rows, and edits to a call row that keep a valid level, pass as today.
- **AC-5**: At call time, a call whose row is missing, inactive, or has no valid level raises a `config_error` before any request reaches OpenRouter, so no tokens are spent and no `admin.llm_calls` row is written for it. Each call then fails along its existing path: the chat turn returns 500 `config_error` in the standard error shape and reaches Sentry; the summary raises inside the summary step and `update_quietly` logs it and keeps the existing summary; the memory fold raises in `fold_one` and `fold_finished` logs it, as it does today for a missing row; the exercise pick logs and offers the first candidate exercise, as it does today when the pick returns nothing; the voice translation logs and returns the untranslated transcript.
- **AC-6**: `content/prompts/exercise_select.md` and `content/prompts/voice_translation.md` exist and are seeded. The exercise row holds a fixed instruction, and the code appends the framework name and the exercise list beneath it, so no row edit can break the call's formatting. The translation row holds today's translation instruction word for word. Neither instruction remains as a Python constant.
- **AC-7**: The change alters no request a call sends. Each of the five calls goes out with the same model, effort (`high`), output budget (`chain.sampling`) and provider routing as before: the exercise pick keeps a reply budget of 200 tokens and the translation 500, and both keep routing Azure first with `data_collection` deny.
- **AC-8**: When the prompt cache loads and any call row (including `exercise_select` and `voice_translation`) is missing or inactive, it logs a warning naming it, as it already does for `title_generation` and `summarization`. `EXPECTED_PROMPTS` is derived from `CALL_PROMPTS` plus the layer rows, so there is one list of calls, not two.

## Decision

**Chosen option**: Option 1: Required level in every call's own row, one shared check

Every model call reads a required thinking level from its own prompt row; `CALL_PROMPTS` names the call rows, and one check guards seed, the admin routes, and the call itself.

Settled in design (muhammad's picks): own seeded rows for the exercise pick and the voice translation; required on every call row whatever the model; refused at seed, admin edit and call time; a missing level fails only that call, as a config error; call rows named by a set in code; the exercise row holds a fixed instruction with the facts appended; allowed values stay `low` to `max`; both new rows start on `high`; `model_id` stays optional (out of scope); hosted is seeded before the deploy; no References section. After the cross check (muhammad accepted each recommended fix): the placements and failure handling below, refusing rename and deactivation of call rows, and gating hosted behind the 011 to 017 reconciliation.

Decided at write time:
- **Where the check lives**: a small module `backend/mani/prompts/calls.py` holding `CALL_PROMPTS` and `effort_problem(name, model_parameters) -> str | None` (returns why a row is not acceptable, or `None`). The allowed values become `ReasoningEffort = Literal["low", "medium", "high", "xhigh", "max"]` in `backend/mani/llm/chain.py`, which `calls.py` imports, so `chain` never depends on `prompts`. Runner up: putting it all in `chain.py`, rejected because which row names are calls is a prompt concern, not a request concern.
- **How chain refuses**: `chain._reasoning`, `request_body`, `build` and `build_tool_choice` take `effort: ReasoningEffort` as a required argument with no default, and `client.complete` and `client.choose_exercise` take `reasoning_effort` as required. A forgotten call site is then a type and test failure, not a runtime surprise. The `config_error` itself is raised where the row is read (the call site), through one helper `calls.effort_for(prompt, name) -> ReasoningEffort` that raises `ServiceError(CONFIG_ERROR)`. Runner up: raising inside `chain`, rejected because `chain` does not know which row a call came from and could not name it in the error.
- **Seed validates before writing**: parse and check every prompt file before `asyncpg.connect`, ahead of the framework upsert, so a bad file stops the run before any connection opens. A call row is matched by its frontmatter `name`, never by its file name. The seed already runs in one transaction, so a late failure would roll back too, but checking first gives one clear error and no half run.
- **Exercise pick reads its own row**: model, temperature, `maxTokens` and routing come from `exercise_select`, with today's values as the row's values, rather than being passed down from the chat turn's row. Today the pick inherits `mani_base`'s model (`gpt-6-luna`), routing (empty, so the `Settings` default) and `DEFAULT_TEMPERATURE` (0.7); the new row sets the same model and `temperature: 0.7` with no routing, so the request is identical. `_offer_exercise` drops its `model` and `routing` arguments. This keeps "a call's configuration lives in its row" true for all five calls.
- **Chat turn check placement**: the orchestrator calls `calls.effort_for(config.require("mani_base"), "mani_base")` once, right after the daily limit check and before the first `client.complete`, and passes the result to both the first draft and the redraft. `composer.model_settings` keeps its signature. Runner up: calling it inside `model_settings`, rejected because that runs before the daily limit check and would turn a limited person's request into a config error.
- **Exercise pick failure**: `_offer_exercise` reads the row and calls `effort_for` inside a `try` that catches `ServiceError`, logs a warning, and returns `candidates[0]`, so a turn whose reply is already built never becomes a 500 over the exercise pick.
- **Voice path failure**: `cache.load()` and `effort_for` go inside the existing `try` in `_translate_to_english`, so a database hiccup on a cold cache, or a missing row, still degrades to the untranslated transcript. The warning names the row and the reason, never the transcript.
- **Type safety of the check**: `effort_problem` returns a problem string, never raises, for a level that is not a string and for `model_parameters` that is null or not a dict, so bad portal input is a 422, not a `TypeError` and a 500.
- **Where the admin check runs**: inside `config_tables.create_prompt` and `config_tables.update_prompt`, on the row the statement returns, in the same transaction as the write and the `prompt_versions` snapshot, raising `ServiceError(INVALID_REQUEST)` so the whole write rolls back. Runner up: a second read in the route before the write, rejected because it adds a read and a race between the read and the update. The same check refuses a call row renamed out of `CALL_PROMPTS` (compare the stored name before the update) or set inactive.
- **Row ids**: `exercise_select` is `10000000-0000-0000-0000-000000000012` and `voice_translation` is `10000000-0000-0000-0000-000000000013`, the next free numbers after `...011`.

## Feature design

**Data model sketch**: no schema change. Two new rows in the existing `admin.prompts` table, written by `scripts/seed.py`:

| Row `name` | `model_id` | `model_parameters` | `content` |
|---|---|---|---|
| `exercise_select` | `openai/gpt-6-luna` | `{"maxTokens": 200, "temperature": 0.7, "reasoning_effort": "high"}` | fixed instruction: the person just completed a framework; call `start_exercise` with the id from the list below that best fits what they worked through |
| `voice_translation` | `openai/gpt-6-luna` | `{"maxTokens": 500, "temperature": 0, "reasoning_effort": "high"}` | today's `_TRANSLATE_SYSTEM_PROMPT`, word for word |

Their frontmatter ids are `10000000-0000-0000-0000-000000000012` (`exercise_select`) and `10000000-0000-0000-0000-000000000013` (`voice_translation`). Before seeding any shared database, confirm no row of another name already holds either id, since the seed upserts on `name` and a clash is a primary key violation. `PATCH /admin/prompts/{id}` snapshots `model_parameters` into `admin.prompt_versions`, so a level changed in the portal is recorded. `scripts/seed.py` upserts without a snapshot and without bumping `version`, so a level changed by reseeding leaves no history row; feature 11 must record its before and after levels itself.

**State transitions**: none.

**API surface**: no new endpoints. Changed behaviour on two:

| Endpoint | Method | Key inputs | Key outputs | Auth | Key errors |
|---|---|---|---|---|---|
| /admin/prompts | POST | `PromptCreateIn` (unchanged) | `PromptOut` | admin | 422 `invalid_request` when the new row is a call row with no valid level |
| /admin/prompts/{id} | PATCH | `PromptIn` (unchanged) | `PromptOut` | admin | 422 `invalid_request` when the row after the edit is a call row with no valid level; 404 as today |

Internal interfaces that change:

| Function | Change |
|---|---|
| `chain._reasoning`, `request_body`, `build`, `build_tool_choice` | `effort: ReasoningEffort` required; no `settings.reasoning_effort` fallback |
| `client.complete`, `client.choose_exercise` | `reasoning_effort` required; `choose_exercise` also takes the row's instruction `content` |
| `stt._translate_to_english` | reads the `voice_translation` row from `cache.load()` for content, model, effort, budget and temperature |
| `orchestrator._offer_exercise` | reads the `exercise_select` row from the loaded config and passes its values; drops its `model` and `routing` arguments; catches `ServiceError` and returns `candidates[0]` |
| `orchestrator.send` | calls `effort_for` for `mani_base` once after the daily limit check; passes it to the draft and the redraft |
| `config_tables.create_prompt`, `update_prompt` | run `effort_problem` on the written row inside the transaction; refuse renaming or deactivating a call row |
| `prompts.cache.EXPECTED_PROMPTS` | derived from `CALL_PROMPTS` plus the layer rows |
| `calls.effort_for(prompt, name)` | new; returns the row's level or raises `ServiceError(CONFIG_ERROR)` |
| `calls.effort_problem(name, model_parameters)` | new; never raises; shared by seed and the admin writes |

**Value sourcing**:

| Action | Value produced / sent | Source |
|---|---|---|
| Chat turn and redrafts | reasoning effort | `mani_base` row `model_parameters.reasoning_effort` |
| Summary | reasoning effort | `summarization` row `model_parameters.reasoning_effort` |
| Memory fold | reasoning effort | `memory_fold` row `model_parameters.reasoning_effort` |
| Exercise pick | reasoning effort, model, reply budget, temperature, routing | `exercise_select` row (`model_parameters.reasoning_effort`, `model_id or settings.default_chat_model`, `maxTokens` with 200 as the code default, `temperature` with `client.DEFAULT_TEMPERATURE` as the code default, `routing`; today's values come from `mani_base`, which the row reproduces) |
| Exercise pick | instruction text | `exercise_select` row `content` |
| Exercise pick | framework name and exercise list | appended by code from `config.registry` and `exercises_db`, as today |
| Voice translation | reasoning effort, model, reply budget, temperature, routing | `voice_translation` row (`model_parameters.reasoning_effort`, `model_id or settings.default_chat_model`, `maxTokens` with 500 as the code default, `temperature` with 0 as the code default, `routing`) |
| Voice translation | instruction text | `voice_translation` row `content` |
| Seed and admin check | which rows are calls | `CALL_PROMPTS` in `mani/prompts/calls.py` |
| Seed and admin check | allowed levels | `ReasoningEffort` in `mani/llm/chain.py` |
| Admin POST and PATCH check | the row after the edit | the row `create_prompt` / `update_prompt` writes and returns, checked inside the same transaction |
| Admin PATCH check | whether a call row is being renamed away | the stored `name` before the update, compared with `CALL_PROMPTS` |
| Total output budget sent | `max_completion_tokens` | `chain.sampling`: the row's reply budget plus `REASONING_ALLOWANCE_TOKENS`, unchanged |

**Key invariants**:
- No request leaves `chain` without an explicit `ReasoningEffort` chosen by a row; there is no default anywhere in the backend.
- Every name in `CALL_PROMPTS` has a file in `content/prompts/` and, once seeded, a row with a valid level.
- The level is checked the same way in all three places, by the same function.
- Routing for every call still goes through `settings.routing(row.routing)`, so `data_collection` deny holds for both new rows.

**Security model**: unchanged. The admin routes stay admin only. The prompt cache reads through `pool.as_admin()` as it already does for the summary and memory fold; the voice translation joining that path reads only prompt rows, never user data. Conversations and transcripts are special category health data: the voice translation keeps the same provider order and `data_collection` deny as every other call (AC-7), and nothing in this change logs transcript text (the existing warning logs only the failure).

**Configuration required**: none added. `REASONING_EFFORT` is removed from `Settings` and `.env.example`.

**Critical test scenarios** (few, on real logic, using fakes built from the real interfaces):
- Seed check: a temporary call prompt file with no level, and one with `"extreme"`, are refused with the file named; a layer prompt with no level passes; a name in `CALL_PROMPTS` with no file is refused. Verifies **AC-3**.
- Every authored prompt: each name in `CALL_PROMPTS` has a file whose level is allowed (replaces `test_every_prompt_on_a_reasoning_model_says_how_hard_to_think` from `9be3b38`, which only checked reasoning models). Verifies **AC-1**, **AC-3**, **AC-6**.
- Admin check on the merged row: replacing a call row's `model_parameters` without the level is refused; renaming a layer row to `memory_fold` without a level is refused; `reasoning_effort: ["high"]` and `model_parameters: null` are refused with 422, not 500; renaming `memory_fold` to another name, and setting it inactive, are refused; a content only edit to a valid call row passes; an edit to `response_format` with no level passes; a refused PATCH leaves no `prompt_versions` row. Verifies **AC-4**.
- Call time refusal: a config whose `exercise_select` row has no level makes the turn offer the first candidate exercise with no pick request sent, and a `mani_base` row with no level makes the turn raise `config_error` with no `llm_calls` row written. Verifies **AC-5**.
- Request bodies unchanged: capture the body each of the exercise pick and the voice translation sends (same pattern as `test_the_effort_reaches_the_request_body`) and assert `reasoning.effort == "high"`, the provider order, `data_collection: deny`, and `max_completion_tokens` equal to the reply budget plus the allowance. Verifies **AC-1**, **AC-7**.
- No default: `Settings` has no `reasoning_effort` field, and calling `chain.request_body` without an effort is a `TypeError`. Verifies **AC-2**.

## Build plan

Tracer Bullet: the first slice threads one call (the voice translation) through every layer (content file, seed check, cache, call site, chain), so the whole path is proven before the other calls move onto it.

1. Add `ReasoningEffort` to `chain.py`, and `mani/prompts/calls.py` with `CALL_PROMPTS`, `effort_problem` (never raises) and `effort_for`. Derive `EXPECTED_PROMPTS` in `prompts/cache.py` from `CALL_PROMPTS` plus the layer rows. Satisfies **AC-1**, **AC-3**, **AC-4**, **AC-5**, **AC-8**.
2. Tracer slice, voice translation: add `content/prompts/voice_translation.md` (id `...013`, content moved from `_TRANSLATE_SYSTEM_PROMPT`), make `seed.py` parse and check every prompt file by frontmatter `name` before `asyncpg.connect`, and have `stt._translate_to_english` read the row through `cache.load()` inside its existing `try` and pass its level, model, budget, temperature and routing. A missing row or level logs a warning (no transcript text) and returns the untranslated transcript. Update `test_stt.py` to give `cache.load` a `Config` holding the row, in place of `settings().reasoning_effort`. Satisfies **AC-1**, **AC-3**, **AC-5**, **AC-6**, **AC-7**.
3. Exercise pick: add `content/prompts/exercise_select.md` (id `...012`, `temperature: 0.7`); `_offer_exercise` reads the row, drops its `model` and `routing` arguments, and passes the row's values and content to `client.choose_exercise`, which appends the framework name and list beneath the row's instruction. `effort_for` runs inside a `try` that catches `ServiceError`, logs, and returns `candidates[0]`. Satisfies **AC-1**, **AC-5**, **AC-6**, **AC-7**.
4. Chat turn, summary and memory fold: in `orchestrator.send`, call `effort_for` for `mani_base` once after the daily limit check and pass it to the draft and the redraft; in `summarize.py` and `memory.py`, replace `model_parameters.get("reasoning_effort")` with `effort_for`. Satisfies **AC-1**, **AC-5**.
5. Remove the fallback: drop `Settings.reasoning_effort` and `REASONING_EFFORT` from `.env.example`; make `effort` required through `chain` and `reasoning_effort` required on `client.complete` and `client.choose_exercise`. Update every call site this breaks in the tests (about 20 in `test_client.py`, the `chain.build` calls in `test_chain.py`), and remove the tests that assert the config default (`test_chain.py`, the effort default tests). Satisfies **AC-2**.
6. Admin writes: run `effort_problem` inside `config_tables.create_prompt` and `update_prompt` on the written row, in the same transaction, and refuse renaming a call row out of `CALL_PROMPTS` or setting it inactive, raising `ServiceError(INVALID_REQUEST)` so the write and its `prompt_versions` snapshot roll back. Satisfies **AC-4**.
7. Tests from *Critical test scenarios*. Reseed local, then run the whole `pytest` and confirm the integration tests ran, not skipped (`test_turn.py` now reads `exercise_select` from the database). Satisfies **AC-1** to **AC-8**.
8. Update `backend/PORT-STATUS.md`: the five calls and their rows, the removed setting, a line under "Decisions in force" (every model call names its thinking level in its own prompt row; no default), and correct the stale "A hosted project does not exist yet" line (line 14), which contradicts the hosted drift section further down. Satisfies **AC-1**, **AC-2**.

## Migration plan

**Strategy**: no schema migration; content first, then code. Local first; hosted only after hosted migrations 011 to 017 are reconciled, the same gate spec 0002 sets, because this code ships alongside 0002's and hosted's schema has drifted.
**Phases**:
0. Local: reseed, run the whole suite, done.
1. Hosted, once the gate is cleared: confirm no other row holds ids `...012` or `...013`, then seed hosted with the new content (`python scripts/seed.py` against hosted). This adds `exercise_select` and `voice_translation`; the running code ignores both. Confirm all five call rows show a level.
2. Deploy the code. Every call row is already in place, so no call fails during the switch.
3. Remove `REASONING_EFFORT` from the hosted environment (optional; it is ignored once the code ships).
**Rollback**: revert the code commit. The two extra rows are harmless to the previous code, which ignores them, and the previous code falls back to `REASONING_EFFORT` again, so keep that variable set until the deploy has proven itself.
**Risks**: seeding hosted overwrites every authored prompt and every framework row with the repo's version, including any portal edit made there since the last seed; check hosted's `admin.prompts` and `admin.frameworks` `updated_at` and `updated_by` before seeding. The seed does not rewrite `routing` or `is_active` on an existing row, so a hosted row deactivated or given custom routing keeps it; `data_collection` deny still holds because `settings.routing` applies it under any row routing that does not override it. If the deploy goes out before the seed, the exercise pick falls back to the first candidate exercise and voice input stays untranslated until the seed runs (both logged, and no turn fails).

## Consequences

**Positive**:
- Every call's level is visible in one place per call, and recorded in `prompt_versions` when changed through the portal, which is what feature 11 needs to tune and compare.
- No path can send a call at a level nobody chose.
- Two more pieces of model facing text leave Python, ahead of feature 8.

**Negative / tradeoffs**:
- A call row without a level now fails its call instead of running at a default. A chat turn on a broken `mani_base` row returns 500 until someone reseeds or fixes the row.
- `CALL_PROMPTS` must be updated whenever a new model call is added; forgetting it lets that row skip the seed and admin checks (the call time check and the required `chain` argument still catch it).
- Hosted must be seeded before the deploy, and seeding overwrites portal edits to prompts and frameworks.
- The portal can no longer switch a call off by deactivating its row (for example, pausing memory folding). Doing that now takes a code change.
- Voice translation and the exercise pick stay on `high`, which is likely more than these small tasks need, until feature 11 measures them.

**Neutral**:
- `model_id` stays optional on call rows and still falls back to `DEFAULT_CHAT_MODEL` / `DEFAULT_SUMMARY_MODEL`.
- The voice translation now reads the prompt cache, so it touches the database through the admin pool on a cold cache.

## Follow-up

- [ ] Build after spec 0002's work on `chain.py`, `client.py` and `llm_calls.py` is committed; both specs change the same signatures.
- [ ] Hosted rollout waits on the reconciliation of hosted migrations 011 to 017 (already open in `PORT-STATUS.md`, and the same gate as spec 0002).
- [x] Update the scope line for feature 2: the calls are chat turn, summary, memory fold, exercise pick and voice translation (title is not a call).
- [ ] Decide separately whether `model_id` should become required on call rows and the two model defaults go away (out of scope here by choice).
- [ ] Feature 11: tune each call's level from measured numbers, starting with voice translation and the exercise pick.
