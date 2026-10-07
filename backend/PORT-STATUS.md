# Port status

What the backend does today and what is still open. Stack notes: `.claude/BACKEND.md`. Database rules:
`.claude/SUPABASE.md`. **Update this file in
the same change as the work.**

## Status, 2026-10-01

- The TypeScript to Python port is complete. FastAPI is the only thing that touches the database.
- Tests: `pytest` runs 798 passed, 4 skipped (the four symmetric-token auth tests, which skip on a
  JWKS-configured project).
- Database: 10 migrations, 15 tables (8 `public`, 7 `admin`), 6 frameworks and 5 prompts seeded.
  `admin.exercises` holds the 17 library exercises from `content/exercises/`, with their audio in the
  private `exercises` bucket (`scripts/seed_exercises.py`). A hosted project does not exist yet.
- Models: `openai/gpt-6-luna` for chat and for summaries (`mani/config.py`), routed Azure first with
  OpenAI as the fallback. It is a reasoning model: it takes no `temperature` on any provider and reads
  `reasoning_effort` instead, so `mani/llm/chain.py` sends the sampling parameters an ordinary
  chat model takes only to models that accept them. A prompt row names its own effort in
  `model_parameters.reasoning_effort` and `mani/config.py` holds the default for the calls that have
  no row of their own; `mani_base`, `summarization` and `memory_fold` are all on `high`. Effort is
  billed: measured against Azure, `high` spent 26 reasoning tokens where `low` spent 0, about three
  times the cost of the same call. The fallback keeps `data_collection: deny`, so
  training use stays refused, but a turn that cannot reach Azure is processed by a different company -
  a data protection question that is open, not settled.
- Every call to OpenRouter carries the same provider order, data policy and reasoning effort, from
  `chain.request_body`. The voice translation in `mani/stt.py` calls the SDK directly and used to send
  none of them, so a transcript went to whichever provider OpenRouter chose; it now uses the same body.
  It is still not recorded in `admin.llm_calls`, which has no purpose for it.
- A reasoning model's output budget covers its thinking and its reply together. Every caller sizes
  `max_tokens` for the reply alone, so `chain.sampling` adds `REASONING_ALLOWANCE_TOKENS` (8,192) on top.
  Without it, at effort high, 4 of 61 chat calls ran out of tokens while thinking and the turn failed
  (2026-10-07). Measured at high: 12.6 s for an average turn, 41 s for the longest.
- `mani_base.md` and `response_format.md` are YAML rules rather than prose (ADR-012): about 10,600 tokens
  became 4,850. The Framework Index and the per-framework rules are not restructured yet.
- Web and mobile do not call this API yet; they run on placeholder data.

## What the service does

- **Auth** (`mani/auth/`): HS256 or JWKS, audience checked, `alg: none` refused. Admin is
  `app_metadata.admin_role == 'admin'` and `user_metadata` cannot grant it.
- **Database** (`mani/db/`): `as_user()` opens a transaction as `mani_service` with the caller's claims set, so RLS
  applies to real traffic. `as_admin()` is the named exception. A turn's writes share one transaction.
- **A chat turn** (`mani/chat/orchestrator.py`), in order:
  1. The deterministic safety screen (`safety.py`) runs before anything else. An explicit statement locks
     the thread with no model call. An indirect one (including passive ideation and "pills in my hand")
     is a concern: it suspends frameworks and offers without locking.
  2. The router (`router.py`) shortlists frameworks from phrases over their last four messages. It is a hint, never a requirement. When the nearest fit falls due, the top of the shortlist carries its offer wording even if the router is not confident of it.
  3. `context.py` builds the `[ctx]` block: style, offer timing, the stage in progress, and `their_last`
     (a vague reply, a correction, or a request only to be heard).
  4. One model call (`mani/llm/`, LangChain on OpenRouter) returns a structured reply: `reasoning`, `style`,
     `heading_toward`, `offer_fit`, then `text`. The order is deliberate.
  5. `redraft.py` may ask once more (twice for a missing question): a feeling the person never named, an
     offer before it is allowed or one their words rule out, an offer that is due and missing, no
     question, or the last reply's question asked again.
  6. `repairs.py` corrects what remains, in code: script leakage, buttons, an early offer, an unnamed feeling.
  7. Crisis, the reply, the framework state and the summary are written together.
- **Frameworks** (`content/frameworks/*.md`, seeded to `admin.frameworks`): six, each reviewed against the
  client's specification. A confident offer may come from the person's second message (third for ABCDE,
  Thought Reframe and ACT); the nearest fit is due by the fourth, with "Try the closest fit" beside
  "Keep chatting". The shared body check-in and practice come from `content/prompts/somatic.md`.
  The body route is held in code (`orchestrator._body_route_step`): the check-in is asked once; whatever
  the person answers, the next reply asks where, with Chest / Head / Stomach / Somewhere else; "idk" asks
  again; a place gets the client's practice for that place and style, word for word, ending "How do you feel
  now?". The framework is not retired, and Chat More / Go to Library do not appear, until a practice has been
  given (or they decline, or say what they will do). "It comes back" gets the client's waves reply for the
  style.
- **Memory**: per person, folded from earlier chats by `mani/memory.py`; idle threads fold through
  `scripts/fold_idle_threads.py` or `GET /internal/cron/fold-summaries` behind `CRON_SECRET`.
- **Exercises**: catalog, completions and signed URLs (`mani/storage.py`). A completing framework picks one
  exercise from the whole active catalog with one bound tool call (`mani/llm/tools.py`): the framework's own
  exercises are listed first, and the pick sees the person's last three messages and the thread's current
  issue. `GET /v1/exercises` is the whole catalog, and responses never carry the storage path.
- **Admin**: prompt CRUD with versioning, exercise CRUD, crisis event review, a user's memory.
- **Account deletion**: `DELETE /v1/account` removes the user and everything they own.
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
| GET | `/internal/cron/fold-summaries` | idle memory fold, bearer `CRON_SECRET`, no JWT |

## Decisions in force

- **A turn is one model call, or more when a draft is redrafted**. The one scoped extra
  call is the exercise pick at the end of a framework. `test_a_turn_costs_exactly_one_provider_call` still
  holds for a draft that needs no redraft.
- **Offers follow Mani's confidence**. Every reply before an offer asks one question.
- **Memory is per person**.
- Also settled: OpenRouter only, asyncpg not PostgREST, the
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
   Needs countries and services from muhammad. Do not invent numbers.
4. **Migrations are not run by anything.** `supabase db push` is manual.
5. **Memory fold and summaries need a scheduler.** Summaries run as in process background tasks (lost on a
   crash). The cron route exists but nothing calls it. Hosting is not decided: a container platform that can
   run two process types from one image (`vercel.json` and `render.yaml` were removed).
6. **`CORS_ORIGINS` must name the deployed web origin**, or `web/` gets no browser response. Mobile is
   unaffected.
7. **Pool and load.** `mani/db/pool.py` is min 2, max 10 with a 90 second command timeout, sized by reasoning.
   A turn holds a transaction open across the model call, so about 10 turns per process is the ceiling, and
   any `idle_in_transaction_session_timeout` below the model's latency kills turns. Nothing has been load
   tested. `config.py` also defines `db_pool_*` settings that nothing reads.
8. **The backend's database role.** `001_initial_schema.sql` grants `mani_service` to `postgres`. If the
   deployed `DATABASE_URL` connects as anything else, `set local role mani_service` fails. Grant it to that role,
   never to `authenticator`.
9. **Email confirmation is not enforced** and **app attestation is absent.** Confirmation needs
   `enable_confirmations` in Supabase and SMTP; do not read `email_verified` from the token, because the user can
   write it. Attestation layers on after the rate limit, in front of the chat endpoint only.

## Open decisions for muhammad

- Crisis resources, `PROTOCOLS` and `CLARIFICATION` wording (point 3 above).
- Tell the client that offers now follow Mani's confidence, with the nearest fit due by the fourth message, which replaced their offer cadence, and have them read about five real
  Supportive and Reflective transcripts.
- Tell the client: when a person asks Mani to pick, it offers one small draft step to accept
  or change, which the Behavioral Activation specification's "must not choose the activity" does not allow
  as written.
- Tell the client: after Try it Mani no longer asks the first stage's question when the person
  has already said it, and a person who cannot say what to do is offered up to three options at the first
  "I don't know". Both depart from the literal Structured Problem Solving example.
- Panic with no action in sight: the overview sends it to DBT STOP, the STOP specification is written around an
  action about to be taken. The client's call.
- Whether a crisis turn should hand off to an exercise. Left out on purpose; do not add it as a missing branch.
- Whether a person should see or erase their memory short of deleting the account.
- The three styles still differ little in length and question rate. Schema field order was the lever that worked
  for openers; more prose rules did not.
- Revisit the grief veto (Behavioral Activation after loss words) with real transcripts.

## Open engineering

- **The hosted database is seven migrations ahead of this code.** `main` was reverted to `1473a0c`,
  which ships migrations 001-010, but hosted still has 011-017 applied from the reverted branches:
  `holds`, `known`, `ending` and `phase_since` on `thread_technique_state`, `decision` on
  `admin.llm_calls`, the `public.framework_outcomes` table, and `'stopped'` on the
  `technique_outcome` enum. Hosted holds live data in them - 2 `framework_outcomes` rows, 55
  `llm_calls.decision` rows - so a rollback destroys data. `016` cannot be undone at all: Postgres
  has no `drop value` for an enum, so retiring it means recreating the type or writing a new
  migration forward. Local was reset to 001-010 on 2026-10-07; hosted was not. The two are not the
  same schema, and nothing reconciles them yet.
- **Migration numbers were reused across the reverted branches.** `011` was both
  `technique_state_holds` and `technique_outcome_stopped`; `013` was both `llm_call_decision` and
  `llm_call_facts`. Reviving any of those branches collides again.


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
  meeting). About 10% is the line to watch on real traffic.
- Lost wallet chat (panic), three runs: the confirmation question after Try it went from 9 of 9 to 0 of 6;
  the bank step comes in the first or second reply. Three options at the first "I don't know" is
  still the minority.
- Behavioral Activation chat (comparing with others online), three runs: the first question after Try it asked
  for what they had stopped doing, a request to pick got one draft step in 4 of 6, and two of three runs
  reached the body check. One wallet start in five still asked for the problem again.
- Replies with no question before an offer: 1 of 39 on that chat (from 8 of 47).
- Wrong framework offered early: Direct chose ACT or a plan for a colleague chat that wants ABCDE, until offers
  for ABCDE, Thought Reframe and ACT were made to wait for the third message (Direct then chose ABCDE 3 of 3).
- Local Supabase answers on 54321 to 54324 on this machine, not the 5434x in `config.toml`. See
  `.claude/BACKEND.md`.
