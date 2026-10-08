# 0004. Require a thinking level on every model call: decision record

The build spec is [index.md](index.md).

## Context

> ⚠️ Premise note: the scope line lists five calls ("chat, summary, memory fold, title and the exercise pick"), but the title is not a call. `title_generation` is text added to the chat turn's system prompt, so it already runs at the chat turn's level. The real list is also one longer than the scope says: on `origin/main`, commit `9be3b38` routes the voice translation through `chain.request_body`, so it is a model call too, and it has no row. The spec covers the five real calls: chat turn (with its redrafts), summary, memory fold, exercise pick and voice translation.

This spec builds on `9be3b38` (`chain.request_body`, `chain.sampling`, the voice translation call, and a test asserting that prompts on reasoning models carry an effort), which `feat/turn-cost-baseline` already contains. That branch also carries spec 0002's uncommitted edits to `chain.py`, `client.py` and `llm_calls.py`, which touch the same signatures this spec changes.

A reasoning model (here `openai/gpt-6-luna`, served by Azure first through OpenRouter) takes no temperature. It reads a reasoning effort instead, and that effort is the single biggest lever on a call's cost and latency: measured on 2026-10-07, `high` spent 26 reasoning tokens where `low` spent 0, about three times the cost of the same call, and one chat turn at `high` thought for 1,955 of its 2,048 output tokens. Today three calls (`mani_base`, `summarization`, `memory_fold`) name their effort in `admin.prompts.model_parameters.reasoning_effort`. Two calls name none: the exercise pick (`client.choose_exercise`) and the voice translation (`stt._translate_to_english`). Both silently fall back to `Settings.reasoning_effort`, read from `REASONING_EFFORT`. The prompt rows fall back to it too whenever their `reasoning_effort` key is missing, and nothing stops a row from losing it: `scripts/seed.py` accepts any `model_parameters`, and `PATCH /admin/prompts/{id}` replaces `model_parameters` wholesale.

The scope's direction is that each call's level is a deliberate, measured choice (feature 11 tunes them from the baseline in spec 0002). A silent fallback defeats that: a row edited in the portal, or a hosted database seeded from older content, keeps running on whatever the environment says, and nobody can tell from the row what a call actually costs. Hosted also runs real traffic and has a schema that has drifted from local (see spec 0002), so the change has to land without a window where calls fail.

The conversations are special category health data. The voice translation carries what someone said, so its routing must stay the same as every other call: Azure first, OpenAI behind it, `data_collection` deny.

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

## Rationale

The scope wants each call's level to be a measured choice that feature 11 can change and compare, three runs before and three after. That only works if the level lives somewhere a reseed or a portal edit can change it and the rest of the system cannot quietly override. Rows already hold the level for three of five calls, and a portal edit snapshots it in `admin.prompt_versions`, so extending the same home to the last two calls is the smallest change that makes the rule uniform. Option 3 would turn every tuning step into a deploy, and Option 2 keeps the exact fallback the scope says to remove.

Refusing at three points is what makes "no silent fallback" true rather than mostly true. Seed covers authored content, the admin check covers the portal (which replaces `model_parameters` wholesale, so one careless save drops the level), and the call time check covers rows already in a database, such as a hosted database seeded from older content. Failing only the affected call, as a config error before any request goes out, keeps the blast radius small: a broken `memory_fold` row stops memory folding, not every chat turn, and no tokens are spent finding out.

Keeping both new rows on `high` follows the journal lesson "measure before tuning prompts". This spec is a refactor of where the level lives; changing what the level is belongs to feature 11, where the baseline from spec 0002 can show the effect. Option 4's database constraint is stronger, but it costs a migration on two databases that have drifted apart, for a rule that has exactly two writers (seed and the admin routes), both of which this spec guards.
