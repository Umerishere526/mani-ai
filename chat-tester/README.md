# chat-tester

A small Streamlit UI for having real conversations against the running backend - to feel
when a framework gets offered, when the somatic hand-off happens, and when it lands on an
exercise, before tuning any of that behaviour further in the LangChain prompts or config.

**This is a fourth, independent thing in this repo, alongside `web/`, `mobile/` and
`backend/` - not part of any of them.** It has its own dependencies and does not touch
backend code. Every message it sends goes through the real `POST /v1/threads/{id}/messages`
endpoint, the real LangChain call, the real router and safety screen - this is not a mock.

## What it simulates versus what is real

- **Real:** every chat turn, every capsule tap, style selection (tapping one of the greeting's
  three style buttons), the nickname in the greeting (`PUT /v1/profile`), framework offers, the somatic hand-off, the exercise hand-off, crisis locking. All of it
  goes over HTTP to the actual FastAPI app - nothing here calls `orchestrator.py` directly.
- **Real, too:** the sign-in that happens automatically on load, through Supabase Auth. The
  backend verifies the token exactly as it will a phone's, and it is refreshed when it expires.
- **Fixed, on purpose:** there is no sign-up or sign-in screen. The app always signs in as
  `CHAT_TESTER_FIXED_USER` (one name, one account, created via the Admin API the first time
  it's needed) - a public link to this tool can never create or reach any other account.

## Setup

```bash
cd chat-tester
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env` from `supabase status -o env`: `API_URL`, `ANON_KEY`, `SERVICE_ROLE_KEY` and
`DB_URL`. None of them is a secret for local Supabase.

A 401 "Your session has expired" on the very first call means the backend cannot verify real
Supabase tokens. Local Supabase signs them with a published key set, so `backend/.env` needs
`SUPABASE_URL` pointing at it (`http://127.0.0.1:54341`) and `SUPABASE_JWT_SECRET` left blank.

## Running

The backend has to already be running:

```bash
cd backend && source .venv/bin/activate && supabase start && fastapi dev main.py
```

Then, in another terminal:

```bash
cd chat-tester && source .venv/bin/activate && streamlit run app.py
```

There is no sign-in screen. On load, the app signs in as `CHAT_TESTER_FIXED_USER`
(`.env.example` default: `streamlit-tester`, i.e. `streamlit-tester@tester.mani.local`) -
creating that one account the first time it's needed - and resumes its conversation.
The sidebar's **New conversation** button starts a fresh thread for that same user.

## What to look at

- **The sidebar's "Framework state" panel** - a direct read of `thread_technique_state`,
  refreshed on every interaction. Watch `phase` move through a framework's stages as the
  conversation continues, and `outcome` flip from `offered` to `accepted` when you tap
  "Try it" or say so in free text. The current framework and stage also show under the title.
- **"What Mani remembers"** - a direct read of `admin.user_memory`: the patterns folded in
  from this person's earlier chats. It fills in a few seconds after **New conversation**.
- **The "Recent calls" panel** - one row per model call, in order, with token counts and
  the cached fraction. A completing framework with a matching exercise shows as two calls
  instead of one; check `admin.exercises.framework_id` if there is content to match.
- **"Last turn, raw"** - the exact `TurnOut` JSON, including `reasoning` if
  `AI_DEBUG_MODE=true` in `backend/.env`.

None of these three panels are things a real client shows - they exist here because seeing
them is the entire point of this tool.
