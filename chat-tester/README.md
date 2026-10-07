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
  three style buttons), framework offers (including the nearest fit, shown as "Try the closest fit" beside "Keep chatting"), the somatic hand-off, the exercise hand-off, crisis locking. All of it
  goes over HTTP to the actual FastAPI app - nothing here calls `orchestrator.py` directly.
- **Real, too:** the library page (sidebar **Library**, or any **Go to Library** button). It lists
  every exercise from `GET /v1/exercises` on one page, grouped by topic, each playable from its
  signed link. Go to Library opens it rather than sending a message, as the apps navigate there.
- **Real, too:** sign-in, sign-up and forgot-password, through Supabase Auth with an email and
  password. The backend verifies the token exactly as it will a phone's, and it is refreshed when
  it expires. Each account sees only its own conversations - the backend scopes every thread to
  the signed-in user. A forgotten password is reset on the page itself: email plus a new
  password, no email or code involved.
- **Open, on purpose:** anyone who can reach the page can create an account. Sign-up goes
  through the Admin API (created confirmed, no email sent), so it uses the service role key and
  every new account can spend model credit. For the same reason, anyone who can reach the page can
  reset any account's password and read its conversations. Don't put a link to this tool anywhere public.

## Deploying this

One thing to set beyond the environment variables above.

**Where sessions are kept.** A signed-in session lives in a file on the instance that handled the
sign-in, so a reload is recognised by that instance. On one container - how this tool is run - that
is every reload. Behind more than one replica a reload that lands elsewhere falls back to the login
screen, which is no worse than not having this at all and never an error. `CHAT_TESTER_SESSION_DIR`
points it at a mounted volume so sessions survive a restart.

Leave `CHAT_TESTER_DEV_MODE` unset on anything a client sees, and remember sign-up is open to
anyone who can reach the page: every new account can spend model credit.

## Setup

```bash
cd chat-tester
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env` from `supabase status -o env`, into the names `.env.example` uses: `SUPABASE_URL`
(from `API_URL`), `SUPABASE_ANON_KEY` (from `ANON_KEY`), `SUPABASE_SERVICE_ROLE_KEY` (from
`SERVICE_ROLE_KEY`) and `DATABASE_URL` (from `DB_URL`), plus `API_BASE_URL` for the backend. None of
them is a secret for local Supabase. Use the ports `supabase status` prints: `.env.example` says
`5434x` (what `backend/supabase/config.toml` asks for), and a local instance may answer on
`54321`/`54322` instead.

A 401 "Your session has expired" on the very first call means the backend cannot verify real
Supabase tokens. Local Supabase signs them with a published key set, so `backend/.env` needs
`SUPABASE_URL` pointing at it (`http://127.0.0.1:54321` or `:54341`, whichever `supabase status` shows) and `SUPABASE_JWT_SECRET` left blank.

## Running

The backend has to already be running:

```bash
cd backend && source .venv/bin/activate && supabase start && fastapi dev main.py
```

Then, in another terminal:

```bash
cd chat-tester && source venv/bin/activate && streamlit run app.py
```

The app opens on a **Sign in** / **Sign up** screen. Sign up takes an email, a password and an
optional nickname the greeting uses; after that, the same email and password sign back in to the
same conversations. **Forgot password** takes the account's email and a new password (twice) and,
on submit, sets that password and signs you in. Refreshing the browser tab keeps you
signed in - the session is remembered for seven days. The sidebar's **Sign out** switches
accounts, and **New conversation** starts a fresh thread for the signed-in user. Under it,
**Conversations** lists that user's threads, most recently active first (the latest 20, titled once a
thread has had an exchange, "Untitled" before that). Tap one to open it and continue; the open one is
marked ▶. Hover a title to see its message count and last activity. An opened thread shows its latest 100
messages, with Mani's buttons live only on its newest message, as in the apps.

## Tests

```bash
cd chat-tester && source .venv/bin/activate && pip install -r requirements-dev.txt
pytest
```

They sign up, reset and delete real accounts on the local Supabase in `.env`, and skip when it is
not running. Never point them at a hosted project.

## What to look at

The three developer panels below only appear with `CHAT_TESTER_DEV_MODE=1` in `chat-tester/.env`
**and** the sidebar's "Show developer details" toggle switched on. "What Mani remembers" shows without
them. The developer view lists an offer's framework id but not whether the offer was a confident one
or the nearest fit; the button's label ("Try it" or "Try the closest fit") is how you tell.

- **The sidebar's "Framework state" panel** - a direct read of `thread_technique_state`,
  refreshed on every interaction. Watch `phase` move through a framework's stages as the
  conversation continues, and `outcome` flip from `offered` to `accepted` when you tap
  "Try it" or say so in free text. The current framework and stage also show under the title.
- **"What Mani remembers"** - a direct read of `admin.user_memory`: the patterns folded in
  from this person's earlier chats. It fills in a few seconds after **New conversation**.
- **The "Recent calls" panel** - one row per model call, in order, with token counts and
  the cached fraction. A completing framework shows as two calls instead of one: the second is
  the `exercise_select` pick from the library catalog.
- **"Last turn, raw"** - the exact `TurnOut` JSON, including `reasoning` if
  `AI_DEBUG_MODE=true` in `backend/.env`.

None of these three panels are things a real client shows - they exist here because seeing
them is the entire point of this tool.
