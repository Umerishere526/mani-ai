# 0014. Remove what nothing reads or runs

**Date**: 2026-10-08
**Status**: In Progress
**Decision record**: [rationale.md](rationale.md) (context, options considered, rationale, and the full inventory with its evidence and muhammad's marks)

## Summary

An audit of the backend, the chat tester and the docs found code, columns, grants, packages, tests and documents that nothing reads or runs. muhammad marked every item keep or delete. This spec removes what was marked delete, fixes the stale statements, and leaves guardrails, crisis handling and audit records alone. Nothing a person sees changes, and the API schema stays the same. The build is a deletion pass that shrinks the code, the database schema and the deployed image.

## Requirements

**User stories**:
- As muhammad, I want every line of code, column and grant to have a reader, so the next change does not have to work out whether a dead path matters.
- As whoever reads the docs next, I want every file, command and column they name to exist, so they do not chase things that are gone.
- As the person talking to Mani, I notice nothing: the same replies, the same safety behaviour.

**Acceptance criteria** (item ids such as A1 refer to the inventory in [rationale.md](rationale.md)):

- **AC-1**: The Python items marked delete are gone, along with every test line that used them:
  - A1 `summary_snapshot` in `mani/chat/orchestrator.py`.
  - A2 `get_prompt` in `mani/db/config_tables.py`. The admin route `get_prompt` in `mani/routers/admin.py` stays.
  - A3 the `SystemPrompt.length` property in `mani/prompts/composer.py`.
  - A4 and B3: `Call.model`, `Call.usage` and `Call.latency_ms` in `mani/llm/client.py`, and the three values in the `Call(...)` at the end of `complete`. `Call` keeps `value` and `call_id`, and its docstring says "A completed model call: what came back, and the id of its record." Production reads only `.value` and `.call_id` (orchestrator.py, summarize.py, memory.py). The five fakes that build `Call` stop passing those three: `tests/integration/test_memory.py` near lines 40 and 238, `test_turn.py` near lines 59 and 1369, and `test_account_lifecycle.py` near line 62. The fake in `test_memory.py` near line 292 records `usage=llm_calls.Usage()` instead of `call.usage`.
  - A5 `Thread.deleted_at` and A6 `Framework.activation_conditions` in `mani/models/rows.py`, and their names in the column lists in `mani/db/threads.py` and `mani/db/config_tables.py`. The `deleted_at is null` filters in SQL stay.
  - A7 the unused `Any` import in `mani/db/threads.py`.
  - B1 `spend_since` in `mani/db/llm_calls.py`, and the whole test `test_a_model_call_is_recorded_with_its_cost` in `tests/integration/test_queries.py` (near lines 313 to 325), whose only assertions use it. The next test there still covers `record`.
  - B2 `Claims.email` in `mani/auth/jwt.py`: the field near line 30 and the assignment near line 104. Also its assertion in `tests/unit/test_auth.py` near line 41.
  - C2 the `message_id` parameter of `llm_calls.record`, since the link is written later by `attach_message`. The INSERT stops naming `message_id`, its placeholders are renumbered, and the column defaults to null as it does today.
  - C3 the `limit` parameter of `summarize.reconcile_due`. Its default becomes a module constant `RECONCILE_BATCH = 200` in `mani/summarize.py`. The fake `due_for_summary` in `tests/unit/test_summarize.py` keeps its own `limit` parameter.

  A grep for each removed name over `backend/mani`, `backend/main.py`, `backend/scripts` and `backend/tests` finds only unrelated names of the same spelling.
- **AC-2**: `db_pool_min_size` and `db_pool_max_size` are gone from `mani/config.py`. `mani/db/pool.py` keeps `MIN_POOL_SIZE = 2` and `MAX_POOL_SIZE = 10`. The comment that explains the connection ceiling (instances times pool max against the Supabase session pooler) moves from `config.py` to sit above those two constants. It names the constants, not the settings, and says the values 2 and 10 are a hedge, not a measured guarantee.
- **AC-3**: These statements are corrected, and none of them changes code:
  - The `_handle_crisis` docstring in `mani/chat/orchestrator.py`, which says it is "called from two places". It has one caller.
  - Both `ABOUTME` lines of `mani/db/llm_calls.py`. The first says each record holds "which prompt version produced it". The second ("Nothing here existed before") is history, and it becomes what the file does: records each model call's cost and outcome, and links it to the reply it produced.
  - The `attach_message` docstring in `mani/db/llm_calls.py`, which says the link answers "which prompt version wrote a particular reply". It says the link answers which call, model and cost produced a reply.
  - The comment in `mani/db/threads.py` near line 285, which says the column grant covers `last_message_at`. After AC-8 it covers `title` and `deleted_at`.
  - The `rows.py` comment near lines 158 to 160 about `stages` and `activation_conditions`. It goes with the fields.
  - In `scripts/seed.py`, the "read by nothing" comments near lines 181 and 190. They go with the keys.
- **AC-4**: In `backend/requirements.txt`, `email-validator` is removed and `langchain==1.4.1` is replaced by `langchain-core==1.6.6`, which is what `mani/llm/chain.py` imports. The comment saying LangSmith arrives with langchain and stays off now names `langchain-core`, which is what brings LangSmith in. A fresh venv built only from `requirements.txt` and `requirements-dev.txt` imports `main` and passes the whole `pytest`. `pip show langgraph` in it finds nothing.
- **AC-5**: Migration `022_drop_threads_vague_streak.sql` drops `public.threads.vague_streak` and its check constraint `threads_vague_streak_sane`. The column grant to `mani_service` goes with the column. The two `vague_streak` assertions in `tests/sql/test_grants.sql` (near lines 92 to 98, including their comment) are removed. The `conversation_style` assertion stays.
- **AC-6**: Migration `023_drop_unused_framework_columns.sql` drops `admin.frameworks.stages` with its constraint `frameworks_stages_is_an_object`, and `admin.frameworks.activation_conditions`. In the same slice, three things change:
  - The `Framework` model in `mani/models/rows.py` loses both fields (`stages` near line 162, `activation_conditions` from AC-1).
  - `FRAMEWORK_COLUMNS` in `mani/db/config_tables.py` (near lines 25 to 28) loses both names. Otherwise every config load (`prompts/cache.py:92`), and so every turn, fails with "column does not exist".
  - `scripts/seed.py` no longer builds either value. Its upsert (near lines 209 to 232) loses both columns, with the placeholders renumbered. It still refuses a `stages:` frontmatter key.

  In `tests/unit/test_seed_frameworks.py`, the assertions on `parsed["activation_conditions"]` and `parsed["stages"]` (near lines 45, 46 and 54) are removed. The test name near line 42 drops "and starts when as the activation text". The refusal case near line 100 stays.
- **AC-7**: Migration `024_drop_llm_calls_prompt_version.sql` drops `admin.llm_calls.prompt_version_id` and the index `idx_llm_calls_prompt_version`. The `prompt_version_id` parameter is gone from `complete`, `choose_exercise` and `_record` in `mani/llm/client.py`, from `llm_calls.record`, from the call in `mani/chat/orchestrator.py` near line 395, and from `tests/integration/test_memory.py` near line 293.
- **AC-8**: Migration `025_revoke_unused_grants.sql` revokes, each with a one line comment saying no code path uses it:
  - DELETE on `public.thread_technique_state` from `mani_service`, and the policy `technique_state_delete`. A finished technique is retired with an UPDATE.
  - DELETE on `public.threads` from `authenticated`, and the policy `threads_delete`. Threads are soft deleted with an UPDATE of `deleted_at`.
  - DELETE on `public.thread_techniques_offered` from `authenticated`. It has no DELETE policy, so the migration uses `drop policy if exists` for safety.
  - UPDATE on `public.exercise_completions` from `authenticated`, and the policy `completions_update`. Completions are only inserted.
  - Column UPDATE `(last_message_at)` on `public.threads` from `authenticated`. Its only writer is the trigger `sync_thread_message_count`. That trigger is not security definer, but it only fires on inserts into `messages`, which happen inside `create_message_pair` and `create_greeting` (running as their owner) or in the account cascade (as `supabase_auth_admin`, which holds its own grant from migration 005). The column grants on `title` and `deleted_at` stay.
  - SELECT on `admin.frameworks` from `authenticated`. Frameworks load on the admin connection. SELECT on `admin.exercises` stays.
  - The policy `messages_delete` (001:441). It has no DELETE grant behind it, so it permits nothing today. Dropping it means a future grant needs a policy chosen on purpose.

  `mani_service` inherits from `authenticated`, so every revoke from `authenticated` also leaves `mani_service` without it. Two test files change:
  - `tests/sql/test_grants.sql`. The assertion "the backend can clear technique state" and the block that requires a DELETE policy on `thread_technique_state` (near lines 192 to 241) become assertions that `mani_service` holds no DELETE on it and that no DELETE policy exists. New assertions check that neither `authenticated` nor `mani_service` holds any other revoked privilege, and that `authenticated` still holds column UPDATE on `threads.deleted_at` and `threads.title`. "A user cannot delete technique state directly" stays. The comment near line 147 that calls the framework registry shared content is rewritten.
  - `tests/sql/test_rls.sql`. The block "Finishing a technique clears its row, for the owner only" (near lines 330 to 362) deletes technique state as `mani_service`. It becomes an assertion that this DELETE raises `insufficient_privilege`. Otherwise `test_db.sh` stops at it (`ON_ERROR_STOP`).

  Deleting an account still removes all of its rows: `tests/integration/test_account_lifecycle.py` and `tests/integration/test_account_deletion_cascade.py` pass and are not skipped.
- **AC-9**: The `type:` and `provider:` frontmatter lines are gone from all 10 files in `backend/content/prompts/`. After `python scripts/seed.py`, every `admin.prompts` row has the same `content`, `model_id` and `model_parameters` as before the edit.
- **AC-10**: Tests, scripts and the chat tester:
  - Removed: `TONES` in `tests/unit/test_chat_context.py` near line 292. `check_capsules` and `MAX_CAPSULES` in `tests/evals/validators.py`. `SELF_JUDGMENTS` and `MAX_CAPSULE_WORDS` in `tests/evals/vocabulary.py`, with their imports. The four `check_capsules` tests in `tests/evals/test_negative_set.py` near lines 212 to 238. `ManiClient.list_messages` and `ManiClient.set_conversation_style` in `chat-tester/client.py`.
  - Fixed: `test_after_keep_chatting_...` near line 532 of `test_chat_context.py` is named after "I want to keep talking". The `tests/__init__.py` docstring names unit, evals, integration and sql. The `tests/conftest.py` comment that says the fallback names no database matches the fallback it sits above. The root `.gitignore` entry `chat-tester/.venv/` reads `chat-tester/venv/`. The `ABOUTME` of `scripts/eval_conversations.yaml` no longer says turns come from the framework files' worked examples. `backend/.env.example` lists `CRON_SECRET`.
- **AC-11**: Every stale statement listed in group G of [rationale.md](rationale.md) is corrected in place, in these files: `.claude/BACKEND.md`, `.claude/SUPABASE.md`, `backend/PORT-STATUS.md`, `backend/docs/database-schema-reference.md`, `backend/docs/specs/README.md`, `backend/docs/specs/conversational-styles.md` and `chat-tester/README.md`. `backend/docs/database-schema-reference.md` also describes the schema after migrations 020 to 025. The `mani_service` privilege list in `.claude/SUPABASE.md` loses `DELETE on thread_technique_state` and `threads.vague_streak`. Beyond the listed lines, a grep for every removed name and dropped grant in group A to E (`spend_since`, `db_pool_`, `vague_streak`, `activation_conditions`, `stages` as a column, `prompt_version_id`, `email-validator`, `langchain==`, `summary_snapshot`, `check_capsules`) across `*.md` outside `docs/specs/` and `mani-vault/`, and across comments in `backend/`, finds no statement that is now false. `backend/docs/ai-layer-audit.md` is deleted, and so is its line in `.claude/BACKEND.md`. Migration 001's own comments are not edited, because migrations are forward only.
- **AC-12**: `backend/.eval/client_style/` and the two `.log` files in `backend/.eval/` are deleted, and `backend/.eval/safety_flag/` is kept. `.obsidian/workspace.json` is removed from git with `git rm --cached` and added to the root `.gitignore`; the file stays on disk.
- **AC-13**: Every item marked keep is unchanged. That covers the guardrails (`safety.CLARIFICATION`, `Assessment.matched`, the crisis code and `crisis_events` columns, `backend/.eval/safety_flag/`), the audit columns (`llm_calls.model`, `error_message` and `message_id` with `attach_message`, `prompts.created_by/updated_by`, `prompt_versions.created_by`, every `created_at`/`updated_at` and its trigger), and `skills-lock.json` and `.agents/skills/`. The OpenAPI schema (`main.app.openapi()`, dumped with sorted keys) is byte for byte the same before and after the build.
- **AC-14**: The build passes on a reset local database: `supabase db reset`, then `python scripts/seed.py`, `python scripts/seed_exercises.py`, `./scripts/test_db.sh --local`, and the whole `pytest` with pristine output. The passed and skipped counts are recorded before and after, and the integration tests are not skipped. The passed count drops by exactly 5 (the four `check_capsules` tests and the `spend_since` test), and the skipped count is unchanged. No real model conversation is run.
- **AC-15**: In the same change, `backend/PORT-STATUS.md` is edited in place:
  - Decisions in force gains one line: "Code, columns, grants and packages nothing reads are removed, not kept in case; write only audit records stay because a person reads them (spec 0014)."
  - The migration count reads 18.

  A journal note in `mani-vault/Journal/` records the before and after test counts, that `check_capsules` was the only executable form of "no self judging button label" and went with nothing checking labels today, and anything else learned.

**Not in this spec**:
- web/ and mobile/ (they run on placeholder data, so "unused" there mostly means "not wired yet"). mobile's `stylePrompt` stays deferred.
- The four findings in *Follow-up*, which are behaviour gaps, not dead code.

## Decision

**Chosen option**: Option 1: Delete what is marked delete, fix what is stale, one time.

Remove the items muhammad marked delete in one change of small slices, correct every stale statement, and add no standing dead code check.

**Implementation skills**: `supabase-postgres` (`.claude/skills/supabase-postgres/`)

## Rationale

Reasoning and options: see [rationale.md](rationale.md).

## Feature design

**Data model sketch** (the target, only what changes):
- `public.threads`: `vague_streak` and its check removed.
- `admin.frameworks`: `stages` and its check removed, and `activation_conditions` removed. What a framework says to the model stays in `body`, which already carries the "Starts when" line.
- `admin.llm_calls`: `prompt_version_id` and its index removed. `model`, `error_message`, `message_id` and the token and latency columns stay.
- No table is added or removed. No column is added.

**API surface**: no endpoint, request or response changes. The OpenAPI schema is identical before and after (AC-13).

**Value sourcing**: no action produces a new value. The one value whose source changes is the pool size, which now comes only from the constants in `mani/db/pool.py` (AC-2). Before, it came from those same constants, and the settings were ignored.

**Key invariants**:
- No guardrail, crisis path, RLS policy that protects a person's rows, or audit column is removed.
- Revoking a grant never removes a privilege a code path uses. The whole integration suite, run as `mani_service`, proves it.
- Account deletion still cascades through every table (AC-8).

**Security model**: privileges only shrink. `authenticated` can no longer hard delete its own threads or offered techniques through PostgREST, which skipped the soft delete. It can no longer edit its own exercise completions or `last_message_at`, or read the framework catalog. `mani_service` can no longer delete technique state, threads or offered techniques. The dead `messages_delete` policy goes. RLS stays on everywhere, and `anon` still holds nothing.

**Configuration required**: none added. `DB_POOL_MIN_SIZE` and `DB_POOL_MAX_SIZE` stop being settings. Any environment that sets them is ignored, as it already was in effect. `CRON_SECRET` is documented in `.env.example`, not added.

**Critical test scenarios**:
- Happy path: the whole `pytest` on a reset and reseeded database, with the integration tests running, verifies **AC-1**, **AC-6**, **AC-7**, **AC-14**
- Failure case: a fresh venv without `langchain` and `email-validator` imports the app and runs the suite, verifies **AC-4**
- Auth/permission: `test_db.sh --local` asserts the revoked privileges are gone and the kept ones remain. `test_rls.sql` asserts the backend's technique state DELETE is refused. `test_account_lifecycle.py` and `test_account_deletion_cascade.py` delete an account and find no rows left, verifying **AC-5** and **AC-8**
- Nothing visible changed: a byte compare of `app.openapi()` before and after, and a grep showing every keep item still present, verifies **AC-13**

## Migration plan

**Strategy**: no live data to move. No hosted project holds data yet (muhammad, 2026-10-08), so the four migrations are plain forward migrations, applied with `supabase db reset` locally.
**Phases**:
1. Code stops reading and writing each column (slices 1 and 3) in the same change as the migration that drops it, so the code and the schema never disagree on a commit.
2. Migrations 022 to 025 apply in order.
**Rollback**: a new forward migration that adds the column or grant back. A dropped column's data does not come back; today that data is empty or always null (`vague_streak` 0, `stages` `{}`, `prompt_version_id` null), and `activation_conditions` is a copy of the first line of `body`.
**Risks**: if a hosted project is created and receives data before this ships, check the dropped columns there before `supabase db push`. Migration numbers can collide after a merge, so check that no other branch added a 022 to 025 first (see the journal note on duplicate migration versions).

## Build plan

Build approach: Tracer Bullet (project default). For a deletion pass, the thin first thread is the change with no schema, end to end through the tests. Each slice ends with the whole `pytest`, pristine, with the counts noted.

0. Precondition: muhammad has committed the 0012 and 0013 work, so `git status` shows no change in `backend/` or `chat-tester/` before the build starts. Many 0014 edits land in the same files (orchestrator.py, rows.py, config_tables.py, seed.py, the content prompts, tests), and the 0014 diff must be its own. If the tree is not clean, stop and ask.
1. Before anything changes, record the `pytest` passed and skipped counts, and save the schema with `python -c "import json, main; print(json.dumps(main.app.openapi(), sort_keys=True))"` into the scratchpad, satisfies **AC-13**, **AC-14**
2. Tracer: the Python deletions and fixes (A1 to A7 except the `stages` and `activation_conditions` names, which go with migration 023; B1 to B3, C2, C3, the five `Call` fakes, the `spend_since` test, the `Claims.email` assertion), and the AC-3 docstrings and comments outside `rows.py` and `seed.py`, satisfies **AC-1**, **AC-3**
3. Pool settings out of `config.py`, comment moved to `pool.py`, satisfies **AC-2**
4. Tests and chat tester removals and fixes, `.gitignore`, YAML ABOUTME, `.env.example`, satisfies **AC-10**
5. Dependencies: edit `requirements.txt`, build a fresh venv in the scratchpad from both requirements files, run the suite in it, then rebuild `backend/.venv` the same way, satisfies **AC-4**
6. Content: remove `type:` and `provider:` from the 10 prompt files, reseed, compare the prompt rows, satisfies **AC-9**
7. Migration 022 with the `test_grants.sql` edit, satisfies **AC-5**
8. Migration 023 with the `Framework` fields in `rows.py`, `FRAMEWORK_COLUMNS` in `config_tables.py`, the `seed.py` upsert and comments, and `test_seed_frameworks.py`, then reset and reseed, satisfies **AC-6**, **AC-1**, **AC-3**
9. Migration 024 with the `prompt_version_id` parameter removals in `client.py`, `llm_calls.py`, `orchestrator.py` and `test_memory.py`, satisfies **AC-7**
10. Migration 025 with the `test_grants.sql` and `test_rls.sql` edits and the `threads.py` comment; run `test_db.sh --local`, `test_account_lifecycle.py` and `test_account_deletion_cascade.py`, satisfies **AC-8**, **AC-3**
11. Documents: correct group G, describe 020 to 025 in the schema reference, update the `mani_service` list, delete `ai-layer-audit.md` and its pointer, satisfies **AC-11**
12. Strays: delete the old `.eval` outputs, untrack `.obsidian/workspace.json`, satisfies **AC-12**
13. Close out: full reset, reseed and `pytest`, `test_db.sh --local`, the OpenAPI compare against step 1, a grep for every keep item, PORT-STATUS, the journal note, satisfies **AC-13**, **AC-14**, **AC-15**

## Consequences

**Positive**:
- Less to read before any change. Four columns, six grants, two packages (and `langgraph` with them), about twenty Python names and one stale document go away.
- Least privilege: a user's anon key JWT can no longer hard delete their threads around the soft delete.
- The docs name only files, commands and columns that exist.

**Negative / tradeoffs**:
- The pool size can no longer be changed per environment without a code change. That was already true in effect, but a future deploy that needs a smaller pool now edits `pool.py`.
- Dropped columns are gone for good once a hosted project exists. Bringing one back is a new migration and starts empty.
- `prompt_version_id` was the hook for tying a call to the exact prompt version. If that is wanted later, it comes back with code that fills it, not as an empty column.
- A one time audit drifts. Without a standing check, new dead code collects again, and the next audit starts from scratch.

**Neutral**:
- Four forward migrations, 022 to 025.
- The tests shrink by the `check_capsules` cases and the `spend_since` test, so the passed count goes down for a reason that is recorded.

## Follow-up

- [ ] `admin.crisis_events.resolution` and `resolved_at` are never written, so the admin `unresolved=true` filter returns every crisis event. GUARDRAIL: needs its own decision, enrolled as scope feature 18.
- [ ] `scripts/fold_idle_threads.py` is scheduled by nothing, and `/internal/cron/fold-summaries` runs thread summaries, not memory folding. Memory may never fold once deployed. Needs a decision on how it is scheduled, enrolled as scope feature 19.
- [ ] The chat tester's framework state panel leaves out `ending_from` and `stage_ledger` (migrations 020 and 021). On the scope's Deferred list.
- [ ] Spec 0010's `expect_stage`, `stage_turn_cap` and `stage_last_try` are not built, and the spec has no `verify.md`. On the scope's Deferred list.
- [ ] `docs/scope/scope.md` has stale lines (8 line framing, feature 3 status, "the other five drafted"). That is for a `/scope` run, and on the scope's Deferred list.
