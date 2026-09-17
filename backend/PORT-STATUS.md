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
      closed; the reference returned valid for both. The registry is loaded from
      `admin.frameworks`, which now carries all six frameworks from `frameworks/*.md`:
      per-stage content (purpose, listening cues, readiness, boundaries, unclear-answer
      handling, one `ask` per style) and the router's activation data.
- [x] **7. Prompt composition** — `mani/prompts/`. Fixed layer order, TTL cache,
      `POST /v1/admin/prompts/cache/invalidate`. A missing required layer is refused.
- [x] **8. Model call** — `mani/llm/`. Composed with LangChain: `chain.py` holds the
      `ChatOpenAI` pointed at OpenRouter's `base_url` and the structured-output binding,
      `client.py` holds the app's side — one attempt plus one retry on a schema failure
      only, typed errors, and an `admin.llm_calls` row on success *and* failure. SDK
      retries stay 0; a retry is a decision this layer makes, not the SDK's.
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
- [x] **17. Framework routing, in process** — `mani/chat/router.py`. Phrase scoring
      against each framework's activation data, recency-weighted, with the
      specification's own distinctions as hard overrides. No model call, so routing
      accuracy is a unit test rather than a paid eval. It narrows; the model still
      chooses and `repairs.py` still validates that choice against the registry.
- [x] **18. Safety screen** — `mani/chat/safety.py`, ahead of everything else on every
      turn. An explicit statement locks the thread with **no provider call at all**; an
      indirect one suppresses the router without locking, because the specification is
      direct that ordinary distress words must not produce a crisis response. The
      model's own crisis judgment still runs afterwards, unchanged.
- [x] **19. Stage content in the turn** — `mani/chat/context.py` carries the active
      framework's current and next stage into `[ctx]`, resolved to the conversation's
      style, plus the router's shortlist when nothing is running. This is what makes a
      reply framework-specific rather than generic.
- [x] **20. Exercise hand-off** — a completed framework hands off to the exercise that
      names it, chosen by a real bound tool call (`mani/llm/tools.py`). See the call-count
      note under "Decisions already taken".

## Still to do

- [~] **Eval scenarios in pytest.** `tests/evals/` now holds the negative set: every
      framework's "responses MANI must avoid" examples, as deterministic assertions that
      run in every suite. What is still missing is the other half — nothing judges
      whether the model *detects* a crisis in realistic language. The deterministic
      screen in `mani/chat/safety.py` catches explicit phrasing with no model call, so
      that gap is now narrower than it was, but indirect phrasing still rests on the
      model's own judgment and is untested.
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
2. **No rate limit on the chat endpoint, and no per-user cost ceiling** (MYM-25, still
   open). One client in a retry loop bills the OpenRouter account at ~8k input tokens a
   turn. `llm_calls.spend_since()` is the measurement a ceiling would read; the ceiling
   itself needs a number. Nothing isolates one person's usage from another's, in either
   cost or throughput — see point 7 for the throughput half. What *is* already in place:
   a retried send carrying the same `client_message_id` returns the original reply
   instead of generating a second one, so an honest client's retries are free and
   idempotent; it is a deliberate loop this does not protect against.
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
| GET PATCH DELETE | `/v1/threads/{id}` | fetch, set `conversation_style`, soft delete |
| GET POST | `/v1/threads/{id}/messages` | history, **send a turn**. The reply carries `exercise` on the turn a framework completes |
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

- **OpenRouter is the only provider.** LangChain composes the call and `langchain-openai`
  is the client, because it is an OpenAI-*protocol* client taking a `base_url` — one
  protocol and one bill, not a second provider. No `providers` table; the key lives in
  the environment. LangSmith arrives as a dependency of LangChain and stays off: it would
  receive transcripts, which are special-category health data.
- **asyncpg direct to Postgres**, not PostgREST — a turn needs one real transaction.
- **Two schemas**: `public` (user data, RLS) and `admin` (config and analytics, never
  exposed to PostgREST).
- **Ordinary traffic runs as `mani_service`** with the caller's claims set, reads *and*
  writes, so RLS applies to real requests. The role is a member of `authenticated` and
  holds the few privileges the user must not — the three definer functions, and DELETE on
  `thread_technique_state`. See `.claude/SUPABASE.md` and "Fixed from review" below.
- **One provider call per turn**, with exactly one scoped exception: when a framework
  completes *and* the catalog holds an exercise naming it, a second, small bound tool call
  picks which one. Both halves are asserted — `test_a_turn_costs_exactly_one_provider_call`
  is unchanged and still exact, and a completing turn with nothing in the catalog (the
  production case today) is asserted to stay at one call as well.
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

Real turns against local Supabase and live OpenRouter, `google/gemini-3-flash-preview`.

A chat turn, measured twice back to back:

```
first call in a process   input 8,194 · cached     0 (0%)  · 4,330 ms · 1 call
the identical call after  input 8,194 · cached 3,568 (44%) · 2,487 ms · 1 call
```

The cached figure matters: earlier measurements against the same prompt showed **0
cached tokens on every call**. Fixing the layer order so the static prefix is identical
every turn is what made caching start working. Two things about the shape of it: it caps
at 3,568 on a byte-identical prompt rather than the full 8,194 — the provider caches a
prefix, not everything — and a fresh process starts at 0% again. **Whether it survives
the gap between two real turns, while somebody reads and types, is still unmeasured**,
and that is what decides whether the remaining prompt reordering is worth doing.

The exercise hand-off's tool call, on the turn a framework completes:

```
input 321 · output 52 · 2,460 ms · 1 call
```

Small because it is a short prompt and a closed list, not the conversation. It fires only
when the catalog holds an exercise for that framework, so today it never fires at all.

Several seconds of silence is still a lot for a chat UI, and sits uneasily with "no
streaming in v1" — worth revisiting before launch.

## Open

- **Hosted Supabase Data API settings.** `supabase/config.toml` only configures local
  development. A hosted project needs `auto_expose_new_tables` off and the exposed-schema
  list limited to `public` + `graphql_public`, set by hand in the dashboard — `db push`
  does not carry them. Run `scripts/test_db.sh --local` against the hosted database before
  it takes traffic; left at the defaults, a user could clear their own crisis flag.
- **Crisis resources** — `mani/chat/crisis.py` ships an empty list. Needs countries and
  services from muhammad. Do not invent phone numbers. The same is true of
  `safety.PROTOCOLS` and `safety.CLARIFICATION`: the specifications say precisely *when*
  the safety path fires and what Mani must and must not do, and refer throughout to "the
  approved safety protocol" without containing one. Until it exists, an indirect concern
  changes routing only and Mani answers in its own words.
- **The exercise catalog is empty.** `admin.exercises` holds zero rows and the bucket has
  no files. The hand-off that offers one when a framework completes is built and tested
  against fixtures, so it starts working the moment there is content — but until then it
  is inert, and a completed framework falls back to the plain library offer.
- **Hosting** — a container platform supporting two process types from one image.
- **Per-user rate limit and cost ceiling** — neither exists. Both need a number from
  muhammad rather than a guess; `llm_calls.spend_since()` is the measurement they would
  read. See "Before it takes real traffic", points 2 and 7, for what that leaves exposed.
- **The vague-reply pivot.** `threads.vague_streak` exists, is granted to the backend
  alone, and is written by nothing. The pacing rules it belongs to are designed and not
  built.
