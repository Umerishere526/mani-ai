# Port status

The TypeScript→Python port is **complete**. `reference/` is gone; every file in it has a
Python counterpart under test. What follows is what landed, what changed on the way, and
what is still open.

Conventions and stack notes: `.claude/BACKEND.md`. Database rules: `.claude/SUPABASE.md`.

Legend: `[ ]` not started · `[~]` in progress · `[x]` done and tested

---

## Build order

- [x] **1. Project setup** — venv, `config.py`, `errors.py`, `main.py`, `/health`, pytest
- [x] **2. Schema** — `001_initial_schema.sql`, seeded with 2 frameworks and 5 prompts.
      14 RLS and ~25 privilege assertions pass against a throwaway Postgres and against
      the real local Supabase.
- [x] **3. Auth** — `mani/auth/`. HS256 or JWKS, audience checked, `alg: none` refused.
      Admin is `app_metadata.admin_role == 'admin'`; `user_metadata` cannot grant it.
- [x] **4. Connection layer** — `mani/db/pool.py`. `as_user()` opens a transaction and
      sets the caller's claims so RLS applies; `as_admin()` is the named exception.
- [x] **4b. Row models** — `mani/models/rows.py`, frozen.
- [x] **4c. Profiles** — `public.profiles`, replacing auth `user_metadata`.
- [x] **5. Queries** — `mani/db/`. One composed read (`load_turn_context`) replaces six
      round trips; one composed write (`ThreadUpdates.apply`) replaces fourteen.
- [x] **6. Techniques** — `mani/chat/techniques.py`. Unknown framework or phase fails
      closed; the reference returned valid for both.
- [x] **7. Prompt composition** — `mani/prompts/`. Fixed layer order, TTL cache,
      `POST /v1/admin/prompts/cache/invalidate`. A missing required layer is refused.
- [x] **8. Model call** — `mani/llm/`. Timeout, SDK retries 0, structured output parsed
      into Pydantic, an `admin.llm_calls` row written on success *and* failure.
- [x] **9. Output checks** — script-leakage stripper in `mani/chat/repairs.py`. The
      three-word forbidden list dropped.
- [x] **10. Repairs** — all six deterministic. **One provider call per turn**, asserted.
- [x] **11. Crisis** — read off the first reply before any repair, a real non-empty
      answer, a `crisis_events` row with its reason and the message that triggered it.
- [x] **12. Context block** — `[ctx]` built per turn from the database snapshot, never
      persisted. `context.strip()` exists only for rows the previous system wrote.
- [x] **13. Orchestrator** — `mani/chat/orchestrator.py`. Idempotency checked at entry;
      every write in the caller's one transaction.
- [x] **14. Summarization** — `mani/summarize.py`, via OpenRouter, schema-validated,
      scheduled after the response rather than as an un-awaited coroutine.
- [x] **15. Exercises** — catalog, completions, Storage signed URLs (`mani/storage.py`).
- [x] **16. Admin endpoints** — prompt CRUD, versioning with a snapshot in the same
      transaction as the publish, exercise CRUD, crisis-event review.

## Still to do

- [ ] **Eval scenarios in pytest.** The four crisis scenarios from the old repo have
      never once run. `tests/integration/test_turn.py` covers crisis mechanically — the
      lock, the stored event, the non-empty reply — but nothing judges whether the model
      *detects* a crisis in realistic language.
- [ ] **Generated TypeScript types** for `web/` and `mobile/` from the OpenAPI schema,
      with a CI gate. See `.claude/BACKEND.md`.
- [ ] **Audio upload** from `library_audio/` into the `exercises` bucket, and the bucket
      itself. `mani/storage.py` signs paths; nothing has put files at them yet.
- [ ] **A worker process.** Summarization runs as a FastAPI background task, which is
      fine for one box and wrong for two. Hosting must support two process types.

---

## API conventions

Things a reviewer will check for, and where they are.

- **One error shape, everywhere.** `{"error": {category, message, retryable}}`. Both the
  `ServiceError` and the validation handlers in `main.py` produce it, so a client has one
  branch rather than two. FastAPI's default `{"detail": [...]}` is overridden.
- **401 and 403 are distinct.** No usable token is `unauthenticated` → 401, so a client
  refreshes. Authenticated but not permitted is `forbidden` → 403.
- **4xx does not log a stack trace.** Expired tokens are routine; a traceback each would
  bury real faults and spend the Sentry quota. 5xx logs with `exc_info`.
- **A validation error never echoes the input.** FastAPI's default includes the offending
  value, which here could be part of somebody's message.
- **`operationId` is the handler name** (`send`, `list_threads`), not FastAPI's
  `send_v1_threads__thread_id__messages_post`. These become the generated client's
  function names; uniqueness is asserted in `tests/unit/test_app.py`.
- **`response_model=` on every route.** Without it the generated schema degrades to
  `Any` and the types become decorative.
- **Every write is a POST/PATCH/DELETE.** `/v1/threads/current` creates a thread and a
  greeting on first call, so it is POST — a GET must be safe, and prefetchers treat it so.
- **Cursors are `datetime`, not `str`.** Typed loosely, a malformed cursor reached
  Postgres as a cast and returned 500 rather than a refused request.
- **Expiring state is not stored.** `prompts` come back only on Mani's newest message,
  decided at serialization. `selected_prompt` persists everywhere — what somebody chose
  is part of the conversation, what they were offered is not.

## Parity gaps against the implementation replaced

Deliberate omissions are in the table above. These are absences, tracked here so they are
not mistaken for decisions.

- [x] **Empty-thread reuse** — `threads.create_or_reuse`.
- [x] **Stale button clearing** — done at serialization instead of by mutating history.
- [ ] **Email confirmation is not enforced.** The previous system gated every procedure
      on it. The fix is `[auth.email] enable_confirmations = true` in Supabase, not a
      backend check: GoTrue then refuses to mint a session at all, so the guarantee holds
      on every endpoint rather than the ones someone remembered to decorate. Needs SMTP.
      **Do not read `email_verified` from the token** — it is in `user_metadata`, which
      the user can write. Verified by experiment: an account with nothing confirmed
      carried `email_verified: true`, and successfully wrote `admin_role: "admin"` into
      its own metadata. `app_metadata` stayed clean, which is why the admin check reads
      only from there.
- [ ] **App attestation is absent.** The previous system required it on every endpoint
      (fail-open on an unrecognised mode, MYM-88; slated for replacement, MYM-75).
      Attestation is anti-abuse, not authorization — a real device can be instrumented —
      so the rate limit and cost ceiling come first and it layers on top, in front of the
      chat endpoint only, failing closed.
- [ ] **Admin conversation browser.** The portal could list and read any user's threads.
      No equivalent here, and it should not be rebuilt as one: scope it to threads with an
      unresolved crisis event, write an `admin.access_log` row per read, and return
      metadata rather than content by default.
- [ ] **`GET /api/admin/models`** — populated the model dropdown in the prompt editor.
- [ ] **Audio upload to Storage.** `mani/storage.py` signs for reading only.

## Before it takes real traffic

Ordered by what breaks first.

1. **Hosted Data API settings.** `supabase/config.toml` configures local development
   only. On a hosted project, set `auto_expose_new_tables` off and limit the exposed
   schema list to `public` + `graphql_public` **by hand** — `db push` does not carry
   them. Left at the defaults, PostgREST grants the Data API roles access to new
   `public` tables without explicit GRANTs, which overrides the column-scoped grant
   stopping a user clearing their own `crisis_detected` flag. Run
   `scripts/test_db.sh --local` against the hosted database before it opens.
2. **No rate limit on the chat endpoint** (MYM-25, still open). One client in a retry
   loop bills the OpenRouter account at ~8k input tokens a turn. `llm_calls.spend_since()`
   is the measurement a ceiling would read; the ceiling itself needs a number.
3. **Crisis resources are empty.** `mani/chat/crisis.py` returns `[]`. The panel will
   render with nothing in it. Needs countries and services.
4. **Migrations are not run by anything.** `supabase db push` is a manual step; no
   release process invokes it.
5. **Summarization dies with the process.** A FastAPI background task is in-process, so
   a deploy or a crash drops it silently. Correct on one instance, lossy on more.
6. **`CORS_ORIGINS` must name the deployed web origin**, or `web/` gets no response at
   all from a browser. Mobile is unaffected.
7. **No load has been run, and a turn is idle-in-transaction across the model call.**
   The pool is `min 2 / max 10` with a 90-second command timeout, sized by reasoning
   rather than measurement. `as_user()` opens the transaction for the whole request and
   `orchestrator.send()` awaits the provider inside it, which buys the atomicity the
   turn needs and costs three things worth stating plainly:
   - **10 concurrent turns per process is the ceiling.** The 11th blocks on the pool.
   - **Each in-flight turn holds an open transaction for ~5 s**, holding back vacuum and
     pinning the xmin horizon on every table the turn touches.
   - **Any `idle_in_transaction_session_timeout` below the model's latency kills turns
     outright.** Supabase sets none by default; a platform or pooler in front of it may.
     Check before assuming, and if one exists it must exceed `COMMAND_TIMEOUT_SECONDS`.

   The atomicity is worth keeping — the alternative is a user message stored with no
   reply. Raising `max_size` trades memory for concurrency and is the cheap first move;
   splitting the turn into two transactions is not, and needs a decision, not a tweak.
8. **The backend's database role must exist and be assumable.** `001_initial_schema.sql`
   creates `mani_service` and grants it to `postgres`. If the deployed `DATABASE_URL`
   connects as anything other than `postgres`, `set local role mani_service` fails and
   every request 500s. Grant membership to that role too. Never to `authenticator` —
   PostgREST would then be able to assume it and the separation would be undone.

---

## The API

| Method | Path | |
|---|---|---|
| GET | `/health`, `/health/ready` | liveness, readiness |
| GET PUT | `/v1/profile` | onboarding answers |
| GET POST | `/v1/threads` | list, start (writes the greeting) |
| GET | `/v1/threads/current` | what to show on opening the app |
| GET DELETE | `/v1/threads/{id}` | fetch, soft delete |
| GET POST | `/v1/threads/{id}/messages` | history, **send a turn** |
| GET | `/v1/exercises`, `/home`, `/{id}` | catalog with signed audio |
| GET POST | `/v1/exercises/completions` | a user's completions |
| GET | `/v1/crisis/resources` | empty until real services exist |
| GET POST | `/v1/admin/prompts` | portal |
| GET PATCH | `/v1/admin/prompts/{id}` | patch snapshots the old version first |
| GET | `/v1/admin/prompts/{id}/versions` | history |
| POST | `/v1/admin/prompts/cache/invalidate` | publish now, not in five minutes |
| GET POST | `/v1/admin/exercises` | catalog CRUD |
| PATCH DELETE | `/v1/admin/exercises/{id}` | |
| GET | `/v1/admin/crisis-events` | review queue |

---

## Decisions already taken — do not re-litigate

- **OpenRouter is the only provider.** The OpenAI *SDK* is the client because OpenRouter
  speaks that protocol. No `providers` table; the key lives in the environment.
- **asyncpg direct to Postgres**, not PostgREST — a turn needs one real transaction.
- **Two schemas**: `public` (user data, RLS) and `admin` (config and analytics, never
  exposed to PostgREST).
- **Ordinary traffic runs as `authenticated`** with the caller's claims set, reads *and*
  writes, so RLS applies to real requests. See `.claude/SUPABASE.md`.
- **Three writes are security-definer functions**, not grants: `create_message_pair`,
  `create_greeting` and `mark_thread_crisis`.
- **No streaming in v1.** Plain request/response.
- **Six repair checks are code**, not model calls.
- **`llm_calls` and `crisis_events` written from day one** — neither is backfillable.

---

## What changed on the way across

Behaviour that was ported deliberately differently, with the reason.

| Was | Is |
|---|---|
| Up to 21 provider calls for one user message | **One**, asserted in `test_turn.py` |
| Crisis returned `""` | A real reply, plus the event row and the message id |
| `state.accepted` absent meant *declined* | Tri-state: absent leaves the offer open |
| Unknown technique or phase passed the guard | Fails closed, and the id is dropped |
| Title capped at 50 chars, failing the whole generation | Trimmed to 100 |
| `message_count == 3` exactly gated the title | `>= 3`, so a crisis turn cannot desync it |
| Forbidden words `broken`, `weak`, `heavy` | Dropped — they collide with the mirroring instruction |
| Tap matched against the last Mani message | Against the last one *that offered buttons*, then stops |
| `[ctx]` prefixed and then stored | Built per turn, never stored |
| Summary checkpoint could be a summary id | A message id, enforced by a foreign key |
| Summary trigger compared two different units | Both sides are thread message counts |
| Prompt version snapshot failed silently | Same transaction as the publish |
| Transcripts logged at `error` level | Never logged |
| `/qwen/i` sniffing inside the orchestrator | In `llm/client.py`, where the model lives |
| Nickname only, from auth metadata | Nickname, topics and support style, from a table |
| "New chat" could leave a trail of empty threads | One statement reuses an unused thread |
| Stale buttons cleared by an UPDATE on history | Buttons returned only on Mani's newest message |

## Fixed from review

- **A user could forge Mani's side of their own conversation.** Withholding the INSERT
  grant on `public.messages` did nothing while `create_message_pair` — a definer
  function that takes Mani's words from its caller — was granted to `authenticated` and
  reachable at `POST /rest/v1/rpc/create_message_pair` with the user's own anon-key JWT.
  `mark_thread_crisis` was the same shape: a self-lockout plus arbitrary text into
  `admin.crisis_events`, a table users are otherwise walled out of. The root cause was
  that the backend acted as `authenticated`, so every privilege it needed was one the
  user also held. Ordinary traffic now runs as `mani_service`, which holds the three
  EXECUTE grants alone. RLS still applies to it: the policies carry no `TO` clause and
  it owns no tables. Asserted in `tests/sql/test_rls.sql` and `test_grants.sql`.
- **Completing a technique crashed the turn.** `apply()` deletes the technique state row
  when a technique reaches `ground` accepted — the ordinary successful path — but the
  table had neither a DELETE grant nor a DELETE policy. Since the turn shares one
  transaction, the abort took the user's message and Mani's reply with it. Both halves
  added, and both are covered: `test_finishing_a_technique_clears_it_without_losing_the_turn`
  fails with `InsufficientPrivilegeError` without the grant and on a silent no-op
  without the policy.
- **Conversation content reached the logs on a validation failure.** Pydantic's
  `errors()` carries the rejected value, so a message over the 4,000-character cap was
  written to the log in full at WARNING — the only place in the service that leaked
  content. Now only the error type and field are logged.
- **Two statements in `apply()` relied on RLS alone.** The clear-technique DELETE and
  the `library_offered` UPDATE carried no `user_id` predicate while the title UPDATE
  beside them did. Made consistent; RLS was already catching it, defence in depth is
  the point.
- **A reused `client_message_id` returned a half-empty pair.** The unique key is
  `(user_id, client_message_id)` but `create_message_pair` looked for the matching Mani
  reply in the thread the *call* named, so a reuse across threads yielded NULL. It now
  looks in the thread the original message is actually in, matching what
  `find_pair_by_client_id` already did in Python.

## Bugs found and fixed while porting

- **Message-pair ordering.** `now()` is fixed for a whole transaction, so both halves of
  a turn shared a timestamp and their order was undefined. The previous project shipped
  this, hit it, and patched it by adding a millisecond to Mani's row
  (`20260128111643_fix_message_pair_ordering.sql`). Fixed at the root with
  `clock_timestamp()`, and asserted.
- **A soft delete was impossible.** `deleted_at` was missing from the column-scoped
  update grant on `threads`.
- **`topics` failed to write** — `coalesce()` made Postgres infer the parameter as
  `text` rather than `text[]`.
- **jsonb came back as strings.** Now decoded by a codec on the pool rather than by each
  query module remembering to.
- **The test suite pointed at the wrong database.** `tests/conftest.py` hardcoded port
  54332 — the *previous* project — so integration tests were passing against a schema
  that was not the one under test. conftest now defers to `.env`.
- **`llm_calls.message_id` was written from the wrong connection.** The link was made on
  an admin connection while the turn's transaction was still open, so the foreign key
  could not see the message. It is now made after the turn commits.

## Measured

One real turn against local Supabase and live OpenRouter, `google/gemini-3-flash-preview`:

```
input 8,260 · output 195 · cached 3,572 · 4,633 ms · 1 call
```

The cached figure matters: earlier measurements against the same prompt showed **0
cached tokens on every call**. Fixing the layer order so the static prefix is identical
every turn is what made caching start working. 4.6 s of silence is still a lot for a chat
UI, and sits uneasily with "no streaming in v1" — worth revisiting before launch.

## Open

- **Hosted Supabase Data API settings.** `supabase/config.toml` only configures local
  development. A hosted project needs `auto_expose_new_tables` off and the exposed-schema
  list limited to `public` + `graphql_public`, set by hand in the dashboard — `db push`
  does not carry them. Run `scripts/test_db.sh --local` against the hosted database before
  it takes traffic; left at the defaults, a user could clear their own crisis flag.
- **Crisis resources** — `mani/chat/crisis.py` ships an empty list. Needs countries and
  services from muhammad. Do not invent phone numbers.
- **Hosting** — a container platform supporting two process types from one image.
- **Per-user cost ceiling** — a number is needed to size the retry budget.
  `llm_calls.spend_since()` is the measurement it would read.
