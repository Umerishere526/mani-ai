# chat-tester

A small Streamlit UI for having real conversations against the running backend - to feel
when a framework gets offered, when the somatic hand-off happens, and when it lands on an
exercise, before tuning any of that behaviour further in the LangChain prompts or config.

**This is a fourth, independent thing in this repo, alongside `web/`, `mobile/` and
`backend/` - not part of any of them.** It has its own dependencies and does not touch
backend code. Every message it sends goes through the real `POST /v1/threads/{id}/messages`
endpoint (a conversation's first message through `POST /v1/threads`, which creates it), the real LangChain call, the real router and safety screen - this is not a mock.

## What it simulates versus what is real

- **Real:** every chat turn, every capsule tap, style selection (tapping one of the greeting's
  three style buttons), framework offers (the lead-in, the five steps and Start), the feelings check after the last stage, the crisis pause (a centred pop-up that leads with where to get help - 988 to call or text, 911, findahelpline.com outside the US, Get help now and Visit library, with 911 first when the danger is to someone else, from someone or in the body, and "Call 911 now." first after an overdose - and only beneath it, smaller, that the chat is paused, for how long and about how many minutes are left; no ticking clock; closing it keeps the help lines above the readable conversation, and the Library stays open). All of it
  goes over HTTP to the actual FastAPI app - nothing here calls the chat code directly.
- **Real, too:** the library page (sidebar **Library**, or any **Visit library** button). It lists
  every exercise from `GET /v1/exercises` on one page, grouped by topic, each playable from its
  signed link in one player with 10-second skips; stories also get 0.5x, 1x, 1.5x or 2x speed. Under
  each player 👍/👎 saves the person's rating at once, then an optional reason and Submit; an admin
  reviews every rating under **Library feedback**, filtered by email. Visit library opens it rather
  than sending a message, as the apps navigate there.
- **Real, too:** sign-in and sign-up, through Supabase Auth with an email and password and the
  publishable (anon) key alone. The backend verifies the token exactly as it will a phone's, and it is
  refreshed when it expires. Each account sees only its own conversations - the backend scopes every
  thread to the signed-in user. There is no password reset on the page: a forgotten password is reset
  from the Supabase dashboard (or the Auth Admin API).
- **Open, on purpose:** anyone who can reach the page can create an account, through Supabase Auth's
  public signup, and every new account can spend model credit. Don't put a link to this tool anywhere
  public.

## Admin: reading everyone's conversations

An admin account sees every person's conversations, read-only, to review how beta chats pace themselves. It
gets no composer, no New conversation and no buttons that send anything, and the backend refuses a chat message
from an admin token whatever the page does. The sidebar groups conversations under each person, people ordered by
their most recent activity and each person's conversations newest first (searchable by email or user id, 🚨
marks a crisis flag, and each title carries the style Mani spoke in, e.g. "(Directive)"); opening one shows every message with its time and the gap since the
message before (`+2m`, `+1h 5m`), and which button the person tapped. Each opened conversation is logged by the
backend in `admin.thread_reads`.

To make an account an admin, sign it up here first, then from `backend/`:

```bash
source .venv/bin/activate && python scripts/grant_admin.py admin@example.com
```

It takes effect at the account's next sign-in (or a reload, which refreshes the token). `--revoke` undoes it.
Several admins are fine; each is granted the same way.

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
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env` from `supabase status -o env`, into the names `.env.example` uses: `SUPABASE_URL`
(from `API_URL`), `SUPABASE_ANON_KEY` (from `ANON_KEY`) and `DATABASE_URL` (from `DB_URL`), plus
`API_BASE_URL` for the backend. None of them is a secret for local Supabase. No service role key is
needed. Use the ports `supabase status` prints: `.env.example` says
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
cd chat-tester && source .venv/bin/activate && streamlit run app.py
```

The app opens on a **Sign in** / **Sign up** screen. Sign up takes an email, a password and an
optional nickname the greeting uses; after that, the same email and password sign back in to the
same conversations. A project that confirms accounts itself (the hosted mani-app) signs you straight
in. Local Supabase emails a confirmation link first (`enable_confirmations` in
`backend/supabase/config.toml`), so the page says to open it; the email lands in the local mail
catcher (`[local_smtp]`, http://127.0.0.1:54344), and the nickname is then set from the sidebar. Refreshing the browser tab keeps you
signed in - the session is remembered for seven days. The sidebar's **Nickname** field changes
the name the greeting uses, from the next new conversation. Every message has a copy icon under it,
in the chat and in the admin viewer. **Sign out** switches
accounts, and **New conversation** shows a fresh opening for the signed-in user: Mani's greeting, with "I'm MANI, an AI
companion, not a therapist." under it, and the three style buttons. Nothing is stored until the first message sent, which creates the conversation (with the style
tapped, if any), so an opening nobody wrote in never appears in the list, and a reload opens the latest conversation
instead of it. Under it,
**Conversations** lists that user's threads, most recently active first (the latest 20, titled once a
thread has had an exchange, "Untitled" before that). Tap one to open it and continue; the open one is
marked ▶. Hover a title to see its message count and last activity. An opened thread, or a reloaded
tab, shows the whole conversation, with Mani's buttons live only on its newest message, as in the apps.

## Tests

```bash
cd chat-tester && source .venv/bin/activate && pip install -r requirements-dev.txt
pytest
```

`test_sign_up.py` signs up and deletes real accounts on the local Supabase in `.env`, and skips when it
is not running. Never point it at a hosted project. Every other test runs against fakes and needs no
service, not even the backend.

## What to look at

The three developer panels below only appear with `CHAT_TESTER_DEV_MODE=1` in `chat-tester/.env`
**and** the sidebar's "Show developer details" toggle switched on. "What Mani knows" shows without them: Mani's notes, the
people and events they spoke of, the replies ledger (each reply's move and gist, the question it asked and their
answer) and the frameworks declined or finished, all sent only while `AI_DEBUG_MODE=true` in `backend/.env`. An offer
shows the client's steps as the backend sends them: the lead-in's buttons (Not sure / Show me how / Give me a tool),
the five steps with Start and Talk more first, and after the last stage how they feel.

- **The sidebar's "Framework state" panel** - a direct read of `thread_technique_state`,
  refreshed on every interaction. Watch `phase` move through a framework's stages as the
  conversation continues, and `outcome` flip from `offered` to `accepted` when you tap
  Start or say yes after the five steps. The current framework and stage also show under the title.
- **The "Recent calls" panel** - one row per model call, in order, with token counts and
  the cached fraction. Every turn is one call; a completing framework no longer makes a second one.
- **"Last turn, raw"** - the exact `TurnOut` JSON, including `reasoning` if
  `AI_DEBUG_MODE=true` in `backend/.env`.

None of these three panels are things a real client shows - they exist here because seeing
them is the entire point of this tool.
