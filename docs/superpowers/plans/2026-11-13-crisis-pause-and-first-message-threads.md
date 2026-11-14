# Crisis pause and first-message threads Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A conversation exists only once the person writes to Mani; when danger continues after Mani's one direction
with no protection in place, the person's chat pauses for 15 minutes (Library still open), and each conversation asks
whether they are all right when they come back.

**Architecture:** Part 1 replaces "create a thread on click" with a read-only opening plus a create-on-first-message
route that reuses the existing greeting, style and send paths. Part 2 adds one closed judgment (`help_in_place`), one
pure pause rule, a backend-only `chat_pauses` table, a backend gate on every chat route, a per-conversation return
check, and a Streamlit pop-up in a module of its own. The old lock paths (`CRISIS_BLOCKS_CHAT`, help-refused) are
removed completely.

**Tech Stack:** Python 3.14, FastAPI, asyncpg, Pydantic, Supabase Postgres (RLS), Streamlit (chat-tester), pytest.

**Spec:** `docs/superpowers/specs/2026-11-13-crisis-pause-and-first-message-threads-design.md`

## Global Constraints

- **Nothing is committed or pushed by Claude** (muhammad's standing rule). Where a task would commit, leave the work in
  the working tree and record it in the ledger instead.
- No AI attribution anywhere. ABOUTME two-line header on every new code file.
- Test-first: write the test, run it, read it fail for the right reason, then the code. Whole backend suite on the
  throwaway database before a task is done: `cd backend && ./scripts/test_db.sh` (KEEP_DB=1 keeps it on 55432), then
  `DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:55432/postgres ./.venv/bin/python -m pytest -q --deselect tests/integration/test_account_lifecycle.py`
  (seed that database first with `scripts/seed.py` and `scripts/seed_exercises.py` against it). Chat-tester:
  `cd chat-tester && ./venv/bin/python -m pytest -q` (`test_password_reset.py` needs the local backend on 8000).
- Local database: migration up, never reset (`supabase migration up` against 54342). Never touch the hosted one.
- Pause length: setting `CRISIS_PAUSE_MINUTES`, default `15`.
- Every kind of danger can pause (themselves, someone_else, from_someone, body). Nobody is signed out.
- A conversation's pause reason is never read by another conversation, the memory fold or the profile.
- Help numbers (reference, pending the client's list): 911 for immediate danger; 988 Suicide & Crisis Lifeline, call or
  text 988 or chat at https://988lifeline.org; Crisis Text Line, text HOME to 741741 (US).
- No text that suggests a new conversation as an alternative to help (R87).
- Comments and names say what code does, never its history (`.claude/ENGINEERING.md` rules carried in `AGENTS.md`).

## Review Focus

1. A body symptom with help already on its way ("my wife called the ambulance", the tightness still there) must never
   pause. Test in Task 6: `test_danger_with_help_on_its_way_never_pauses`.
2. The return-check turn itself must never pause, even when its message reads as danger ("still want to do it").
   Test in Task 8: `test_the_first_message_back_asks_and_never_pauses`.
3. A second pause after a return check needs a second return check (the check is tied to the pause, not just to the
   thread). Test in Task 8: `test_a_second_pause_asks_again`.
4. A retried create (same `client_message_id`, network drop after success) must not make a second thread. Test in
   Task 2: `test_a_retried_first_message_returns_the_same_thread`.
5. A pause started in another tab while this one is mid-send: the turn path itself refuses, not only the route gate.
   Test in Task 7: `test_a_turn_refuses_while_paused_even_past_the_route`.

---

## Part 1: a thread exists only once the person has written

### Task 1: Threads are created plainly and listed only once someone has written

**Files:**
- Modify: `backend/mani/db/threads.py` (`list_for_user`, `most_recent`, `create_or_reuse` → `create`)
- Modify: `backend/mani/db/admin_threads.py` (`list_all`, same filter)
- Modify: `backend/mani/chat/orchestrator.py:1683-1699` (`start_thread` calls `threads.create`)
- Test: `backend/tests/integration/test_queries.py`, `backend/tests/integration/test_turn.py` (reuse tests around :1430)

**Interfaces:**
- Produces: `threads.create(conn, user_id, title: str | None = None) -> Thread` (plain insert);
  `orchestrator.start_thread(conn, claims, title=None) -> Thread` (no longer returns `created`; always new; writes the
  greeting). "Written" means: at least one `role='user'` message with `selected_prompt is null`.

- [ ] **Step 1: Write the failing tests** in `test_queries.py`:
  `test_a_thread_with_only_a_greeting_or_a_style_tap_is_not_listed` (insert via `start_thread`, add a style tap with
  `selected_prompt`; `list_for_user` and `most_recent` return nothing; after a typed message both return it) and
  `test_start_thread_always_creates` (two calls → two distinct ids). Replace the reuse tests in `test_turn.py` (the
  ones asserting `is_new is False` / the same id on a second "new chat") with the new expectation.
- [ ] **Step 2: Run them**; expected FAIL (greeting-only thread listed; second call returns the same id).
- [ ] **Step 3: Implement** the `exists (... m.role = 'user' and m.selected_prompt is null)` filter in the three list
  queries, `threads.create`, and `start_thread` returning `Thread`. Delete `create_or_reuse` and its tests in
  `test_queries.py`; update every caller (`grep -rn "create_or_reuse\|start_thread(" backend chat-tester` — tests'
  `start()` helper keeps calling `start_thread` and takes `thread = await start_thread(...)`).
- [ ] **Step 4: Run the whole backend suite.** Expected: all pass.

### Task 2: The opening is read-only and the first message creates the thread

**Files:**
- Modify: `backend/mani/routers/threads.py` (new `GET /opening`, `POST ""` takes the first message, `GET /current`,
  `POST /memory-fold`)
- Modify: `backend/mani/models/api.py` (`OpeningOut`, `ThreadStartIn`, `ThreadStartedOut`, `CurrentOut`; delete
  `StartOut`, `ThreadCreateIn`)
- Modify: `backend/mani/chat/runner.py` (`start`)
- Modify: `backend/mani/db/messages.py` (`thread_of_client_message`)
- Modify: `backend/mani/routers/messages.py` (move `_turn_out` to `serializers.to_turn` so both routers use it)
- Test: `backend/tests/integration/test_threads_api.py` (create; or the existing route test file for threads if one
  exists — `grep -rln "/v1/threads" backend/tests`)

**Interfaces:**
- Consumes: `orchestrator.start_thread` (Task 1), `runner.send`, `greeting.greeting/STYLE_OPTIONS/OPENERS`.
- Produces:
  - `GET /v1/threads/opening -> OpeningOut{greeting: str, style_options: list[{label, style}], openers: dict[str, str], chat_paused_until: datetime | None}` (the last field is `None` until Task 7 fills it).
  - `POST /v1/threads` body `ThreadStartIn{content: str (same constraints as SendMessageIn), client_message_id: uuid | None, style: SupportStyle | None}` → `201 ThreadStartedOut{thread: ThreadOut, turn: TurnOut}`.
  - `GET /v1/threads/current -> CurrentOut{thread: ThreadOut | None, messages: list[MessageOut]}` (writes nothing).
  - `POST /v1/threads/memory-fold -> MemoryFoldOut` (`memory.fold_finished(user)` with no `keep`); the
    `/{thread_id}/memory-fold` route is deleted.
  - `runner.start(claims, content, client_message_id, style) -> tuple[Thread, orchestrator.Turn]`.
  - `messages_db.thread_of_client_message(conn, user_id, client_message_id) -> uuid.UUID | None`.

- [ ] **Step 1: Write the failing tests:**
  - `test_opening_writes_nothing` — `GET /opening` for a new account returns the greeting text
    `"Hi Al. It's MANI. How would you like me to speak with you today?"` and the three options; the account has 0 threads after it.
  - `test_current_writes_nothing_for_a_new_account` — `GET /current` → `thread is None`, 0 threads.
  - `test_the_first_message_creates_the_thread_with_its_opening` — scripted model; `POST /v1/threads` with
    `style="supportive"` and content `"I've been feeling low"` → thread exists with messages in order: greeting,
    `"Supportive"` (selected_prompt), `"How can I support you today?"`, the content, the reply; `message_count == 5`;
    `conversation_style == "supportive"`.
  - `test_the_first_message_without_a_style_writes_no_tap` — `message_count == 3`, no style.
  - `test_a_failed_first_turn_leaves_no_thread_in_view` — model raises → error status; `list_for_user` empty.
  - `test_a_retried_first_message_returns_the_same_thread` — same `client_message_id` twice → one thread, second
    response `turn.was_duplicate is True`.
- [ ] **Step 2: Run them**; expected FAIL (routes/shapes missing).
- [ ] **Step 3: Implement.** `runner.start`: if `client_message_id` is set and `thread_of_client_message` finds a
  thread, send to it (the send path returns the stored turn); otherwise `start_thread` in its own committed
  transaction, then `runner.send(claims, id, label)` when a style is given (label from `STYLE_OPTIONS`, which goes
  through `_open_in_style` unchanged), then `runner.send(claims, id, content, client_message_id)`. On any exception
  after creation: `threads.soft_delete` the new thread, then re-raise. Fill `OpeningOut` from
  `greeting.greeting(profile.nickname, returning)` with `returning = orchestrator._has_earlier_thread(...)` (make it
  public as `has_earlier_thread`).
- [ ] **Step 4: Run the whole backend suite**, fix the tests that pinned `StartOut`/`/current` writing
  (`test_account_lifecycle.py:160-165` included; it is run separately against local auth).

### Task 3: The chat-tester holds the draft until the first message

**Files:**
- Modify: `chat-tester/client.py` (`opening`, `current_thread`, `start_thread`, `fold_memory`; delete
  `start_or_resume_thread`, `start_new_thread`, `set_conversation_style`)
- Modify: `chat-tester/app.py` (`reset_thread_state`, "New conversation", first load, button taps, `deliver`)
- Test: `chat-tester/test_follow_up.py` (memory fold expectation), `chat-tester/test_history.py` or a new
  `chat-tester/test_draft.py`

**Interfaces:**
- Consumes: Task 2 routes.
- Produces: `ManiClient.opening() -> dict`, `current_thread() -> dict`, `start_thread(content: str, style: str | None, client_message_id: str | None = None) -> dict` (returns `{"thread", "turn"}` and starts the follow-up as `send_message` does), `fold_memory() -> None` (background, as today). App state: `st.session_state.thread is None` means a draft; `st.session_state.draft_style` holds a tapped style.

- [ ] **Step 1: Write the failing tests** (fake HTTP as in `test_follow_up.py`):
  `test_new_conversation_calls_nothing_that_writes` (only `GET /opening` and the fold), 
  `test_a_style_tap_in_a_draft_sends_nothing` (the tap is held; no request),
  `test_the_first_message_creates_the_thread_with_the_held_style` (one `POST /v1/threads` with `style`).
- [ ] **Step 2: Run them**; expected FAIL.
- [ ] **Step 3: Implement.** A draft shows the greeting with the style buttons from `opening()`; a style tap appends
  the tap and its opener locally and sets `draft_style`; `deliver` calls `start_thread` when `thread is None`, then
  loads `full_history`; "New conversation" clears the thread to a draft and calls `fold_memory`. The first load uses
  `current_thread()` and falls back to a draft.
- [ ] **Step 4: Run the chat-tester suite**; then by hand against the local backend: New conversation, tap a style,
  reload (no thread in the sidebar), send (thread appears with greeting, tap, opener, message, reply).

---

## Part 2: the crisis pause

### Task 4: Migration 037 — pauses, and when a crisis happened

**Files:**
- Create: `backend/supabase/migrations/037_chat_pauses.sql`
- Create: `backend/tests/sql/migrations/before_037.sql`, `after_037.sql`
- Modify: `backend/tests/sql/test_grants.sql`, `backend/tests/sql/test_rls.sql`
- Modify: `backend/mani/models/rows.py` (`Pause`)
- Create: `backend/mani/db/pauses.py`

**Interfaces:**
- Produces: table `public.chat_pauses(id uuid pk default gen_random_uuid(), user_id uuid not null references auth.users on delete cascade, thread_id uuid not null references public.threads on delete cascade, started_at timestamptz not null default now(), ends_at timestamptz not null, reason text, checked_at timestamptz)`, index on `user_id` and on `thread_id`; RLS on; `authenticated` may select own rows only; `mani_service` select/insert/update confined by RLS (pattern of `034_backend_only_state.sql`).
  Column `public.threads.crisis_at timestamptz`, backfilled from `min(admin.crisis_events.detected_at)` per thread;
  `mark_thread_crisis` sets `crisis_at = coalesce(crisis_at, now())`.
  `Pause{id, user_id, thread_id, started_at, ends_at, reason: str | None, checked_at}`.
  `pauses.start(conn, user_id, thread_id, minutes: int, reason: str | None) -> Pause`,
  `pauses.active(conn, user_id) -> Pause | None` (ends_at > now()),
  `pauses.mark_checked(conn, pause_id) -> None`.
- [ ] **Step 1: Write the failing tests:** SQL: a user reads their own pause and not another's; a user cannot insert,
  update or delete a pause; `mani_service` inserts one for the user it acts as and not for another; `after_037`:
  a flagged thread planted in `before_037` has `crisis_at` equal to its first crisis event. Python
  (`test_queries.py`): `test_a_pause_is_active_until_it_ends`.
- [ ] **Step 2: Run `./scripts/test_db.sh`**; expected FAIL (no table).
- [ ] **Step 3: Write the migration and `db/pauses.py`.**
- [ ] **Step 4: `./scripts/test_db.sh` passes; whole backend suite passes; `supabase migration up` on the local
  database (54342) succeeds.**

### Task 5: The judgment, the rule, and the first danger reply's direction

**Files:**
- Modify: `backend/mani/llm/schema.py` (`SafetyRead.help_in_place`; delete `refused_help`)
- Create: `backend/mani/chat/pause.py`
- Modify: `backend/mani/chat/context.py` (`DANGER_DIRECTION`; `build` drops `danger_said`)
- Modify: `backend/mani/chat/converse.py` (`note` carries `DANGER_DIRECTION`)
- Modify: `backend/content/prompts/voice.md` only if a test shows the chat path still lacks the direction
- Test: `backend/tests/unit/test_pause.py` (create), `test_chat_context.py`, `test_converse.py`, `test_schema.py`

**Interfaces:**
- Produces:
  - `SafetyRead.help_in_place: bool = False`, description: "Judged from the whole conversation as it stands: help has been called or is on its way, someone is with them, the means are away from them, or they have moved away from the danger. The same for every kind of danger."
  - `pause.pauses_now(before: safety.State, after: safety.State, help_in_place: bool, *, after_return_check: bool, is_return_check: bool) -> bool`
    = `not is_return_check and after is DANGER and not help_in_place and (before is DANGER or after_return_check)`.
  - `context.DANGER_DIRECTION: str` — today's `_MEANING["safety"]["danger"]` text, moved into a constant and prefixed
    "If you judge that someone is in real danger now, ". Sent with every turn that can judge danger: appended to the
    `unsure` instruction, and a line of the chat note (`converse.note`). `build(safety="danger")` always sends
    `danger_said`; the `"danger"` key and the `danger_said` parameter are deleted.
- [ ] **Step 1: Write the failing tests:** `test_pause.py::test_the_chat_pauses_only_when_danger_continues_with_nothing_in_place`
  (table over before ∈ {clear, unsure, danger}, after ∈ {clear, unsure, danger}, help_in_place ∈ {T, F}, the two
  flags; True only for before=danger/after=danger/help=F/not check, and after_return_check/after=danger/help=F/not check);
  `test_chat_context.py::test_an_unsure_turn_is_told_to_give_the_direction_if_it_judges_danger_now`
  (`"Say once, plainly and briefly"` in `build(safety="unsure")`); `test_converse.py::test_a_chat_turn_is_told_to_give_the_direction_if_it_judges_danger_now`;
  `test_schema.py::test_safety_read_reports_whether_help_is_in_place` (field exists, default False; `refused_help` gone).
- [ ] **Step 2: Run them**; expected FAIL.
- [ ] **Step 3: Implement.** Delete `refused_help` and every use (trace field in `_read_traced`).
- [ ] **Step 4: Run the whole backend suite.** Tests that built `build(..., danger_said=...)` change to the new form.

### Task 6: The pausing turn, and the old locks removed

**Files:**
- Modify: `backend/mani/chat/orchestrator.py` (the pause on the turn; delete the `crisis_blocks_chat` lock at :861-866,
  `_help_refused`, `help_refused`, `context.HELP_REFUSED`, `Turn.crisis_blocks_chat`; add `Turn.paused_until`)
- Modify: `backend/mani/chat/crisis.py` (`PAUSE_REPLY`; delete `HELP_REFUSED_REPLY`)
- Modify: `backend/mani/config.py` (`crisis_pause_minutes: int = 15`; delete `crisis_blocks_chat`)
- Modify: `backend/mani/models/api.py`, `routers/serializers.py`, `routers/messages.py` (delete `crisis_blocks_chat`;
  add `TurnOut.paused_until: datetime | None`)
- Modify: `backend/mani/chat/understanding.py` (kept keys), `backend/tests/conftest.py`, `tests/unit/test_config.py`
- Test: `backend/tests/integration/test_turn.py`

**Interfaces:**
- Consumes: `pause.pauses_now`, `pauses.start` (Tasks 4–5).
- Produces: `crisis.PAUSE_REPLY: str` with a `{minutes}` slot, exactly:
  "I'm worried about your safety, so I'm pausing our conversation for the next {minutes} minutes. If you are in danger right now, call 911. You can call or text 988 to reach the Suicide & Crisis Lifeline, or text HOME to 741741 to reach Crisis Text Line. Please reach out to one of them now."
  `Turn.paused_until: datetime | None`, `TurnOut.paused_until`. Trace key `paused: true`.
- [ ] **Step 1: Write the failing tests:**
  - `test_danger_that_continues_with_nothing_in_place_pauses_the_chat` — reply 1 `SafetyRead(danger="now", about="themselves")`, reply 2 the same with `declined=True` and `why="has the pills and will not call"`; turn 2's content is `PAUSE_REPLY.format(minutes=15)`, `paused_until` ≈ now+15 min, a `chat_pauses` row with that `reason` and this thread; `scripted.calls == 2`.
  - `test_danger_with_help_on_its_way_never_pauses` — `about="body", symptom_now="yes"`, second reply `help_in_place=True`; no pause row.
  - `test_the_first_danger_message_never_pauses` and `test_an_unsure_concern_never_pauses`.
  - Delete `test_a_thread_locks_only_where_crisis_blocks_chat_is_on` and the three help-refused tests (`test_turn.py:3580-3630`), and the `crisis_blocks_chat` assertion at :998.
- [ ] **Step 2: Run them**; expected FAIL.
- [ ] **Step 3: Implement.** In `_turn`, after `state_after`: `pausing = pause.pauses_now(state_before, state_after, read.help_in_place, after_return_check=..., is_return_check=...)` (both flags False until Task 8); when pausing, `pauses.start(conn, user_id, thread.id, settings.crisis_pause_minutes, read.why)` in the turn's transaction, the reply text becomes `PAUSE_REPLY`, buttons empty, and the turn carries `paused_until`. Remove every `crisis_blocks_chat` (`grep -rn "crisis_blocks_chat\|CRISIS_BLOCKS\|help_refused\|HELP_REFUSED\|refused_help" backend chat-tester` returns only the journal and PORT-STATUS history). Correct the comments the audit found false: `safety.py:13,59,106` ("the screen locks"), the `_record_danger` docstring ("locks only where CRISIS_BLOCKS_CHAT is on"); delete `Assessment.blocks_framework` (no caller).
- [ ] **Step 4: Run the whole backend suite.**

### Task 7: The gate, the status, and the help numbers

**Files:**
- Modify: `backend/mani/errors.py` (`ErrorCategory.CHAT_PAUSED = "chat_paused"` → 423; `ServiceError(details: dict | None = None)`), `backend/main.py` (`error_body` emits `details`)
- Modify: `backend/mani/auth/deps.py` (`ChatOpen`)
- Modify: `backend/mani/routers/threads.py` (`POST ""` uses `ChatOpen`; `/opening` fills `chat_paused_until`), `routers/messages.py` (send, edit, follow-up use `ChatOpen`), `routers/profile.py` + `ProfileOut.chat_paused_until`
- Modify: `backend/mani/db/threads.py` (`TurnContext.pause`), `backend/mani/chat/orchestrator.py` (refuse inside the turn)
- Modify: `backend/mani/chat/crisis.py` (`RESOURCES`)
- Test: `backend/tests/integration/test_turn.py`, route tests, `backend/tests/unit/test_crisis.py` (or where resources are tested)

**Interfaces:**
- Produces: `paused_error(pause: Pause) -> ServiceError` (category `CHAT_PAUSED`, `user_message` "Your chat with Mani is paused for now. Please reach out for support.", `details={"paused_until": iso}`) in `chat/pause.py`; `ChatOpen = Annotated[Claims, Depends(require_chat_open)]` where `require_chat_open` takes `Participant`, opens a short `pool.as_user` connection and raises `paused_error` when `pauses.active` finds one. `TurnContext.pause: Pause | None` = the user's latest pause, with `reason` selected only when `pause.thread_id = t.id`. `RESOURCES`: three `Resource(country="US", ...)` entries with the Global Constraints' numbers.
- [ ] **Step 1: Write the failing tests:** `test_every_chat_route_refuses_while_paused` (create, send, edit, follow-up → 423, `error.category == "chat_paused"`, `error.details.paused_until`); `test_the_library_and_profile_stay_open_while_paused` (`GET /v1/exercises`, `GET /v1/profile` 200, profile carries `chat_paused_until`; `GET /opening` carries it); `test_a_turn_refuses_while_paused_even_past_the_route` (call `runner.send` directly with an active pause row → `ServiceError` `CHAT_PAUSED`); `test_crisis_resources_list_the_reference_numbers`; `test_another_conversations_turn_never_loads_the_reason`.
- [ ] **Step 2: Run them**; expected FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the whole backend suite.**

### Task 8: The return check, the end check, recent crisis

**Files:**
- Modify: `backend/mani/chat/pause.py` (`return_check`), `backend/mani/chat/context.py` (`_MEANING["safety"]["returning"]`, `["returning_new"]`, keys `RETURN_CHECK`, `DANGER_REACHED`), `backend/mani/chat/orchestrator.py` (`_turn` and `_converse`), `backend/mani/db/threads.py` (`recent_crisis` from `crisis_at`)
- Test: `backend/tests/integration/test_turn.py`, `backend/tests/unit/test_pause.py`

**Interfaces:**
- Produces: `ReturnCheck{pause_id: uuid, kind: Literal["paused_thread", "new_thread"], reason: str | None}`;
  `pause.return_check(ctx) -> ReturnCheck | None`:
  - `paused_thread` when `ctx.pause` ended, `ctx.pause.thread_id == ctx.thread.id`, and `understanding[RETURN_CHECK]` is not `{"pause": that id, ...}`;
  - `new_thread` when `ctx.pause` ended, `checked_at is None`, `ctx.thread.created_at > ctx.pause.ends_at`, and this thread has not asked for that pause.
  `understanding[RETURN_CHECK] = {"pause": str(id), "state": "asked" | "answered"}`; `understanding[DANGER_REACHED] = True` once a turn ends in danger.
  Instruction texts (`[ctx]` `safety: returning` / `returning_new`):
  - returning: "their chat with you was paused earlier because they were in danger: {reason}. Before anything else, ask whether they are all right now, and say plainly that this is why you are asking. Answer what they just wrote in a line at most. No set of questions, no offer, no library."
  - returning_new: "before anything else, ask whether they are all right right now, warmly and in a sentence. Never mention another conversation or anything from one. No set of questions, no offer, no library."
- Behaviour: a return-check turn is a safety turn (state for the turn at least unsure) whatever the thread's state, never pauses (`is_return_check=True`), records `asked`; the next turn passes `after_return_check=True`, records `answered`; a settled answer (state after clear) also calls `pauses.mark_checked`. The end check after a framework's last stage keys on `DANGER_REACHED`, not `crisis_detected`. `recent_crisis` reads `c.crisis_at > now() - 30 days`.
- [ ] **Step 1: Write the failing tests:**
  - `test_the_first_message_back_asks_and_never_pauses` — pause the thread (Task 6 path), move `ends_at` into the past, send "I still want to do it" with a scripted danger reply → no new pause; `[ctx]` sent has `safety: returning` and the stored reason.
  - `test_a_fine_answer_clears_the_paused_thread_and_marks_the_pause_checked`.
  - `test_danger_in_the_answer_pauses_again` and `test_a_second_pause_asks_again`.
  - `test_a_new_conversation_after_a_pause_asks_without_details` — `[ctx]` has `returning_new`, no reason text, no other thread's words; after a fine answer, a third new conversation does not ask; the paused one still asks.
  - `test_an_unsure_answer_is_not_asked_again`.
  - `test_the_end_check_comes_only_after_danger` (a phrase judged unsure and settled → framework ends with the closing choices directly).
  - `test_recent_crisis_counts_from_the_crisis_not_the_last_message`.
- [ ] **Step 2: Run them**; expected FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the whole backend suite.**

### Task 9: The chat-tester pop-up

**Files:**
- Create: `chat-tester/crisis_pause.py`, `chat-tester/test_crisis_pause.py`
- Modify: `chat-tester/app.py` (delete `st.session_state.locked` and its banner; gate the chat page), `chat-tester/client.py` (`crisis_resources`), `chat-tester/trace_view.py` (`paused` → "Chat paused", `return_check` → "Return check"; delete "Blocked, refused help"), `chat-tester/test_trace_view.py`

**Interfaces:**
- Produces: `crisis_pause.paused_until(source: dict) -> datetime | None` (reads `paused_until` from a turn, `chat_paused_until` from a profile or opening, or `error.details.paused_until` from an `ApiError` body); `crisis_pause.minutes_left(until: datetime, now: datetime) -> int` (rounded up, never below 1); `crisis_pause.render(client, until)` — an `st.dialog` titled "Your chat is paused" with "You can chat with Mani again in {n} minutes." and each resource; closing it sets `st.session_state.view = "library"`.
- [ ] **Step 1: Write the failing tests:** `test_paused_until_is_read_from_a_turn_a_profile_and_an_error`, `test_minutes_left_rounds_up_and_never_shows_zero`, `test_trace_view` updates.
- [ ] **Step 2: Run them**; expected FAIL.
- [ ] **Step 3: Implement.** On any of the three sources while the pause runs: `st.session_state.paused_until` is set; the chat page renders the dialog and stops (no composer, no New conversation, no history); the sidebar's New conversation is disabled; the Library works. Checked once per run from the stored value, refreshed from `get_profile()` on sign-in, reload and when the stored time passes.
- [ ] **Step 4: Run the chat-tester suite**, then by hand: refusal chat → pause pop-up → close → Library; chat button → pop-up again; reload → still paused; after the time passes (set `ends_at` back in the local database) the chat opens and the paused conversation asks with its reason.

### Task 10: Records, reseed, live replays

**Files:**
- Modify: `backend/PORT-STATUS.md` (Decisions in force, edited in place: "nothing locks" 2026-11-06, "help refused is the only block" 2026-11-11, `CRISIS_BLOCKS_CHAT`, the end check, threads created on the first message), `docs/client/requirements.md` (to-tell-the-client: the pause, 15 minutes, return check, help numbers, `PAUSE_REPLY` and both return-check texts as our wording), `mani-vault/Journal/` (the audit's dead danger instruction and default mismatch)
- [ ] **Step 1:** Records written.
- [ ] **Step 2:** `cd backend && env -u DATABASE_URL ./.venv/bin/python scripts/seed.py && env -u DATABASE_URL ./.venv/bin/python scripts/seed_exercises.py`; restart `fastapi dev` on 8000; `curl -s http://127.0.0.1:8000/health` → `{"status":"ok"}`; restart the chat-tester on 8501.
- [ ] **Step 3:** Live replays, twice each, on muhammad's key: manasa's Topic 3 (refuses help: expect a pause on the message after the direction), muhammad's chest-and-wife chat (expect no pause), the ten unseen chats of 2026-11-11 (expect pauses only where danger continued with nothing in place; none in the grief and ordinary chats). Report one table: chat, run, pause at which message or none, and any reply that went wrong.
