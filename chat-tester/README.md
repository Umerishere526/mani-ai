# chat-tester

A small Streamlit UI for having real conversations against the running backend - to feel
when a framework gets offered, when the somatic hand-off happens, and when it lands on an
exercise, before tuning any of that behaviour further in the LangChain prompts or config.

**This is a fourth, independent thing in this repo, alongside `web/`, `mobile/` and
`backend/` - not part of any of them.** It has its own dependencies and does not touch
backend code. Every message it sends goes through the real `POST /v1/threads/{id}/messages`
endpoint, the real LangChain call, the real router and safety screen - this is not a mock.

## What it simulates versus what is real

- **Real:** every chat turn, every capsule tap, style selection (`PATCH /v1/threads/{id}`),
  framework offers, the somatic hand-off, the exercise hand-off, crisis locking. All of it
  goes over HTTP to the actual FastAPI app - nothing here calls `orchestrator.py` directly.
- **Simulated, on purpose:** signing in. The backend has no password login of its own to
  test against locally, so this tool mints a JWT with the same secret the backend verifies
  against (`SUPABASE_JWT_SECRET`) and writes a matching row into `auth.users` directly -
  the one thing a real sign-in does that nothing here can otherwise stand in for. It is a
  substitute for that one step, not for anything downstream of it.
- **Simulated, because the backend does not have this yet:** the three-style picker at the
  start of a conversation. The spec calls for it as capsules on the greeting itself; the
  backend does not emit those yet, so this tool asks for the style with its own buttons and
  sets it through the same `PATCH` endpoint a real picker screen would call once built.

## Setup

```bash
cd chat-tester
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env` from `backend/.env` - same `DATABASE_URL`, same `SUPABASE_JWT_SECRET`. If the
backend was set up with a published key set instead of a shared secret, this tool cannot
mint a token; add one locally for testing or ask muhammad how the project signs tokens.

## Running

The backend has to already be running:

```bash
cd backend && source .venv/bin/activate && supabase start && fastapi dev main.py
```

Then, in another terminal:

```bash
cd chat-tester && source .venv/bin/activate && streamlit run app.py
```

Enter any name in the sidebar and press **Start / switch user**. The same name always
resumes the same test user and their conversations - it is hashed into a stable id, not
a random one each time.

## What to look at

- **The sidebar's "Framework state" panel** - a direct read of `thread_technique_state`,
  refreshed on every interaction. Watch `phase` move through a framework's stages as the
  conversation continues, and `outcome` flip from `offered` to `accepted` when you tap
  "Yes, let's try it" or say so in free text.
- **The "Recent calls" panel** - one row per model call, in order, with token counts and
  the cached fraction. A completing framework with a matching exercise shows as two calls
  instead of one; check `admin.exercises.framework_id` if there is content to match.
- **"Last turn, raw"** - the exact `TurnOut` JSON, including `reasoning` if
  `AI_DEBUG_MODE=true` in `backend/.env`.

None of these three panels are things a real client shows - they exist here because seeing
them is the entire point of this tool.
