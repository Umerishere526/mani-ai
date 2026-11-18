# Every chat stands alone

Date: 2026-11-18. Approved: muhammad, 2026-11-18. Size: a small change. Everything is decided and the work is mostly
deletion.

## Intent

muhammad: "the thread chat should be separate and must not be dependent on each other. even if the user is coming
with the same issue the previous chat context must never come into the new chat thread." OpenRouter's caching must
never carry anything from one chat into another either.

Why now: user1's memory held every scenario muhammad had tested. It went into every new chat and pulled old themes
in: "proving your place" in a first reply, and loops over earlier issues
(`mani-vault/Journal/loops-came-from-the-host-the-guard-and-memory-2026-11-18.md`).

This reverses the decision in force **"Memory is per person"** (2026-09-23). The client's requirements ask only for
memory within a conversation (R6, R106), so none of hers is affected.

## Goals

- A new chat's model call carries nothing from any earlier chat, with one exception: the safety check below.
- The memory path is gone completely: code, endpoints, prompt, stored data, tests, tools and docs. No dormant
  pieces are left.
- A test pins that a chat request never opts into OpenRouter's response cache, and that its cache key is that chat's
  own id.

## Kept, by muhammad's word

- **The safety check across chats.** After a pause for a safety worry, the next chat first asks how they are now
  (`chat/pause.return_check`, the return opener, `facts._pause_lines`). The "go gently" line for a recent safety
  worry in another chat (`TurnContext.recent_crisis`) stays too. Both read the pauses and threads tables, not memory.

## Kept, as my call

- **The onboarding profile** (`composer.user_context`: their preferred name and the topics they chose at sign-up).
  It is set at sign-up and never carried from a chat.
- **The greeting "good to see you again".** It carries no content from any chat.
- **The summary inside one long chat** (`summary_layer`, `summarize.py`). It reads only that chat's own messages.

## Non-goals

- No change to OpenRouter prompt caching. It only skips work on text that is byte-identical to what the new request
  itself sends (in a new chat, `mani.md` and the framework guide). Its key is already per chat:
  `session_id` and `prompt_cache_key` are `<thread_id>:<purpose>` (`llm/chain.py`).
- No change to response caching, beyond the test. It is opt-in, through the `X-OpenRouter-Cache` header or a preset,
  and nothing sends either. Live calls show `response_cache_source_id: null`.

## Anti-goals

- Leaving the fold running, or its data stored, after it stops reaching the model.
- Touching the safety carry-over.

## Approaches

- **Remove the whole memory path in one change (chosen).**
- **Only stop sending memory to the model.** Rejected: it keeps dead code and keeps folding people's chats into
  stored data that nothing reads.

## What is removed

- **Backend code:**
  - `mani/memory.py` and `mani/db/memory.py`.
  - `Memory` in `mani/llm/schema.py`.
  - `composer.user_memory` and `_MEMORY_HEADINGS` in `mani/prompts/composer.py`.
  - The `memory` part of `facts.system_prompt`.
  - `TurnContext.memory`, and the `admin.user_memory` subquery in `mani/db/threads.py`.
- **Endpoints and jobs:**
  - `POST /memory-fold` (`routers/threads.py`) and its `MemoryFoldOut` model.
  - `GET /admin/users/{user_id}/memory` (`routers/admin.py`) and its `UserMemoryOut` model.
  - The memory-fold step of the scheduled catch-up (`catch_up.py`, and the `cron.py` docstring). Its summaries and
    follow-ups stay.
  - `scripts/fold_idle_threads.py`.
- **Prompt:** `content/prompts/memory_fold.md`, and its `admin.prompts` row, deleted by the migration.
- **Data:** a new migration, `041_drop_user_memory.sql`, forward-only. It drops `admin.user_memory` and
  `public.threads.memory_folded_at`, with any grants, policies or functions that name them. muhammad approved
  dropping the data on 2026-11-18. It is permanent wherever the migration runs.
- **Chat tester:** the fold call on a new chat (`app.py` about line 185), the memory panel (`app.py` about lines
  593-600), the client methods (`client.py` `fold_memory`, `session_store.py` `remembered`), their tests, and the
  README lines.
- **Tests:**
  - `tests/integration/test_memory.py`.
  - The memory parts of `test_threads_api.py`, `test_account_deletion_cascade.py`, `test_account_lifecycle.py`,
    `test_catch_up.py`, `test_composer.py`, `test_client.py` and `test_follow_up_endpoint.py`.
  - The `user_memory` lines in `tests/sql/test_grants.sql` and `test_rls.sql`.
- **Comments and docs:**
  - Lines that name the fold: `one_at_a_time.py` ABOUTME, `db/pool.py`, `llm/client.py` about line 303,
    `scripts/llm_call_providers.py` help text.
  - `.claude/BACKEND.md` and `.claude/SUPABASE.md`.

## Added

- A unit test on the chat request the turn builds (`llm/chain.py`). It asserts:
  - the request has no `X-OpenRouter-Cache` header and no `cache_enabled` preset;
  - `session_id` and `prompt_cache_key` are the chat's own `<thread_id>:chat`;
  - two different chats get different keys.
- An integration test showing that a new chat's system prompt has nothing from an earlier chat of the same person,
  while the return check after a pause still appears.

## Records

- `backend/PORT-STATUS.md`:
  - Replace "Memory is per person" in place with **"Every chat stands alone: nothing from an earlier chat reaches a
    new one except the safety check after a pause"**, its Because line and pointers.
  - Update the "Mani's notes … nothing runs after a reply but the summary" entry and any other line that names the
    fold.
- `mani-vault/Journal/`: add `> Superseded 2026-11-18` lines to the notes that argued for memory across chats.
- A `docs/client/requirements.md` row is not needed, since it is muhammad's decision. A Conflicts row is not needed
  either, since no client requirement is reversed.

## Left to the builder

- **The `memory_fold` value of `llm_calls.purpose`.** Old log rows keep it. Remove the Python member
  (`LlmPurpose.MEMORY_FOLD`) only if nothing parses old rows into the enum. Leave the database type alone if it is an
  enum: dropping an enum value isn't worth a migration.
- **Order.** Code first, then the migration, so no running code reads a dropped table. Run the migration on the local
  databases only. Applying it to the hosted Supabase projects is muhammad's step.
