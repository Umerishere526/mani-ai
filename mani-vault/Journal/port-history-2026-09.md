---
type: journal
date: 2026-10-01
tags: [journal, history, port]
---

# The port to Python: history, as it stood at completion

> **HISTORICAL, moved verbatim from `backend/PORT-STATUS.md` on 2026-10-01.** Accurate as of the end of
> the port (about 2026-09-24), not as of today: counts, model names, offer timing and the "one call per
> turn" rule have all moved on. Current status: `backend/PORT-STATUS.md`. Why things are built as they
> are: [[_Index]] (the decisions index). Lessons drawn from this: [[Journal]].

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
      `admin.frameworks`, which now carries all six frameworks from `content/frameworks/*.md`:
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

- **`admin.llm_calls.purpose` was free text holding a closed set.** `mani/db/llm_calls.py`'s
  `Purpose` enum has always been limited to `chat`/`summarize`/`exercise_select`; the column
  let the database accept anything. Migration 006 makes it a real Postgres enum,
  `admin.llm_call_purpose`, matching the sibling `outcome` column's existing discipline.
  Verified against live data first (only `chat`/`summarize` present, both valid) and no
  Python change was needed - `record()` already wrote `purpose.value` the same way it
  already wrote `outcome.value` into the pre-existing enum column. A generated
  `backend/docs/database-schema-reference.md` documents the full schema, roles, RLS
  policies and grants as queried live from `pg_catalog`/`information_schema` - not
  reconstructed from the migration files - and is the reference for future schema work.
- **Verified, not assumed: the six migrations reproduce the live local database, and
  `scripts/seed.py` works against a completely clean one.** Snapshotted every table,
  column, constraint, RLS policy, and grant on both the live local Supabase and a
  from-scratch throwaway built only from `test_harness.sql` + the six migrations, then
  diffed them. Tables, columns, constraints, RLS-enabled flags, enum types, and policies
  matched **exactly**. The only difference was 24 grants (`REFERENCES`/`TRIGGER`/`TRUNCATE`
  for `service_role` on every `public` table) that the live database has and the throwaway
  doesn't - traced to `pg_default_acl`, confirmed as Supabase's own platform-level default
  privilege for `service_role` (set by `supabase_admin`, applied automatically to any new
  table on any Supabase project), not something any migration granted or should. Separately,
  ran `scripts/seed.py` against that same clean throwaway with `DATABASE_URL` pointed at it
  - all 6 frameworks and all 4 prompts loaded with identical row counts and content lengths
  to the live database. A fresh environment genuinely reproduces this one.
- **Four tables let a signed-in user write onto someone else's thread.** `public.messages`
  has always checked both halves - the row carries your `user_id` *and* the thread it names
  is yours. `thread_technique_state`, `thread_techniques_offered`, `thread_response_styles`
  and `thread_summaries` checked only the first, while `authenticated` holds INSERT on all
  four directly and `public` is exposed to PostgREST, so the backend was not the only door.
  `thread_id` is the PRIMARY KEY on two of them, so one inserted row permanently occupied a
  victim's slot: their own upsert then failed the conflict, and the turn shares one
  transaction, so they lost their message and Mani's reply on every turn after. A read leak
  it was not - every SELECT policy is still `auth.uid() = user_id` - but a persistent denial
  of service on a stranger's conversation it was. Migration 003 adds the `exists` clause
  `messages_insert` already used. `tests/sql/test_rls.sql` had a near-miss for this: it set
  `user_id` to the *victim's*, which `auth.uid() = user_id` catches on its own, so it passed
  throughout. The real case - attacker's own `user_id`, victim's `thread_id`, run as
  `authenticated` - is now tested for all four tables, and fails without 003.
- **`scripts/test_db.sh` only ever applied migration 001.** It named that one file, so from
  the moment 002 landed both SQL suites asserted against a schema the project no longer had.
  It now applies every migration in order.
- **The reply schema asked for a clinical note on every turn and threw it away.**
  `clinical_note` was marked Required and described as "written for the care team" - three or
  four sentences of clinical formulation, paid for in output tokens, reaching no column, no
  log and no screen. Removed rather than stored: persisting a formulation about someone's
  mental state is a decision that needs a retention rule and an access policy, and there is
  no care-team surface to justify one yet. Also removes 1,354 characters from the system
  prompt on every turn. If that surface is ever built, it comes back with the column.
- **Shape and voice were free text in the database.** The closed sets were enforced in
  Python only, and the table is append-only so a bad value was never corrected. Live data
  showed why it mattered: of 435 rows, 35 carried an off-list voice - 24 were a capitalised
  form of a real value ("Transitional"), and 5 were `Supportive`/`Direct`, which are
  conversation styles, written into the voice field on turns when `[ctx]` never named the
  style in force. Migration 003 lowercases the recoverable ones, nulls the rest (voice is
  nullable by design) and adds the check.
- **A production process could boot without the two secrets it cannot work without.**
  `OPENROUTER_API_KEY` and the JWT secret both defaulted to empty, so a misconfigured deploy
  started, answered `/health` and `/health/ready` with ok, and failed every real request -
  a chat turn at the provider call, an authenticated request at the JWKS fetch. `Settings`
  now refuses to construct when `environment == "production"` and either is missing.
  Development and the test suite are unaffected.
- **Nothing tested that an admin endpoint is actually admin-only over the wire.** Every turn
  test calls `orchestrator.send()` directly, which is the right shape for testing a turn but
  meant the dependency wiring was never exercised: `require_admin` can be correct and simply
  not attached to a route, and that is invisible to a unit test of the function.
  `tests/unit/test_endpoint_auth.py` drives the routes out of the OpenAPI spec - so a new
  endpoint is covered without anyone editing the test - and asserts every versioned path
  answers 401 without a token and every admin path answers 403 for an ordinary signed-in
  user, including one holding `user_metadata.admin_role`.
- **The conversation style never reached the model.** `mani_base.md` tells it the style in
  force is named in the `[ctx]` block, and the block named it nowhere: `resolve_style()` was
  used only to pick which of a stage's three `ask` variants to inline, so outside a running
  framework the style arrived through no channel at all. The one prose mention lived in the
  composer and read `profile.support_style`, so a thread that had chosen differently was
  contradicted rather than served. `[ctx]` now carries `conversation_style` as its first
  line and the composer's copy is gone — one source, and the prompt's existing claim is true
  rather than aspirational. This is the cause of the failure recorded in
  `tests/evals/test_negative_set.py`: all three styles opening with "I'm here."
- **Capsule labels were only checked offline.** The rules that a button may not name a
  feeling the person did not use, judge them, or run past four words lived in
  `tests/evals/validators.py` and nothing enforced them at runtime — which is how
  "I'm overthinking it" reached a real thread as something to tap. They now run in
  `repairs.apply()` as drops, never rewrites: putting different words in someone's mouth is
  not a repair. The word lists moved into `mani/chat/repairs.py` and the eval imports them,
  so the two layers cannot drift. The mirroring exemption is keyed on everything the person
  has said in the thread, not just the current turn, so a feeling they named four messages
  ago may still be mirrored back.
- **A framework completing on a crisis turn stayed mid-flight forever.** `_handle_crisis()`
  returned before the end-of-turn write, so `thread_technique_state` kept its phase with
  outcome `accepted` on a thread that then locked one way — nothing would ever correct it.
  It now calls `threads.apply()`, and carries the `llm_call_id` through so a crisis the
  model reported links to the call that decided it. No exercise is offered on a crisis turn;
  see "Open".
- **A closed enum in the reply schema could cost the person their message.** `Style.shape`,
  `Style.voice` and `SmartPrompt.library` were typed as enums, so a value outside the set
  was a `ValidationError` — which lands in `parsing_error`, burns a second provider call and
  then raises, and `complete()` runs before the message pair is written. The whole turn was
  lost over a cosmetic self-report about a reply that was otherwise fine. The fields are now
  permissive in the schema and checked in `repairs.apply()`, which drops the bad half and
  keeps the reply. Case is normalized first: a model reading a table returns "Mirror and ask"
  far more often than it returns something genuinely off-list.
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
- **Every turn of a summarized thread raised `AttributeError`.** In `context.build()` a
  local holding the rendered framework history reused the name of the `history` parameter,
  so once a summary named a technique, the message list the opener signal reads had been
  replaced by a string. It needed a thread long enough to summarize *and* a framework
  recorded against it, which no test combined and the evals are too short to reach.

- **The crisis screen missed phone typing.** iOS curly apostrophes ("don’t") and no
  apostrophe at all ("dont") both scored NONE on phrases the straight form flagged, and the
  router shares the same `normalize()`. Both forms now expand like the straight one.
- **A person could write their own summary and framework state.** `authenticated` held
  INSERT/UPDATE on `thread_summaries` (free text placed in the system prompt) and
  `thread_technique_state` (accept a framework, reset the cooldown). Moved to `mani_service`
  in migration 007.
- **A typed `[ctx]` block reached the model as metadata** and replayed from history.
  `context.disarm()` neutralises the markers in anything the person wrote.
- **A safety concern changed nothing but the router.** Mid-framework, the next stage's
  question still went out. `[ctx]` now carries `safety: concern`, the framework is paused
  (not ended), and technique buttons are dropped for that turn.
- **New chat bypassed a crisis entirely.** A new thread now carries `recent_crisis: yes` for
  30 days, the fact only - no lock and no content.
- **`profile.topics` was unbounded** and pasted into every system prompt. Capped (migration 008).
- **Summaries had never once succeeded.** Every call 404'd: the model was not served by the
  pinned provider. Now on the pinned Gemini model, and the threshold equals the history
  window so no message falls between the window and the summary.
- **A finished or declined framework counted as running forever**, stripping every later
  technique button and switching the router off for the rest of the thread. One liveness
  rule in `orchestrator.send`; the cooldown - which the stripped buttons had been enforcing
  by accident - is now a real check in `repairs.apply`.
- **A tapped decline was lost** whenever the model returned `state: null`, leaving the offer
  open. **The model could switch the running framework** through `state.technique`.
- **A reply cut off at `max_tokens` was never retried and was logged as 0 tokens.** The SDK
  raises it inside the model step, before LangChain's `parsing_error`. Now one retry, billed
  at its real usage. An empty reply after repairs is a retryable error, not a 500.
- **Stage questions carried worked-example details into every conversation** - "your
  manager", "your sister", "her silence" - plus author notes and asserted conclusions ("This
  belief is supported by the facts"). 37 asks rewritten; a test now refuses people, author
  notes and unlicensed feeling words in any ask.
- **The ending ran in the opposite order to the prompt.** Now closing, then somatic, in all
  six frameworks, with one body check-in script instead of two.
- **Contraindications never reached the model** - abuse, a medical cause, a protective
  action, OCD reassurance-seeking. Now in the Framework Index as "Never offer one when".
- **Router:** substring matching ("she hates meetings"), a repeated phrase not counting as
  corroboration, a rule-promoted pick never confident, STOP held behind the two-exchange
  gate, and "my manager" / "she said" lifting ABCDE in any conversation with a person in it.

- **The opening flow the client specified was never built.** Every chat opened "How can I
  support you today?" - the Supportive opener - and never asked for a style. It now greets per
  the spec, asks "How would you like me to speak with you today?" with three style buttons,
  and a tap sets the style and answers with that style's opener, with no model call.
- **The prompt had drifted from the client's own examples.** It forbade "I'm sorry you're
  feeling this way" (in two client examples), required naming the framework (no client example
  does), paraphrased the "Tell me more" explanations and consent lines, and never gave the
  model the client's three offer labels. `repairs.py` then deleted the client's own
  five-word "I want to keep talking" button. All aligned to `docs/specs/conversational-styles.md`.
- **Offers were made too early and sometimes shared a reply with another question.**
  `[ctx]` now carries `conversation_phase` and `understanding_turns`; an offer made only by
  buttons gets the client's permission question, and offer buttons under an unrelated question
  are dropped.

- **The prompt contradicted itself in about twenty places the model reads on every turn.**
  Among them:
  - "let moments breathe without a question" sat two lines above "every reply ends with a
    question";
  - "by the name shown there" contradicted "you do not need to name it";
  - a Vocabulary block approved "I'm listening" (presence outside Supportive) and "so busy"
    (added scale);
  - "named or clearly implied" let the model voice feelings no one named;
  - "never mirror twice in a row" fought the client's own Reflective examples.

  All resolved, with muhammad deciding the three that were product calls (2026-09-23):
  - same-weight feeling synonyms stay;
  - mirroring may repeat as long as the voice varies;
  - passive-ideation phrases are added at concern level.

  The "Before you answer" checklist is folded into the reasoning steps, because it ran after
  the reply was already written.
- **Announced presence outside Supportive** survived every prompt wording when someone asked
  only to be heard. `repairs.py` now removes a sentence that only announces presence ("I'm
  here", "I'm listening") in Direct and Reflective, never leaving the reply empty.
- **The chat-tester bypassed the client's flow.** It set the style through PATCH, so the
  greeting's question hung unanswered in history, and it never rendered buttons. It now
  starts from the greeting's buttons and renders every button as a tap.

- **Integration tests left fabricated cost rows in the local database.** Deleting a test
  user sets `llm_calls.user_id` to null instead of removing the row, and one test writes a
  fake call under the real model name. That left 108 rows and 568K fake input tokens counted
  as real spend and real cache misses. Every integration fixture now removes its user through
  `tests/integration/cleanup.py`, which deletes the user's cost rows first, and a full run
  leaves nothing behind.

- **A retry sent while the first request was still waiting on the model was paid for twice**,
  and could crash on the unique key. The duplicate check read before the model call and held
  nothing while it ran. A transaction-scoped advisory lock on the message id now makes the
  retry wait and return the stored reply.
- **A message id reused in another conversation returned the first conversation's reply** and
  wrote nothing where it was sent. It is now refused with 409 `conflict`.
- **Two summaries started together both paid for a generation.** A non-blocking lock per thread
  lets the second step aside.
- **"Tell me more" cost a model call to paraphrase text the client had written word for word.**
  It is now a fixed reply with the client's explanation and the two re-offer buttons, and the
  explanations are no longer in the prompt.

- **Printing the settings printed every secret.** An AttributeError on `Settings` includes the
  whole object in its message, so a log line, a traceback or a Sentry event carried the
  OpenRouter key, the service-role key, the JWT secret and the database password. It showed
  up live in a test failure. All five fields are now `repr=False`, and a test asserts none of
  them appear.
- **Nothing limited paid calls per person.** `DAILY_MESSAGE_LIMIT` caps one person's messages
  per 24 hours. It is checked immediately before the model call, so the safety screen and the
  free fixed replies are never refused. It is **off (0) by default** on muhammad's
  instruction while testing; his number is 300, and it must be set before real traffic.

- **The eval ran scenarios as one shared user,** so scenarios started together landed in the
  same conversation, and every prompt carried that user's folded memory. Each scenario and
  style now gets a fresh user.
- **Frameworks often ended without the client's two choices.** The buttons came mislabeled
  ("Something else") or not at all. The reply that ends a framework now always carries
  **Chat More** / **Go to Library**, unless the person has already chosen one.
- **Thought Reframe could not finish.**
  - Its first stage waited for a literal "yes" while the person elaborated.
  - Its reframe stage required a 0-100 rating, which is not in the client's spec.

  Readiness now accepts the person's own words; the rating is removed (muhammad, 2026-09-24).
- **One transient provider failure (Google AI Studio 503, 1 in 265 calls)** is retried once;
  a timeout is not.

- **Offers follow the client's newer direction (2026-09-24):**
  - Mani never says a framework's name or the word "framework". It offers "a sequence of
    questions" and says how it would help with what the person said, using each framework's
    description from the client (now its `summary`, shown word for word on "Tell me about
    this").
  - The buttons are **Try it** / **Tell me about this** / **Keep chatting**.
  - There is no fixed message count before an offer.
  - After "Keep chatting" Mani may offer again after three replies: the same framework or a
    different one. Only a framework just finished is never re-offered.
  - After a framework ends and the person carries on with the same issue, the client's three
    forward-moving questions are asked one per reply, tracked in `[ctx]` as
    `after_framework_question`.
  - Twelve writer's notes left inside reply text Mani could say were removed from the
    framework files.
  - Carrying on talking without answering an offer counts as **Keep chatting**. The model
    reports it as `accepted: false`, and only a question about the offer keeps it open. The
    reply that takes a no never carries an offer, and Tell me about this / Keep chatting go
    with any offer button that is dropped.
  - Offers are worded fresh each time: "some questions" (a sequence, a set, a few) and how
    they would help this person. Each framework's `offer_ask` is a model for that sentence,
    not a line to repeat. The repairs recognise an offer in any of these wordings.
  - The styles are three personas of one Mani, all warm and friendly. **Direct** aims at a way
    through what they feel and offers as soon as the fit is clear, often at the first or second
    reply. **Supportive** leads with feelings before the situation. **Reflective** explores
    with warm curiosity. Both offer after about two to four exchanges.
  - **Chat More** / **Go to Library** go on the reply that asks "What would you like to do
    next?", once. The body check-in question carries neither, unless the person had already
    described their body and the check-in reply goes straight to what next. The reply after
    the choice was offered does not offer it again.

- **Buttons appear only at a framework's offer and its end** (the client, 2026-09-24: in ordinary
  chat they read as a menu). `repairs.apply` drops any other button: in free chat and in the
  middle of a framework. The body check-in and the practice after it keep theirs, and the
  greeting's style buttons and Chat More / Go to Library are written by the orchestrator after
  the repairs, so they are untouched.


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

Response shapes across a full eval run, 48 turns over four scenarios and three styles:

```
mirror and ask 37 · honor and follow 4 · mirror and hold 3 · gentle follow 2 · warmth lead 2
```

An earlier run showed `mirror and ask` at 94% with three shapes never chosen at all. That
reading was mostly an artifact: every scripted turn had the person actively offering new
material, which is exactly the moment a question belongs, so the eval had no turn a
question-free shape could win. `disclosure_no_question_needed` supplies those turns, and
run on its own the distribution inverts — `honor and follow` 5, `mirror and ask` 4,
`mirror and hold` 2, `presence only` 1, no findings. It was rewritten once to avoid the
wording used in `mani_base`'s worked examples, so what it measures is shape selection
rather than recall of the examples.

`Reply` declares `reasoning` and `style` before `text`. Structured output is generated in
schema order (checked against the raw JSON from the provider), so while they sat after
`text` the opener check in `reasoning` and the shape choice in `style` were written about a
reply that already existed. Moving them first, `criticism_abcde` run repeatedly:

```
reasoning after text    6 repeated openers in  9 conversations
reasoning before text   1 repeated opener  in 15 conversations
```

A full run afterwards: 1 finding across 48 turns, `mirror and ask` 32 · `honor and follow`
7 · `mirror and hold` 5 · `gentle follow` 4. The cost is latency: chat calls averaged
2,829 ms and 178 output tokens before, 3,314 ms and 209 after, because the reasoning is
now substantive rather than a formality.

Library buttons: the model filled `library` with values that are not sections -
`"library"`, `"default"`, `"self_care"`, a topic phrase - every time meaning the library in
general, even with `home` named in both field descriptions. `repairs.py` now sends an
unknown value to `home` instead of dropping the button, so the end-of-conversation library
link survives. An enum would fail the whole turn instead.

Memory fold, three live calls: 346-426 output tokens, 2.8-3.7 s each. Against what the
person actually typed, entries were in their own words except one ("burden"). Before the
boundary on ideation, it recorded "an urge to disappear or to have never existed"; after it,
nothing of the kind.

The static system prompt is now about 35.6K characters (was 32.4K): the contraindications
added 2.3K and the complete `[ctx]` guide 1K. All of it is in the cached prefix.

Full eval after the contradiction pass: 8 scenarios × 3 styles, 84 replies. **1 finding** (an
introduced feeling word), 0 failed calls, 66% of input tokens cached (53% before), 3.5 s
average. Static prompt about 39.8K characters.

Token pass: the static prompt is about 38.1K characters (was 39.8K) after moving "Tell me
more" into code and removing rules stated two or three times. Full eval, 9 scenarios including
a framework walkthrough, about 100 replies: **0 findings**, 9,563 input tokens per turn (was
9,855), 67% cached, 219 output, 3.4 s. Gemini reports 0 hidden reasoning tokens, so the reasoning
field is the only thinking paid for. Tried and reverted: sending only purpose, boundaries and ask
for the next stage. It saved about 130 tokens a framework turn (1%), and in the A/B the stages
advanced a turn late, which is not a trade worth making on the core flow.

Demo rehearsal, isolated users, 21 scenarios × 3 styles (307 calls, 0 failed):
- Journeys reach the body check-in and hand off in 7 of 9 runs; the other two ran out of scripted
  answers, not stalled.
- No missing hand-offs, and 1 repeated question.
- 9,425 input tokens a turn, 69% cached, 3.1 s.

The exercise hand-off's tool call, on the turn a framework completes:

```
input 321 · output 52 · 2,460 ms · 1 call
```

Small because it is a short prompt and a closed list, not the conversation. It fires only
when the catalog holds an exercise for that framework, so today it never fires at all.

Several seconds of silence is still a lot for a chat UI, and sits uneasily with "no
streaming in v1" — worth revisiting before launch.
