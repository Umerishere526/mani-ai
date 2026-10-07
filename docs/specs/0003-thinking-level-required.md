# 0003. Require a thinking level on every model call

**Date**: 2026-10-07
**Status**: Proposed

## Summary

Every model call the backend makes will name its own thinking level (how hard a reasoning model thinks before it answers, billed as output tokens) in its own prompt row. The config default `REASONING_EFFORT` goes away, so no call runs on a level nobody chose. The exercise pick and the voice translation get their own prompt rows, since they are the two calls that have none today. A missing or unknown level is refused when seeding, when an admin edits a prompt, and right before a call goes out. Every call stays on `high`, so nothing changes in what the model is asked or what it costs; feature 11 tunes the levels from measurements.

## Context

> ⚠️ Premise note: the scope line lists five calls ("chat, summary, memory fold, title and the exercise pick"), but the title is not a call. `title_generation` is text added to the chat turn's system prompt, so it already runs at the chat turn's level. The real list is also one longer than the scope says: on `origin/main`, commit `9be3b38` routes the voice translation through `chain.request_body`, so it is a model call too, and it has no row. The spec covers the five real calls: chat turn (with its redrafts), summary, memory fold, exercise pick and voice translation.

This branch (`fix/chat-tester-work`) is 4 commits behind `origin/main`, and `9be3b38` changes the code this spec builds on (`chain.request_body`, `chain.sampling`, the voice translation call, and a test asserting that prompts on reasoning models carry an effort). Everything below assumes `origin/main`.

A reasoning model (here `openai/gpt-6-luna`, served by Azure first through OpenRouter) takes no temperature. It reads a reasoning effort instead, and that effort is the single biggest lever on a call's cost and latency: measured on 2026-10-07, `high` spent 26 reasoning tokens where `low` spent 0, about three times the cost of the same call, and one chat turn at `high` thought for 1,955 of its 2,048 output tokens. Today three calls (`mani_base`, `summarization`, `memory_fold`) name their effort in `admin.prompts.model_parameters.reasoning_effort`. Two calls name none: the exercise pick (`client.choose_exercise`) and the voice translation (`stt._translate_to_english`). Both silently fall back to `Settings.reasoning_effort`, read from `REASONING_EFFORT`. The prompt rows fall back to it too whenever their `reasoning_effort` key is missing, and nothing stops a row from losing it: `scripts/seed.py` accepts any `model_parameters`, and `PATCH /admin/prompts/{id}` replaces `model_parameters` wholesale.

The scope's direction is that each call's level is a deliberate, measured choice (feature 11 tunes them from the baseline in spec 0002). A silent fallback defeats that: a row edited in the portal, or a hosted database seeded from older content, keeps running on whatever the environment says, and nobody can tell from the row what a call actually costs. Hosted also runs real traffic and has a schema that has drifted from local (see spec 0002), so the change has to land without a window where calls fail.

The conversations are special category health data. The voice translation carries what someone said, so its routing must stay the same as every other call: Azure first, OpenAI behind it, `data_collection` deny.

## Requirements

**User stories**:
- As muhammad, I want every model call to name its own thinking level in its prompt row, so that the cost and latency of each call is a choice I can see and tune, not an environment default.
- As muhammad, I want a missing or wrong level to be refused where it is written, so that a portal edit or a stale seed cannot quietly change what a call costs.

**Acceptance criteria**:
- **AC-1**: Each of the five model calls reads its thinking level from its own active prompt row's `model_parameters.reasoning_effort` and sends it to models that read one: chat turn and its redrafts from `mani_base`, summary from `summarization`, memory fold from `memory_fold`, exercise pick from `exercise_select`, voice translation from `voice_translation`. No call reads a level from anywhere else.
- **AC-2**: `Settings` has no `reasoning_effort` field, `.env.example` has no `REASONING_EFFORT`, and `chain` has no default level to fall back to. A leftover `REASONING_EFFORT` in someone's `.env` is ignored and changes nothing.
- **AC-3**: `python scripts/seed.py` stops with an error naming the file, and writes nothing, when any call prompt (a name in `CALL_PROMPTS`) has no `reasoning_effort` or one outside `low`, `medium`, `high`, `xhigh`, `max`, whatever its `model_id`. It also stops when a name in `CALL_PROMPTS` has no file in `content/prompts/`. Layer prompts (`response_format`, `title_generation`) and `somatic.md` need no level.
- **AC-4**: `POST /admin/prompts` and `PATCH /admin/prompts/{id}` refuse, with the standard `invalid_request` error (422) and no change saved, any write after which a row named in `CALL_PROMPTS` has no valid level. The check runs on the row as it would be after the edit, so replacing `model_parameters` without the level, or renaming a layer row to a call name, is refused. Edits to layer rows, and edits to a call row that keep a valid level, pass as today.
- **AC-5**: At call time, a call whose row is missing, inactive, or has no valid level raises a `config_error` before any request reaches OpenRouter, so no tokens are spent and no `admin.llm_calls` row is written for it. Each call then fails along its existing path: the chat turn returns 500 `config_error` in the standard error shape and reaches Sentry; the summary logs and keeps the existing summary; the memory fold raises as it does today for a missing row; the exercise pick logs and falls back to the plain library offer; the voice translation logs and returns the untranslated transcript.
- **AC-6**: `content/prompts/exercise_select.md` and `content/prompts/voice_translation.md` exist and are seeded. The exercise row holds a fixed instruction, and the code appends the framework name and the exercise list beneath it, so no row edit can break the call's formatting. The translation row holds today's translation instruction word for word. Neither instruction remains as a Python constant.
- **AC-7**: The change alters no request a call sends. Each of the five calls goes out with the same model, effort (`high`), output budget (`chain.sampling`) and provider routing as before: the exercise pick keeps a reply budget of 200 tokens and the translation 500, and both keep routing Azure first with `data_collection` deny.
- **AC-8**: When the prompt cache loads and `exercise_select` or `voice_translation` is missing or inactive, it logs a warning naming them, as it already does for `title_generation` and `summarization`.

## Options considered

### Option 1: Required level in every call's own row, one shared check

Every call gets a prompt row, a named set `CALL_PROMPTS` in code says which rows are calls, and one function checks a row's level. Seed, the admin routes, and the call itself all use that function. The config default is deleted.

**Pros**:
- Every call's level is visible and editable in one place, the same way for all five.
- No path can write or send a call without a level, so the scope's "no silent fallback" holds everywhere, not only at seed time.
- No migration: `model_parameters` already exists on `admin.prompts` and `admin.prompt_versions`.

**Cons**:
- Two new rows to author and seed, and hosted must be seeded before the deploy.
- A call row missing its level now fails that call instead of running at a default. Mitigated by the seed and admin checks, but it is a new way for a call to fail.
- `CALL_PROMPTS` is a list in code that must grow with every new call.

### Option 2: Keep the config default, warn when it is used

Leave `REASONING_EFFORT` as the fallback and log a warning whenever a call uses it. Add the effort to the two calls' code paths as constants.

**Pros**:
- Smallest change, and no call can fail for want of a level.
- No new rows and no rollout ordering.

**Cons**:
- The fallback the scope asks to remove stays, so a portal edit still changes a call's cost silently; a warning in the logs is not a refusal.
- Two calls keep their level in Python, against the scope's "nothing hardcoded" slice.

### Option 3: A map from call purpose to level in code

`chain.py` holds `{CHAT: "high", SUMMARY: "high", ...}` keyed by `llm_calls.Purpose`, and the prompt rows stop carrying an effort.

**Pros**:
- One place, typed, impossible to leave out at a call site.
- No new rows.

**Cons**:
- Every tuning step in feature 11 becomes a code change and a deploy instead of a reseed or a portal edit.
- It splits a call's configuration across two homes: model in the row, level in code.

### Option 4: A `kind` column on `admin.prompts`

A migration adds `kind` (`call` or `layer`) and a check constraint requiring `model_parameters ? 'reasoning_effort'` when `kind = 'call'`, so Postgres itself refuses a row without a level.

**Pros**:
- The database enforces the rule for every writer, including ad hoc SQL.
- The portal can show which rows are calls.

**Cons**:
- A schema change on two databases that have already drifted (spec 0002), with the backfill and constraint sequence a running system needs.
- A check constraint cannot easily validate the allowed values against a list the code owns, so the app check is needed anyway.

## Decision

**Chosen option**: Option 1: Required level in every call's own row, one shared check

Every model call reads a required thinking level from its own prompt row; `CALL_PROMPTS` names the call rows, and one check guards seed, the admin routes, and the call itself.

Settled in design (muhammad's picks): own seeded rows for the exercise pick and the voice translation; required on every call row whatever the model; refused at seed, admin edit and call time; a missing level fails only that call, as a config error; call rows named by a set in code; the exercise row holds a fixed instruction with the facts appended; allowed values stay `low` to `max`; both new rows start on `high`; `model_id` stays optional (out of scope); hosted is seeded before the deploy; no References section.

Decided at write time:
- **Where the check lives**: a small module `backend/mani/prompts/calls.py` holding `CALL_PROMPTS` and `effort_problem(name, model_parameters) -> str | None` (returns why a row is not acceptable, or `None`). The allowed values become `ReasoningEffort = Literal["low", "medium", "high", "xhigh", "max"]` in `backend/mani/llm/chain.py`, which `calls.py` imports, so `chain` never depends on `prompts`. Runner up: putting it all in `chain.py`, rejected because which row names are calls is a prompt concern, not a request concern.
- **How chain refuses**: `chain._reasoning`, `request_body`, `build` and `build_tool_choice` take `effort: ReasoningEffort` as a required argument with no default, and `client.complete` and `client.choose_exercise` take `reasoning_effort` as required. A forgotten call site is then a type and test failure, not a runtime surprise. The `config_error` itself is raised where the row is read (the call site), through one helper `calls.effort_for(prompt, name) -> ReasoningEffort` that raises `ServiceError(CONFIG_ERROR)`. Runner up: raising inside `chain`, rejected because `chain` does not know which row a call came from and could not name it in the error.
- **Seed validates before writing**: parse and check every prompt file first, then open the write. The seed already runs in one transaction, so a late failure would roll back too, but checking first gives one clear error and no half run.
- **Exercise pick reads its own row**: model, temperature, `maxTokens` and routing come from `exercise_select`, with today's values as the row's values, rather than being passed down from the chat turn's row. This keeps "a call's configuration lives in its row" true for all five calls.

## Rationale

The scope wants each call's level to be a measured choice that feature 11 can change and compare, three runs before and three after. That only works if the level lives somewhere a reseed or a portal edit can change it and the rest of the system cannot quietly override. Rows already hold the level for three of five calls and already snapshot it in `admin.prompt_versions`, so extending the same home to the last two calls is the smallest change that makes the rule uniform. Option 3 would turn every tuning step into a deploy, and Option 2 keeps the exact fallback the scope says to remove.

Refusing at three points is what makes "no silent fallback" true rather than mostly true. Seed covers authored content, the admin check covers the portal (which replaces `model_parameters` wholesale, so one careless save drops the level), and the call time check covers rows already in a database, such as a hosted database seeded from older content. Failing only the affected call, as a config error before any request goes out, keeps the blast radius small: a broken `memory_fold` row stops memory folding, not every chat turn, and no tokens are spent finding out.

Keeping both new rows on `high` follows the journal lesson "measure before tuning prompts". This spec is a refactor of where the level lives; changing what the level is belongs to feature 11, where the baseline from spec 0002 can show the effect. Option 4's database constraint is stronger, but it costs a migration on two databases that have drifted apart, for a rule that has exactly two writers (seed and the admin routes), both of which this spec guards.

## Feature design

**Data model sketch**: no schema change. Two new rows in the existing `admin.prompts` table, written by `scripts/seed.py`:

| Row `name` | `model_id` | `model_parameters` | `content` |
|---|---|---|---|
| `exercise_select` | `openai/gpt-6-luna` | `{"maxTokens": 200, "reasoning_effort": "high"}` | fixed instruction: the person just completed a framework; call `start_exercise` with the id from the list below that best fits what they worked through |
| `voice_translation` | `openai/gpt-6-luna` | `{"maxTokens": 500, "temperature": 0, "reasoning_effort": "high"}` | today's `_TRANSLATE_SYSTEM_PROMPT`, word for word |

Each needs a fixed `id` in its frontmatter, following the existing `10000000-0000-0000-0000-0000000000NN` pattern (next free numbers). `admin.prompt_versions` snapshots `model_parameters` already, so every level change is recorded with no extra work.

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
| `orchestrator` exercise pick | reads the `exercise_select` row from the loaded config and passes its values |
| `calls.effort_for(prompt, name)` | new; returns the row's level or raises `ServiceError(CONFIG_ERROR)` |
| `calls.effort_problem(name, model_parameters)` | new; shared by seed and the admin routes |

**Value sourcing**:

| Action | Value produced / sent | Source |
|---|---|---|
| Chat turn and redrafts | reasoning effort | `mani_base` row `model_parameters.reasoning_effort` |
| Summary | reasoning effort | `summarization` row `model_parameters.reasoning_effort` |
| Memory fold | reasoning effort | `memory_fold` row `model_parameters.reasoning_effort` |
| Exercise pick | reasoning effort, model, reply budget, temperature, routing | `exercise_select` row (`model_parameters.reasoning_effort`, `model_id or settings.default_chat_model`, `maxTokens` with 200 as the code default, `temperature`, `routing`) |
| Exercise pick | instruction text | `exercise_select` row `content` |
| Exercise pick | framework name and exercise list | appended by code from `config.registry` and `exercises_db`, as today |
| Voice translation | reasoning effort, model, reply budget, temperature, routing | `voice_translation` row (`model_parameters.reasoning_effort`, `model_id or settings.default_chat_model`, `maxTokens` with 500 as the code default, `temperature` with 0 as the code default, `routing`) |
| Voice translation | instruction text | `voice_translation` row `content` |
| Seed and admin check | which rows are calls | `CALL_PROMPTS` in `mani/prompts/calls.py` |
| Seed and admin check | allowed levels | `ReasoningEffort` in `mani/llm/chain.py` |
| Admin PATCH check | the row after the edit | the stored row merged with the request's non null fields |
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
- Admin check on the merged row: replacing a call row's `model_parameters` without the level is refused; renaming a layer row to `memory_fold` without a level is refused; a content only edit to a valid call row passes; an edit to `response_format` with no level passes. Verifies **AC-4**.
- Call time refusal: a config whose `exercise_select` row has no level makes the exercise pick return `None` with no request sent, and a `mani_base` row with no level makes the turn raise `config_error` with no `llm_calls` row written. Verifies **AC-5**.
- Request bodies unchanged: capture the body each of the exercise pick and the voice translation sends (same pattern as `test_the_effort_reaches_the_request_body`) and assert `reasoning.effort == "high"`, the provider order, `data_collection: deny`, and `max_completion_tokens` equal to the reply budget plus the allowance. Verifies **AC-1**, **AC-7**.
- No default: `Settings` has no `reasoning_effort` field, and calling `chain.request_body` without an effort is a `TypeError`. Verifies **AC-2**.

## Build plan

Tracer Bullet: the first slice threads one call (the voice translation) through every layer (content file, seed check, cache, call site, chain), so the whole path is proven before the other calls move onto it. Start from an up to date branch: pull `origin/main` first.

1. Add `ReasoningEffort` to `chain.py`, and `mani/prompts/calls.py` with `CALL_PROMPTS`, `effort_problem` and `effort_for`. Satisfies **AC-1**, **AC-3**, **AC-4**, **AC-5**.
2. Tracer slice, voice translation: add `content/prompts/voice_translation.md` (content moved from `_TRANSLATE_SYSTEM_PROMPT`), make `seed.py` parse and check every prompt file before writing, and have `stt._translate_to_english` read the row from `cache.load()` and pass its level, model, budget, temperature and routing. A missing row or level is logged and returns the untranslated transcript. Satisfies **AC-1**, **AC-3**, **AC-5**, **AC-6**, **AC-7**.
3. Exercise pick: add `content/prompts/exercise_select.md`, have the orchestrator read the row and pass its values and content to `client.choose_exercise`, which appends the framework name and list beneath the row's instruction. A missing row or level logs and returns `None` (the plain library offer). Satisfies **AC-1**, **AC-5**, **AC-6**, **AC-7**.
4. Chat turn, summary and memory fold: replace `parameters.get("reasoning_effort")` with `calls.effort_for(...)` at each call site, so a missing level raises before the request. Satisfies **AC-1**, **AC-5**.
5. Remove the fallback: drop `Settings.reasoning_effort` and `REASONING_EFFORT` from `.env.example`; make `effort` required through `chain` and `client`. Satisfies **AC-2**.
6. Admin routes: run `effort_problem` on the row as it would be after `create_prompt` and `update_prompt`, raising `invalid_request` before the write. Satisfies **AC-4**.
7. Add `exercise_select` and `voice_translation` to `EXPECTED_PROMPTS` in `prompts/cache.py`. Satisfies **AC-8**.
8. Tests from *Critical test scenarios*; remove tests that assert the config default. Run the whole `pytest` and confirm the integration tests ran, not skipped, against a reseeded local database. Satisfies **AC-1** to **AC-8**.
9. Update `backend/PORT-STATUS.md`: the five calls and their rows, the removed setting, and a line under "Decisions in force" (every model call names its thinking level in its own prompt row; no default). Satisfies **AC-1**, **AC-2**.

## Migration plan

**Strategy**: no schema migration; content first, then code.
**Phases**:
1. Seed hosted with the new content (`python scripts/seed.py` against hosted). This adds `exercise_select` and `voice_translation`; the running code ignores both. Confirm all five call rows show a level.
2. Deploy the code. Every call row is already in place, so no call fails during the switch.
3. Remove `REASONING_EFFORT` from the hosted environment (optional; it is ignored once the code ships).
**Rollback**: revert the code commit. The two extra rows are harmless to the previous code, which ignores them, and the previous code falls back to `REASONING_EFFORT` again, so keep that variable set until the deploy has proven itself.
**Risks**: seeding hosted overwrites every authored prompt with the repo's version, including any portal edit made there since the last seed; check hosted's `admin.prompts.updated_at` and `updated_by` before seeding. If the deploy goes out before the seed, the exercise pick falls back to the library offer and voice input stays untranslated until the seed runs (both logged, and no turn fails).

## Consequences

**Positive**:
- Every call's level is visible in one place per call and recorded in `prompt_versions` whenever it changes, which is what feature 11 needs to tune and compare.
- No path can send a call at a level nobody chose.
- Two more pieces of model facing text leave Python, ahead of feature 8.

**Negative / tradeoffs**:
- A call row without a level now fails its call instead of running at a default. A chat turn on a broken `mani_base` row returns 500 until someone reseeds or fixes the row.
- `CALL_PROMPTS` must be updated whenever a new model call is added; forgetting it lets that row skip the seed and admin checks (the call time check and the required `chain` argument still catch it).
- Hosted must be seeded before the deploy, and seeding overwrites portal edits.
- Voice translation and the exercise pick stay on `high`, which is likely more than these small tasks need, until feature 11 measures them.

**Neutral**:
- `model_id` stays optional on call rows and still falls back to `DEFAULT_CHAT_MODEL` / `DEFAULT_SUMMARY_MODEL`.
- The voice translation now reads the prompt cache, so it touches the database through the admin pool on a cold cache.

## Follow-up

- [ ] Pull `origin/main` before building; this spec assumes `9be3b38` is present.
- [ ] Update the scope line for feature 2: the calls are chat turn, summary, memory fold, exercise pick and voice translation (title is not a call).
- [ ] Decide separately whether `model_id` should become required on call rows and the two model defaults go away (out of scope here by choice).
- [ ] Feature 11: tune each call's level from measured numbers, starting with voice translation and the exercise pick.
