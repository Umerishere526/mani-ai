# Port status

What the backend does today and what is still open. Stack notes: `.claude/BACKEND.md`. Database rules:
`.claude/SUPABASE.md`. Why it is built this way: `mani-vault/Decisions/_Index.md`. **Update this file in
the same change as the work.**

History (how the port went, what was fixed from review, old measurements) is in
`mani-vault/Journal/port-history-2026-09.md`. It is accurate as of the end of the port, not as of today.

## Status, 2026-10-05

- The TypeScript to Python port is complete. FastAPI is the only thing that touches the database.
- Tests: `pytest` runs 938 passed, 4 skipped (the four symmetric-token auth tests, which skip on a
  JWKS-configured project).
- Database: 12 migrations, 15 tables (8 `public`, 7 `admin`), 6 frameworks and 5 prompts seeded.
  `admin.exercises` holds the 17 library exercises from `content/exercises/`, with their audio in the
  private `exercises` bucket (`scripts/seed_exercises.py`). A hosted deployment exists (see `b865adf`).
- Models: `google/gemini-3.1-flash-lite` for chat and `openai/gpt-oss-120b` for summaries (`mani/config.py`).
- Web and mobile do not call this API yet; they run on placeholder data.

## What the service does

- **Auth** (`mani/auth/`): HS256 or JWKS, audience checked, `alg: none` refused. Admin is
  `app_metadata.admin_role == 'admin'` and `user_metadata` cannot grant it.
- **Database** (`mani/db/`): `as_user()` opens a transaction as `mani_service` with the caller's claims set, so RLS
  applies to real traffic. `as_admin()` is the named exception. A turn's writes share one transaction.
- **A chat turn** (`mani/chat/orchestrator.py`), in order:
  1. The deterministic safety screen (`safety.py`) runs before anything else. An explicit statement locks
     the thread with no model call. An indirect one (including passive ideation and "pills in my hand")
     is a concern: it suspends frameworks and offers without locking. Phrases match as whole words, after
     reading digits inside a word as letters ("k1ll") and "kms" / "unalive" as what they mean. A denied
     phrase ("I would never…", "I do not want to…") is not counted; hyperbole ("makes me want to…", "die of
     embarrassment"), someone else's safety, and harm wished on another person without a plan ("I want to
     kill my husband") ask rather than lock; a plan or a weapon ("confront him with a knife") locks.
     `tests/unit/test_safety_recall.py` is the labelled table.
  2. A whole message asking to stop a running framework ends it with no model call: outcome `stopped`, the
     specification's "You want to stop here. Would you like to continue chatting?" and Chat More / Go to
     Library (ADR-014).
  3. The router (`router.py`) shortlists frameworks from phrases over their last four messages. It is a
     hint, never a requirement; only a confident match carries its offer wording.
  4. `context.py` builds the `[ctx]` block: style, offer timing, the stage in progress, how many times the
     stage has been asked (from the third, Mani is told to move on or offer to stop), and `their_last`
     (a vague reply, a correction, a request only to be heard, or a word about how Mani is talking,
     `about_mani`). Nothing is offered on a correction, `heard` or `about_mani` turn.
  5. One model call (`mani/llm/`, LangChain on OpenRouter) returns a structured reply: `reasoning`, `style`,
     `heading_toward`, `offer_fit`, then `text`. The order is deliberate.
  6. `redraft.py` may ask once more: a feeling the person never named, any stock empathy ("that sounds",
     "it makes sense", "I hear you"), an instruction of Mani's own outside a framework ("focus on your
     breathing"), an offer that also asks its own question, an offer before it is allowed or one their
     words rule out, or the last reply's question asked again. A reply with no question is not a reason
     (ADR-015, ADR-016). ADR-006, ADR-011, ADR-012.
  7. `repairs.py` corrects what remains, in code: script leakage, dashes (every em or en dash becomes a
     comma), buttons, an early offer, an unnamed feeling.
  8. Crisis, the reply, the framework state and the summary are written together.
- **Frameworks** (`content/frameworks/*.md`, seeded to `admin.frameworks`): six, each reviewed against the
  client's specification. A confident offer may come from the person's second message (third for ABCDE,
  Thought Reframe and ACT); the nearest fit may be offered from the fourth, with "Try the closest fit"
  beside "Keep chatting", and is never owed by a count (ADR-012). Every offer carries the framework's
  `summary`: its name, the client's sentence, its steps and "You can stop at any point" (ADR-013; the added
  wording awaits the client's sign-off). The shared body check-in and practice come from `content/prompts/somatic.md`.
  The body route is held in code (`orchestrator._body_route_step`): the check-in is asked once; whatever
  the person answers, the next reply asks where, with Chest / Head / Stomach / Somewhere else; "idk" asks
  again; a place gets the client's practice for that place and style, word for word, ending "How do you feel
  now?". The framework is not retired, and Chat More / Go to Library do not appear, until a practice has been
  given or they decline. Saying what they will do next no longer skips it: a reply that jumps to the two
  choices gets the check-in itself when nothing they said was about their body. "It comes back" gets the client's waves reply for the
  style.
- **Memory** (ADR-005): per person, folded from earlier chats by `mani/memory.py` when a new chat starts;
  idle threads fold only through `scripts/fold_idle_threads.py`. `GET /internal/cron/fold-summaries` behind
  `CRON_SECRET` reconciles thread summaries, not memory (the idle-fold route exists only in an unapplied
  stash, see `mani-vault/Journal/git-state-2026-10-04.md`).
- **Exercises**: catalog, completions and signed URLs (`mani/storage.py`). A completing framework picks one
  exercise from the whole active catalog with one bound tool call (`mani/llm/tools.py`): the framework's own
  exercises are listed first, and the pick sees the person's last three messages and the thread's current
  issue. `GET /v1/exercises` is the whole catalog, and responses never carry the storage path.
- **Admin**: prompt CRUD with versioning, exercise CRUD, crisis event review, a user's memory.
- **Account deletion**: `DELETE /v1/account` removes the user and everything they own.
- **Error reports** (`main.py`): Sentry gets no request body, no frame locals and no breadcrumbs.
  `llm_calls.error_message` and the model client's `ServiceError` messages name a failure by kind and
  status, never its text. A chained third-party exception's message still reaches Sentry.
- **Eval harness**: `scripts/eval_replies.py` runs scripted conversations through the real stack and removes
  the users it created. `tests/evals/` holds the deterministic checks every suite runs.

## The API

| Method | Path | |
|---|---|---|
| GET | `/health`, `/health/ready` | liveness, readiness |
| GET PUT | `/v1/profile` | onboarding answers |
| GET POST | `/v1/threads` | list, start (writes the greeting) |
| POST | `/v1/threads/current` | what to show on opening the app; creates a thread on first call |
| GET PATCH DELETE | `/v1/threads/{id}` | fetch, set `conversation_style`, soft delete |
| GET POST | `/v1/threads/{id}/messages` | history (paged), **send a turn** |
| GET | `/v1/exercises`, `/home`, `/{id}` | catalog with signed audio |
| GET POST | `/v1/exercises/completions` | a user's completions |
| GET | `/v1/crisis/resources` | empty until real services exist |
| DELETE | `/v1/account` | delete the account and its data |
| GET POST | `/v1/admin/prompts` | portal |
| GET PATCH | `/v1/admin/prompts/{id}` | patch snapshots the old version first |
| GET | `/v1/admin/prompts/{id}/versions` | history |
| POST | `/v1/admin/prompts/cache/invalidate` | publish now |
| GET POST, PATCH DELETE | `/v1/admin/exercises`, `/{id}` | catalog CRUD |
| GET | `/v1/admin/crisis-events` | review queue |
| GET | `/v1/admin/users/{id}/memory` | what is remembered about a person |
| GET | `/internal/cron/fold-summaries` | overdue thread summaries, bearer `CRON_SECRET`, no JWT |

## Decisions in force

The record is `mani-vault/Decisions/_Index.md`. In short:

- **A turn is one model call, or two when a draft is redrafted** (ADR-002, 006). The one scoped extra
  call is the exercise pick at the end of a framework. `test_a_turn_costs_exactly_one_provider_call` still
  holds for a draft that needs no redraft.
- **Offers follow Mani's confidence** (ADR-007, 012). Every reply before an offer ends in one question, by the
  prompt alone with no redraft; questions never chase a framework's missing fields (ADR-015, ADR-016).
- **Memory is per person** (ADR-005).
- Settled without an ADR yet, listed at the foot of the index: OpenRouter only, asyncpg not PostgREST, the
  `public` and `admin` split, the `mani_service` role, three security definer write functions, the
  deterministic safety screen as the only thing that locks a thread, in process routing, no streaming.

## Before it takes real traffic

Ordered by what breaks first.

1. **Hosted Data API settings.** `supabase/config.toml` configures local development only. On a hosted
   project set `auto_expose_new_tables` off and the exposed schemas to `public` and `graphql_public` by hand;
   `db push` does not carry them. Run `scripts/test_db.sh --local` against the hosted database first, or a
   user could clear their own crisis flag.
2. **Rate limit and cost ceiling.** `DAILY_MESSAGE_LIMIT` exists and defaults to 0 (off). It needs a number
   from muhammad. There is no per user cost ceiling; `llm_calls.spend_since()` is what one would read. A retried
   send with the same `client_message_id` returns the first reply for free.
3. **Crisis resources are empty.** `mani/chat/crisis.py` returns `[]`, and `safety.PROTOCOLS` and
   `CLARIFICATION` are empty too: the specifications refer to an approved protocol and do not contain one.
   Needs countries and services from muhammad. Do not invent numbers. The screen's phrase lists and which
   level each reads at are engineering's reading of the specification and have had no clinical review.
4. **Migrations are not run by anything.** `supabase db push` is manual.
5. **Memory fold and summaries need a scheduler.** Summaries run as in process background tasks (lost on a
   crash). The cron route exists but nothing calls it. Hosting is not decided: a container platform that can
   run two process types from one image (`vercel.json` and `render.yaml` were removed).
6. **`CORS_ORIGINS` must name the deployed web origin**, or `web/` gets no browser response. Mobile is
   unaffected.
7. **Pool and load.** `mani/db/pool.py` is min 2, max 10 with a 90 second command timeout, sized by reasoning.
   A turn holds a transaction open across every model call while each call records `llm_calls` on a
   second connection, so about 10 concurrent turns deadlock the pool, not merely queue (audit 2026-10-04,
   CF-5, not yet reproduced here); `acquire()` has no timeout and `/health/ready` hangs with it. Any
   `idle_in_transaction_session_timeout` below the model's latency kills turns. Nothing has been load
   tested. `config.py` also defines `db_pool_*` settings that nothing reads.
8. **The backend's database role.** `001_initial_schema.sql` grants `mani_service` to `postgres`. If the
   deployed `DATABASE_URL` connects as anything else, `set local role mani_service` fails. Grant it to that role,
   never to `authenticator`.
9. **Email confirmation is not enforced** and **app attestation is absent.** Confirmation needs
   `enable_confirmations` in Supabase and SMTP; do not read `email_verified` from the token, because the user can
   write it. Attestation layers on after the rate limit, in front of the chat endpoint only.

## Open decisions for muhammad

- Crisis resources, `PROTOCOLS` and `CLARIFICATION` wording (point 3 above).
- Tell the client about ADR-007, which replaced their offer cadence, and have them read about five real
  Supportive and Reflective transcripts.
- Tell the client about ADR-011: when a person asks Mani to pick, it offers one small draft step to accept
  or change, which the Behavioral Activation specification's "must not choose the activity" does not allow
  as written.
- Tell the client about ADR-010: after Try it Mani no longer asks the first stage's question when the person
  has already said it, and a person who cannot say what to do is offered up to three options at the first
  "I don't know". Both depart from the literal Structured Problem Solving example.
- Panic with no action in sight: the overview sends it to DBT STOP, the STOP specification is written around an
  action about to be taken. The client's call.
- Whether a crisis turn should hand off to an exercise. Left out on purpose; do not add it as a missing branch.
- Whether a person should see or erase their memory short of deleting the account (ADR-005).
- The three styles still differ little in length and question rate. Schema field order was the lever that worked
  for openers; more prose rules did not.
- Revisit the grief veto (Behavioral Activation after loss words) with real transcripts.

## Open engineering

- **Body route, from the client's 2026-10-02 flow.** Still the client's to confirm: Chat More / Go to Library
  keep their labels, where the new document says "take me to the library" / "want to keep chatting"; the
  Reflective chest line was a fragment and is sent with its grammar fixed; the "somewhere else" practice has
  no client wording and the three style versions are ours, written from their Ground specification. The
  practice now carries no buttons, as in the new document. In the scripted eval, Direct can stall in a
  framework's own closing stage (`panic_somatic_once`), which is the model not advancing, not the body route.
- **Generated TypeScript types** for `web/` and `mobile/` from the OpenAPI schema, with a CI gate. No CI exists.
- **Admin audio upload.** The 17 seeded exercises come from `content/exercises/` through
  `scripts/seed_exercises.py`; there is no upload route, and the admin exercise CRUD takes an existing
  `audio_path`. The exercise card is also not kept on the message, so it is gone once a thread reloads.
- **A worker process** for summaries and the memory fold, for when there is more than one instance.
- **Admin conversation browser**: do not rebuild it as a general reader. Scope it to threads with an unresolved
  crisis event, log each read, and return metadata by default.
- **`GET /v1/admin/models`**, which the prompt editor's model dropdown needs.
- **`threads.vague_streak`** is granted to the backend and written by nothing; the pacing it belongs to is
  designed, not built.
- **`appropriate_when` and `not_when`** in the framework files are read by nothing (each file says so).
- The words "worried", "concerned" and "a lot" still reach about 1 reply in 10 in some scenarios; repairs log
  them. The feeling check now redrafts the ones in `repairs.FEELING_WORDS`.

## Latest measurements

Taken 2026-10-01 with `scripts/eval_replies.py`, three runs of four scenarios, every style. Re-measure after any
change to prompts, framework content or the offer rules, and compare with these.

- Reached an offer: 36 of 36 conversations (grief had been 1 of 9). First offers at message 2 to 4.
- Redrafts: 7% of replies across scenarios, 17 to 19% on the hardest chat (a colleague, an embarrassing
  meeting). ADR-006 sets about 10% as the line to watch on real traffic.
- Lost wallet chat (panic), three runs: the confirmation question after Try it went from 9 of 9 to 0 of 6
  (ADR-010); the bank step comes in the first or second reply. Three options at the first "I don't know" is
  still the minority.
- Behavioral Activation chat (comparing with others online), three runs: the first question after Try it asked
  for what they had stopped doing, a request to pick got one draft step in 4 of 6, and two of three runs
  reached the body check (ADR-011). One wallet start in five still asked for the problem again.
- Replies with no question before an offer: 1 of 39 on that chat (from 8 of 47).
- Wrong framework offered early: Direct chose ACT or a plan for a colleague chat that wants ABCDE, until offers
  for ABCDE, Thought Reframe and ACT were made to wait for the third message (Direct then chose ABCDE 3 of 3).
- Local Supabase answers on 54321 to 54324 on this machine, not the 5434x in `config.toml`. See
  `.claude/BACKEND.md`.
