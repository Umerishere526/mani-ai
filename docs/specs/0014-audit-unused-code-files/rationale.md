# 0014. Rationale and inventory

## Context

The lean prompt work (specs 0003 to 0013) removed the router, the redraft and repairs, the body ending module, the per stage framework content and several eval scripts in quick succession. Each change removed what it replaced, but the things around them stayed: columns the old code filled, parameters nobody passes any more, tests for checks no eval runs, and docs that still describe the old shape. The scope (feature 16) asks for one list of all of it, with evidence for each item, before anything is deleted.

The forces are these. The replies are health content, so anything touching safety, crisis handling or the record of what happened has to be marked keep, whether or not code reads it. The schema is forward only, and a dropped column's data is gone. muhammad decides every item; the audit only proposes. The work has to leave behaviour, the API schema and the tests' meaning unchanged.

The audit covers `backend/` (code, content, schema, scripts, tests), `chat-tester/`, `backend/docs/`, `.claude/*.md`, `docs/` and the vault. It leaves out `web/` and `mobile/`, which still run on placeholder data. It read the working tree on `feat/model-text-out-of-python` at f906800, with the uncommitted 0012 and 0013 work, on 2026-10-08.

## Options considered

### Option 1: Delete what is marked delete, fix what is stale, one time

Every item gets evidence and a keep or delete mark from muhammad. The deletes ship as small slices with the whole suite after each, and the stale docs are corrected in the same change.

**Pros**:
- The code, schema and docs match what runs, and there is nothing to maintain afterwards.
- Each delete has a recorded reason and a recorded decision, so the next reader can trust the gap.

**Cons**:
- It is a snapshot. New dead code collects again, and nothing catches it.

### Option 2: Document, do not delete

Mark each unused item in a comment or in PORT-STATUS, and leave it in place until something needs the space.

**Pros**:
- Nothing can break, and every column keeps its data.

**Cons**:
- Every future change still has to read past it, and a comment that says "unused" goes stale the moment someone starts using the thing.
- The extra grants stay, so a user can still hard delete threads around the soft delete.

### Option 3: Delete, and add vulture as a standing pytest check

As Option 1, plus `vulture` in `requirements-dev.txt` and a test that fails on new dead Python.

**Pros**:
- New dead Python fails the suite as soon as it is written.

**Cons**:
- With no CI, it only runs when someone runs `pytest`.
- At a useful confidence level, vulture flags every route handler, validator and `model_config` (see *Method* below), so the check needs a whitelist that has to be maintained.
- It sees only Python, not columns, grants, content fields or docs, which were most of this audit.

## Rationale

Option 1. The cost this feature exists to remove is reading: every change in specs 0007 to 0013 had to work out whether something old still mattered. Option 2 keeps that cost and leaves a real privilege gap open. Option 3's check would cover the smallest part of the problem (Python names) at the price of a whitelist, in a repo with no CI to run it, so it fails "the best code is no code" for a one time job. muhammad chose a single vulture run as a cross check instead, and it found nothing the grep had missed.

The one place the audit stopped short of "delete what nothing reads" is the write only audit columns (E5). No code reads `llm_calls.model`, `llm_calls.error_message` or the prompt editor columns, but each is the only record of something a person needs when a reply or a prompt goes wrong: which model served a call (the model comes from call rows and can change without a deploy), why a call failed, and who edited a prompt through the admin API. muhammad first marked them delete on my recommendation, and then marked them keep after I corrected that recommendation. A record you open by hand is still in use.

`prompt_version_id` is different: it is always null, so it records nothing. If tying a call to a prompt version is wanted later, it should come back together with code that fills it.

## Method

- Three read only agents traced every Python name, content key, column, grant, test, script and document by name across `backend/mani`, `backend/main.py`, `backend/scripts`, `backend/tests`, `backend/supabase/migrations`, `chat-tester/` and the docs. An item counts as unused when the only hits are its definition (and, for "test only", tests).
- The main thread checked the load bearing items again with `grep -rnE '<name>' --include='*.py' --include='*.sql' backend chat-tester` (venvs excluded).
- A read only cross check on another model (Sonnet 5.5) read the drafted spec against the code. It found that `tests/sql/test_rls.sql` deletes technique state as `mani_service` (fixed in AC-8), that the framework column list and `Framework.stages` had to go with migration 023 (AC-6), the stale lines added to group G, and `messages_delete` (E7g). muhammad accepted its fixes.
- One vulture run (`vulture backend/mani backend/main.py backend/scripts chat-tester/*.py --min-confidence 60`, from a throwaway venv in the scratchpad). It reported every item below, plus false positives: route handlers registered by decorator, Pydantic `model_config` and validators, `LibrarySection` members (iterated in `guards.py`), `Memory` fields (read through `model_fields`), response model fields, and the chat tester's `view` and `session_key` (read at `app.py:94` and `session_store.py:158`). At confidence 90 it reported nothing. It added no new finding.

## Inventory

Marks are muhammad's, given on 2026-10-08. "Only def" means the grep returned the definition and nothing else.

### A. Python nothing references

| # | item | where | evidence | mark |
|---|---|---|---|---|
| A1 | `summary_snapshot` | mani/chat/orchestrator.py:947 | only def | delete |
| A2 | `get_prompt` (by name) | mani/db/config_tables.py:43 | only def; the admin route of the same name calls `get_prompt_by_id` | delete |
| A3 | `SystemPrompt.length` | mani/prompts/composer.py:36 | `\.length\b` finds nothing | delete |
| A4 | `Call.model`, `Call.latency_ms` | mani/llm/client.py:41,43 | set at client.py:300, never read; the record gets both from its own parameters | delete |
| A5 | `Thread.deleted_at` row field | mani/models/rows.py:76 | no attribute read; the SQL filter reads the column | delete |
| A6 | `Framework.activation_conditions` row field | mani/models/rows.py:154 | no attribute read; rows.py:160 says "read by nothing" | delete |
| A7 | `from typing import Any` | mani/db/threads.py:9 | `Any` appears only on that line | delete |
| A8 | `db_pool_min_size`, `db_pool_max_size` | mani/config.py:45-46 | read nowhere; pool.py:22-23 uses its own 2 and 10 | delete the settings, keep the constants |
| A9 | GUARDRAIL `CLARIFICATION` placeholder | mani/chat/safety.py:196 | only def | keep |
| A10 | GUARDRAIL `Assessment.matched` | mani/chat/safety.py:46 | set at safety.py:177, never read | keep |

### B. Kept alive only by tests

| # | item | where | evidence | mark |
|---|---|---|---|---|
| B1 | `spend_since` | mani/db/llm_calls.py:85 | def plus tests/integration/test_queries.py:321 | delete with its test |
| B2 | `Claims.email` | mani/auth/jwt.py:30 | read only at tests/unit/test_auth.py:41 | delete |
| B3 | `Call.usage` | mani/llm/client.py:42 | read only by a fake at tests/integration/test_memory.py:292 | delete |
| B4 | `SystemPrompt.layers` | mani/prompts/composer.py:34 | read at test_composer.py:57,61,67 to check layer order | keep |
| B5 | `Settings.supabase_anon_key` | mani/config.py:60 | the account lifecycle test signs up through it | keep |
| B6 | `Ending.KEEP_TALKING`, `SupportStyle.DIRECT/REFLECTIVE` | guards.py:20, rows.py:56-57 | named only in tests, but built from values (`Ending(reported)`, `SupportStyle(...)`) | keep |

### C. Parameters production always passes the same

| # | item | where | evidence | mark |
|---|---|---|---|---|
| C1 | `prompt_version_id` on `complete`, `choose_exercise`, `_record`, `llm_calls.record` | mani/llm/client.py:140,183,320; db/llm_calls.py:45 | the only explicit value is `None` at orchestrator.py:395; every other caller takes the default | delete (with E4) |
| C2 | `llm_calls.record(message_id)` | mani/db/llm_calls.py:44 | its only caller, client.py:154, never passes it | delete |
| C3 | `reconcile_due(limit)` | mani/summarize.py:159 | the only call, cron.py:31, takes the default; test_summarize.py:75 too | delete |
| C4 | GUARDRAIL `_handle_crisis(llm_call_id)` | mani/chat/orchestrator.py:874 | one call site, never passes it; the docstring says "two places" | keep the code, fix the docstring |
| C5 | `settings=` test seams, `seed.load_prompts(directory)` | various | tests inject through them | keep |

### D. Dependencies

| # | item | evidence | mark |
|---|---|---|---|
| D1 | `email-validator` | `grep -rnE "email_validator\|EmailStr"` finds nothing | delete |
| D2 | `langchain==1.4.1` | never imported; it requires `langgraph`. The code imports `langchain_core` (1.6.6 installed, unpinned) and `langchain_openai` | replace with `langchain-core==1.6.6` |
| D3 | `python-dotenv`, `uvicorn[standard]`, `python-multipart`, `pytest-asyncio`, `fastapi-cli` | used indirectly: pydantic-settings, the Dockerfile CMD, `UploadFile`, pytest.ini, `fastapi dev` | keep |

### E. Database

| # | item | evidence | mark |
|---|---|---|---|
| E1 | `threads.vague_streak`, its check and its `mani_service` UPDATE grant | 002:14,23,34; `grep -rn vague_streak mani scripts` finds nothing; only test_grants.sql:95,98 | delete |
| E2 | `admin.frameworks.stages` and its check | seed.py:190 always writes `{}`; the `.stages` reads in guards.py and orchestrator.py are the model reply's stage report | delete |
| E3 | `admin.frameworks.activation_conditions` | written by seed.py:182 as a copy of the "Starts when" line, which is also in `body`; selected at config_tables.py:26, never read | delete |
| E4 | `admin.llm_calls.prompt_version_id`, `idx_llm_calls_prompt_version` | always null (C1) | delete |
| E5 | `llm_calls.model`, `error_message`, `message_id`; `prompts.created_by/updated_by`; `prompt_versions.created_by`; every `created_at/updated_at` and the `touch_updated_at` triggers | written, never read by code | keep (audit records read by hand; see Rationale) |
| E6 | GUARDRAIL `crisis_events.resolution`, `resolved_at`, `message_id` | resolution and resolved_at are never written; message_id is never read | keep |
| E7a | DELETE on `thread_technique_state` to `mani_service`, policy `technique_state_delete` | `grep -rn "delete from public."` finds nothing; retiring is an UPDATE (db/threads.py:299); the 001:721 comment is stale | revoke |
| E7b | DELETE on `threads` to `authenticated`, policy `threads_delete` | soft delete by UPDATE (threads.py:134) | revoke |
| E7c | DELETE on `thread_techniques_offered` to `authenticated` | no delete anywhere | revoke |
| E7d | UPDATE on `exercise_completions`, policy `completions_update` | db/exercises.py:103 only inserts | revoke |
| E7e | column UPDATE `(last_message_at)` on `threads` to `authenticated` | written only by the count trigger inside the definer functions | revoke |
| E7f | SELECT on `admin.frameworks` to `authenticated` | frameworks load on the admin connection only (prompts/cache.py:90) | revoke |
| E7g | policy `messages_delete` (001:441) | no DELETE grant on `messages` behind it, so it permits nothing; found by the cross check | drop (muhammad, with the cross check fixes) |
| E8 | `type:`, `provider:` in the 10 `content/prompts/*.md` | `parse_prompt` (seed.py:39-46) ignores them; nothing else reads the files | delete |

### F. Tests, scripts, chat tester

| # | item | evidence | mark |
|---|---|---|---|
| F1 | `TONES`, tests/unit/test_chat_context.py:292 | only def | delete |
| F2 | `check_capsules`, `MAX_CAPSULES` (tests/evals/validators.py:152-189), `SELF_JUDGMENTS`, `MAX_CAPSULE_WORDS` (tests/evals/vocabulary.py:42,49), 4 tests at test_negative_set.py:212-238 | `eval_replies._score` never scores labels, so only its own tests call it. It is the only executable form of "no self judging button label", and the model still writes labels (guards.py:175, response_format.md:38); accepted as a gap, since nothing runs it today | delete |
| F3 | `test_after_keep_chatting_...` (test_chat_context.py:532); `tests/__init__.py` docstring; conftest.py comment "does not name a database" above a fallback that names one | the label is "I want to keep talking"; the docstring leaves out integration and sql | fix |
| F4 | `ManiClient.list_messages` (chat-tester/client.py:213), `set_conversation_style` (:238) | only def | delete |
| F5 | root `.gitignore` `chat-tester/.venv/` | the venv is `chat-tester/venv/`, ignored only by its own `.gitignore` | fix |
| F6 | `scripts/eval_conversations.yaml` ABOUTME, "worked examples" | framework files are seven lines with no examples | fix |
| F7 | `CRON_SECRET` missing from `backend/.env.example` | read at routers/cron.py | fix |

### G. Documents with stale statements (all fix in place)

| file | stale claim | what is true |
|---|---|---|
| .claude/BACKEND.md:25 | `.env` points at 54321 | `.env` and `docker ps` use 54341/54342/54343 |
| .claude/BACKEND.md:38 | `router.py` shortlists frameworks, `ending.py` holds the body ending | neither exists; the line should name the files in `mani/chat/` as they are (`vetoes.py`, `techniques.py`, `ledger.py`, `offer.py`, `greeting.py`, `crisis.py` among them) |
| .claude/BACKEND.md:39 | `somatic.md` merged into frameworks; activation keys `central_indication` … `not_when`; per stage content | seed.py:99 allows only `never_offer_when_said`; frameworks are seven lines |
| .claude/BACKEND.md:41,120 | evals check stage asks | they check framework lines |
| .claude/BACKEND.md:42 | fold_idle_threads is reachable as the cron route | the route runs `summarize.reconcile_due` |
| .claude/BACKEND.md:43 | `ai-layer-audit.md` (a dated snapshot) | deleted (G1) |
| .claude/BACKEND.md:88-90 | "Things a reviewer will check for." twice | once |
| .claude/SUPABASE.md:66 | `admin` holds "providers" | no such table |
| .claude/SUPABASE.md:47 | `mani_service` holds DELETE on technique state and UPDATE on `vague_streak` | both gone (E1, E7a) |
| backend/PORT-STATUS.md:17 | 12 migrations, 8 prompts | 18 migrations after this spec, 10 prompts |
| backend/PORT-STATUS.md:93,127 | the cron route is the idle memory fold | it runs thread summaries |
| backend/PORT-STATUS.md:296 | `appropriate_when` / `not_when` are in the framework files | they are not |
| backend/PORT-STATUS.md:316-317 | three frameworks wait for the third message | contradicts :80-82; `earliest_offer_message` is gone |
| backend/PORT-STATUS.md:330 | local Supabase on 54321 to 54324 | 5434x |
| backend/docs/database-schema-reference.md:6,24 | after 001 to 010, 018, 019; ten migrations | 020 to 025 exist after this spec |
| backend/docs/database-schema-reference.md | no `stage_ledger`, `ending_from` | migrations 020, 021 |
| backend/docs/database-schema-reference.md:184,191 | `body` written never read; `stages` holds stage content | composer.py:62 reads `body`; `stages` is dropped (E2) |
| backend/docs/specs/README.md:35-40 | stage sections go to `stages` with an `ask` leaf; worked examples feed routing evals | `stages` is dropped; no routing eval exists |
| backend/docs/specs/conversational-styles.md:5 | source of truth is `mani/Programme/conversational-architecture.md` | that file does not exist |
| chat-tester/README.md:10,31 | "the real router"; "variables above" | router.py is gone; no variables are above that line |
| mani/models/rows.py:158-160 | `stages` is read only by the admin side | the field is dropped (E2) |
| backend/PORT-STATUS.md:191,205,294 | `spend_since()` is what one would read; `db_pool_*` settings nothing reads; `vague_streak` granted and written by nothing | all three are gone (B1, A8, E1) |
| .claude/BACKEND.md:59 | `email-validator` is installed | removed (D1) |
| backend/docs/database-schema-reference.md:103,185,191,264,296,345 | `vague_streak`, `activation_conditions`, `stages`, `prompt_version_id`, `mani_service` grants | dropped or revoked (E1 to E4, E7) |
| mani/db/llm_calls.py:2, :76-77 | "Nothing here existed before"; the link answers "which prompt version wrote a reply" | history, and `prompt_version_id` is dropped (E4) |
| mani/llm/client.py:38 | `Call` is "what came back, and what it cost" | the cost fields go (A4, B3) |
| mani/db/threads.py:285 | the column grant covers `last_message_at` | revoked (E7e) |
| tests/sql/test_grants.sql:86-88, :147 | comments on `vague_streak` and the framework registry | both change (E1, E7f) |

| # | item | mark |
|---|---|---|
| G1 | backend/docs/ai-layer-audit.md, a 2026-09-23 snapshot whose "Now" column is itself stale (router.py, redraft, `offer_fit`, the old model) | delete |
| G2 | journal notes naming deleted files, and nine notes no other note links to | keep: they are true as history |
| G3 | docs/scope/scope.md stale lines | keep for `/scope` |

### H. Stray files

| # | item | mark |
|---|---|---|
| H1 | backend/.eval/client_style/* and two .log files, written by the deleted `eval_client_style.py`, gitignored | delete |
| H2 | GUARDRAIL backend/.eval/safety_flag/*.json, from the deleted `eval_safety_flag.py` | keep |
| H3 | `.obsidian/workspace.json`, tracked per user view state | untrack and ignore |
| H4 | `skills-lock.json`, `.agents/skills/**` (40 tracked files), named nowhere in the project docs | keep: most likely the skills installer's lock |

## Looked unused but is used

- The `supabase_auth_admin` grants and policies in migrations 005 and 009, used by the account deletion cascade.
- `create_profile_for_new_user` (004), a trigger on `auth.users`.
- GUARDRAIL `threads.crisis_detected`, read at orchestrator.py:227, db/memory.py:23 and db/threads.py:193.
- GUARDRAIL the RLS policies and the `mani_service` EXECUTE grants, applied on every request through `set local role mani_service`.
- `admin.exercises` SELECT and `admin` schema USAGE for `authenticated`, used by the exercises router and the turn query.
- `threads.memory_folded_at`, written by db/memory.py:95,134.
- `profiles.age_bracket`, returned to the client by serializers.py:78.
- `llm_calls` token and latency columns, `purpose` and `outcome`, read by `eval_replies.py` and `baseline.py`.
- `display_order`, `is_active`, `offered_at`, `thread_response_styles.created_at`, used in WHERE and ORDER BY.
- `library_offered_since`, read at context.py:208.
- The `debug.md` and `title_generation.md` prompts, the `openers` key in `replies.md`, and every key in `tuning.md`.
- `scripts/fold_idle_threads.py` and the other scripts: command line entry points.
- `tests/seeded.py`, `tests/integration/cleanup.py`, and the autouse fixtures `admin_pool` and `no_real_exercise_call`.
- `supabase/templates/recovery.html` (config.toml:255) and `test_harness.sql` (test_db.sh:79).
- GUARDRAIL `safety.PROTOCOLS` and `crisis.RESOURCES`, empty on purpose until approved wording exists.
