> **Historical** (marked 2026-11-25): a design or plan as written at the time; parts no longer match the code (the return check after a pause, for one, is gone). What the backend does today is in `backend/PORT-STATUS.md`.

# Every chat stands alone Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A new chat's model call carries nothing from any earlier chat except the safety check after a pause, and
the whole per-person memory path is gone.

**Architecture:**
- Two guard tests come first. One shows a new chat's system prompt carrying an earlier chat's content, and fails
  while memory exists. The other pins that no chat call opts into OpenRouter's response cache.
- Then the memory path is removed in dependency order: the turn and the API, then the database and the prompt row,
  then the chat tester, then the records.

**Tech Stack:** FastAPI on Python 3.14, asyncpg, Supabase Postgres migrations, pytest, Streamlit chat tester.

**Spec:** `docs/superpowers/specs/2026-11-18-separate-chats-design.md`

## Global Constraints

- Keep the safety carry-over untouched: `chat/pause.return_check`, the return opener, `facts._pause_lines` and
  `TurnContext.recent_crisis`.
- Keep the onboarding profile (`composer.user_context`), the greeting, and the in-chat summary (`summarize.py`,
  `summary_layer`).
- Migration `041_drop_user_memory.sql` is forward-only. Never edit migrations `009`, `031` or `032`.
- Run the migration on the local Supabase only, with `supabase migration up --local` from `backend/`. Never run
  `supabase db reset`, which wipes the local data, and never run it on a hosted project, which is muhammad's step.
- No orphans. Anything that only served memory goes: functions, models, fixtures, imports, endpoints, comments and
  README lines.
- Repo rules: an ABOUTME header on new files, no temporal words, and commit per task on `feat/one-call-turn`. Never
  push, merge or open a PR.

## Review Focus

1. **A pause in chat A still makes chat B ask how they are.** Covered by Task 1's integration test, which keeps the
   return check.
2. **Deleting an account still cascades cleanly with no `user_memory` table.** Covered by the updated
   `test_account_deletion_cascade.py` (Task 2) and the SQL suites (Task 3).
3. **The catch-up cron still runs summaries and follow-ups once its fold step is gone.** Covered by the updated
   `test_catch_up.py` (Task 2).
4. **Old `llm_calls` rows with purpose `memory_fold` still read** in `scripts/latency_report.py` and
   `scripts/llm_call_providers.py`. Task 2, Step 4 checks every reader before the enum member goes.
5. **An older client still calling `POST /memory-fold` gets a plain 404,** not a 500. Task 2's API test asserts it.

---

### Task 1: Guard tests

**Files:**
- Test: `backend/tests/unit/test_client.py` (beside `test_a_call_with_a_thread_carries_its_sticky_keys_…`)
- Test: `backend/tests/integration/test_queries.py` (beside the pause tests)

**Interfaces:**
- Consumes: `threads.load_turn_context(conn, thread_id, user_id) -> TurnContext`,
  `facts.system_prompt(config, ctx, *, summary_due) -> str`, `pause.return_check(ctx) -> ReturnCheck | None`,
  `pauses.start(...)`, and the `sent_bodies` fixture.
- Produces: the tests `test_a_chat_call_never_opts_into_openrouters_response_cache` and
  `test_a_new_chat_carries_nothing_from_an_earlier_one_but_the_safety_check`.

- [ ] **Step 1: Make `sent_bodies` also keep each request's headers.**
  - Its handler appends `dict(request.headers)` to a second list.
  - A new fixture `sent_headers`, depending on `sent_bodies`, yields that list.
  - Existing tests keep using `sent_bodies` unchanged.

- [ ] **Step 2: Write the cache guard.** It is a guard, so it is expected to pass at once (nothing sends the opt-in
  today).

```python
async def test_a_chat_call_never_opts_into_openrouters_response_cache(sent_bodies, sent_headers, recorded):
    """A stored reply could reach another chat. OpenRouter replays one only on X-OpenRouter-Cache or a preset."""
    for thread in (THREAD, OTHER_THREAD):
        await client.complete([{"role": "user", "content": "hi"}], Said, model="minimax/minimax-m3.1-flash",
                              purpose=llm_calls.Purpose.CHAT, thread_id=thread, settings=settings())
    for body, headers in zip(sent_bodies, sent_headers):
        assert not any(name.lower().startswith("x-openrouter-cache") for name in headers)
        assert "preset" not in body and "cache_enabled" not in json.dumps(body)
    assert [b["prompt_cache_key"] for b in sent_bodies] == [f"{THREAD}:chat", f"{OTHER_THREAD}:chat"]
```

- [ ] **Step 3: Write the isolation test** in `test_queries.py`.
  - Alice has chat A. Add a person message to it ("my flatmate never cleans and i'm so done") using whatever helper
    `test_queries.py` already uses to add messages.
  - Insert an `admin.user_memory` row for Alice whose `themes` holds "flatmate never cleans". This step is removed
    in Task 2, Step 6, once the table is gone.
  - Start a pause on chat A the way `test_a_pause_is_active_until_it_ends` does, ended and unchecked, so a return
    check is owed. Check `chat/pause.py` for the exact state it needs.
  - Create chat B. Load its context, and build its system prompt with a `cache.Config` holding a `mani` row whose
    content is `"MANI"`, as `tests/unit/test_composer.py` builds one.
  - Assert:

```python
    assert "flatmate" not in system.lower()
    assert pause.return_check(ctx_b) is not None
```

- [ ] **Step 4: Run both**

Run: `cd backend && source .venv/bin/activate && pytest tests/unit/test_client.py -k response_cache tests/integration/test_queries.py -k earlier_one -v`

Expected: the cache guard PASSES. The isolation test FAILS on `assert "flatmate" not in system.lower()`, because
memory carries the theme.

- [ ] **Step 5: Commit** both tests, with the failing one marked
  `@pytest.mark.xfail(strict=True, reason="memory carries earlier chats until Task 2")` so the suite stays green.
  Message: "Guard tests: no response cache, and a new chat carries nothing from an earlier one".

### Task 2: Remove memory from the turn, the API and the jobs

**Files (remove or edit, per the spec's "What is removed"):**
- Delete: `backend/mani/memory.py`, `backend/mani/db/memory.py`, `backend/scripts/fold_idle_threads.py`,
  `backend/tests/integration/test_memory.py`.
- Modify:
  - `mani/llm/schema.py` (drop `Memory`).
  - `mani/prompts/composer.py` (drop `user_memory` and `_MEMORY_HEADINGS`).
  - `mani/chat/facts.py` (`system_prompt` loses the memory part).
  - `mani/db/threads.py` (drop `TurnContext.memory` and the `user_memory` subquery).
  - `mani/routers/threads.py` (drop `POST /memory-fold`).
  - `mani/routers/admin.py` (drop `GET /admin/users/{user_id}/memory`).
  - `mani/models/api.py` (drop `MemoryFoldOut` and `UserMemoryOut`).
  - `mani/catch_up.py` (drop the fold step and the `folded` key).
  - `mani/routers/cron.py` (docstring).
  - `mani/db/llm_calls.py`.
  - `mani/one_at_a_time.py`, `mani/db/pool.py` and `mani/llm/client.py` (comments that name the fold).
  - `scripts/llm_call_providers.py` (help text).
- Tests: `test_threads_api.py`, `test_account_deletion_cascade.py`, `test_account_lifecycle.py`,
  `test_catch_up.py`, `test_composer.py`, `test_client.py`, `test_follow_up_endpoint.py`, `test_queries.py`.

**Interfaces:**
- Produces:
  - `TurnContext` with no `memory` field.
  - `catch_up` returning `{"summaries": int, "follow_ups": int}`.
  - No `/memory-fold` route.

- [ ] **Step 1: Write the API test** in `test_threads_api.py`:
  `test_the_memory_fold_endpoint_is_gone`, which asserts `POST /memory-fold` with valid auth returns 404. Run it.
  Expected: FAIL (200 today).
- [ ] **Step 2: Update `test_catch_up.py`** so the catch-up result is exactly `{"summaries": …, "follow_ups": …}`.
  Run it. Expected: FAIL on the `folded` key.
- [ ] **Step 3: Remove the code** listed above.
  - Delete every test, fixture, assertion and import that only covered memory.
  - In `test_client.py`, `test_a_call_with_no_thread_sends_no_sticky_keys` switches its purpose from `MEMORY_FOLD`
    to `Purpose.SUMMARIZE`.
- [ ] **Step 4: Decide `Purpose.MEMORY_FOLD`.**
  - Run `grep -rn "MEMORY_FOLD\|memory_fold\|Purpose(" backend/mani backend/scripts`.
  - If something builds `Purpose(...)` from stored rows, keep the member with the comment "Old log rows carry it;
    no call makes it."
  - Otherwise delete it.
  - Ledger the finding either way.
- [ ] **Step 5: Check for leftovers**

Run: `grep -rnI "user_memory\|memory_fold\|fold_memory\|memory-fold\|fold_idle\|MemoryFold\|UserMemory\|\.memory\b" backend/mani backend/scripts backend/tests`

Expected: nothing, except `memory_folded_at` in `mani/db` and tests (Task 3 drops it) and, if Step 4 kept it,
`MEMORY_FOLD`.

- [ ] **Step 6: Edit the isolation test.**
  - Remove its `admin.user_memory` insert and its `xfail` mark.
  - Its chat A message still has to stay out of chat B.
- [ ] **Step 7: Run the whole suite**

Run: `cd backend && source .venv/bin/activate && pytest -q`

Expected: all pass, with clean output.

- [ ] **Step 8: Commit.** Message: "A new chat carries nothing from earlier chats: the memory fold, its endpoints and its catch-up step are gone".

### Task 3: Drop the stored memory

**Files:**
- Create: `backend/supabase/migrations/041_drop_user_memory.sql`.
- Delete: `backend/content/prompts/memory_fold.md`.
- Modify: `backend/tests/sql/test_grants.sql` and `test_rls.sql`, plus any `memory_folded_at` reference left in
  `mani/db` or the tests.

- [ ] **Step 1: Find everything that names the table and the column.**

Run: `grep -rn "user_memory\|memory_folded_at" backend/supabase/migrations`

Read `009`, `031` and `032` to list the grants, policies, indexes and functions on them.

- [ ] **Step 2: Write `041_drop_user_memory.sql`.**
  - It needs a 2-line `-- ABOUTME:` header.
  - It drops the function(s) that only write memory, then `admin.user_memory`, then
    `public.threads.memory_folded_at` (with its index or policy, if any).
  - It runs `delete from admin.prompts where name = 'memory_fold'`.
  - Every statement takes `if exists`, so a database that never had a piece still migrates.
- [ ] **Step 3: Update the SQL suites** so they no longer expect the table, column or functions. Delete
  `content/prompts/memory_fold.md`.
- [ ] **Step 4: Apply and test locally**

Run: `cd backend && supabase migration up --local && scripts/test_db.sh --local && scripts/test_db.sh`

Expected: the migration applies, and both suites pass (on the local Supabase and on a throwaway container that
replays every migration).

- [ ] **Step 5: Run the whole suite and reseed**

Run: `source .venv/bin/activate && pytest -q && python scripts/seed.py`

Expected: all pass. The seed lists 2 prompts (`mani`, `summarization`).

- [ ] **Step 6: Commit.** Message: "Drop the stored per-person memory and the memory_fold prompt".

### Task 4: The chat tester stands alone too

**Files:** `chat-tester/app.py`, `client.py`, `session_store.py`, `README.md`, `test_admin_view.py`, `test_draft.py`,
`test_follow_up.py`.

- [ ] **Step 1: Remove the pieces.**
  - The fold call when a new chat starts (`app.py`, about line 185).
  - The memory panel (`app.py`, about lines 590-600).
  - `fold_memory` and `remembered`, and their fakes and assertions in the three test files.
  - The README lines.
- [ ] **Step 2: Check and test**

Run: `cd chat-tester && grep -rnI "memory\|fold" *.py README.md; source .venv/bin/activate && pytest -q`

Expected: no memory or fold hits that refer to the removed feature, and all chat-tester tests pass.

- [ ] **Step 3: Commit.** Message: "The chat tester no longer folds or shows memory".

### Task 5: Records

**Files:** `backend/PORT-STATUS.md`, `.claude/BACKEND.md`, `.claude/SUPABASE.md`, and journal notes found by grep.

- [ ] **Step 1: `PORT-STATUS.md`.**
  - Replace "**Memory is per person**…" in place with:

    **Every chat stands alone: nothing from an earlier chat reaches a new one except the safety check after a
    pause** (muhammad, 2026-11-18). Because a tester's memory held every scenario tested and pulled old themes and
    loops into new chats, and muhammad wants each chat separate even when the person returns with the same issue
    (2026-11-18).

    Follow it with pointers: the two Task 1 tests and migration `041`.
  - Update every other line that names the fold, the memory, or "nothing runs after a reply but the summary":
    `grep -n -i "memory\|fold" backend/PORT-STATUS.md`.
- [ ] **Step 2: Remove the memory sections** from `.claude/BACKEND.md` and `.claude/SUPABASE.md`.
- [ ] **Step 3: Mark superseded notes.** For each journal note that argued for memory across chats
  (`grep -li "memory" mani-vault/Journal/*.md`, read each), add as its first line under the frontmatter:
  `> Superseded 2026-11-18 (memory across chats) — see [[loops-came-from-the-host-the-guard-and-memory-2026-11-18]]`
- [ ] **Step 4: Check**

Run: `python3 .claude/hooks/digest.py --check backend/PORT-STATUS.md mani-vault/Journal/*.md && python3 .claude/hooks/digest.py decisions | grep -n "stands alone"`

Expected: no complaints, and the new decision is listed.

- [ ] **Step 5: Commit.** Message: "Record that every chat stands alone".
