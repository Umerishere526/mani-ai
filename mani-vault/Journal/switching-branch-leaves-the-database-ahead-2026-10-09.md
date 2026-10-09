---
type: journal
date: 2026-10-09
apps: [backend, chat-tester]
tags: [journal, backend, chat-tester, streamlit, migrations]
---

# Switching branch leaves the database ahead, and the chat tester hid it

## What happened

muhammad reported that tapping Direct / Supportive / Reflective in the chat tester did
nothing. No spinner, no error, no message. `AppTest` with a fake client showed the button
wiring was fine, and the database had no message after the greeting.

The repo had been switched from `feat/model-text-out-of-python` to `fix/forgot-paasword`.
The local database had been migrated to 025 from the first branch; the second stops at 010.
`fastapi dev` reloaded onto the older code, which still selects
`admin.frameworks.activation_conditions`, a column migration 023 removed. Every
`POST /v1/threads/{id}/messages` raised `UndefinedColumnError` in
`config_tables.list_active_frameworks` and returned a bare 500, typed messages included.

The chat tester made it invisible: `send()` called `st.error(...)` and returned, and the
button handler then called `st.rerun()`, which cleared the page in the same instant.

## What to remember

- **`st.error` followed by `st.rerun()` is never seen.** Anything that must survive a rerun
  goes in `st.session_state` and is shown by the next run. chat-tester now keeps a failed send
  in `send_error`.
- A branch checkout moves the code under a running `fastapi dev`, never the database. Same
  lesson as [[reverting-code-does-not-revert-the-database]], reached by a different door.
  Compare `supabase_migrations.schema_migrations` with `backend/supabase/migrations/`
  before trusting a 500.
- The running backend's traceback is only in its terminal. To read one without it, start a
  second backend on a spare port and send the same request there. To test against a branch
  that matches the database without touching the checkout: `git worktree add --detach` in the
  scratchpad, copy `backend/.env` in, run with `backend/.venv`'s `fastapi`.
- A style tap is free (`chosen_style` → `_open_in_style`, no model call), so it is the
  cheap way to prove a send works end to end.

Related: [[streamlit-chat-input-has-a-mic-and-can-be-seeded]].
