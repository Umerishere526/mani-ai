# Port status

What the backend does today and what is still open. Stack notes: `.claude/BACKEND.md`. Database rules:
`.claude/SUPABASE.md`. **Update this file in
the same change as the work.**

## Status, 2026-10-01

- The TypeScript to Python port is complete. FastAPI is the only thing that touches the database.
- Tests: `pytest` runs 641 passed and 4 skipped (the four symmetric-token auth tests, which skip on a
  JWKS-configured project), against a local database reseeded from `content/`. A database seeded before
  spec 0005 still holds the old ABCDE `offering` block and fails `test_an_offer_they_typed_past_is_flagged_then_closed`.
- Cost baseline `before-lean-prompts` (2026-10-07, `scripts/baselines/2026-10-07-before-lean-prompts.json`,
  gpt-6-luna on effort `high`, Supportive, 3 runs): median per run of the three tagged scenarios is 26 calls,
  228,251 input tokens (203,763 cached), 25,595 output tokens of which 21,665 are reasoning, 319 s of model
  time against 320 s of turn time, and 3 findings. A turn takes a median of 11.5 s; 7 of 70 turns were redrafted.
- Database: 18 migrations (001-010 and 018-025), 15 tables (8 `public`, 7 `admin`), 6 frameworks and 10 prompts seeded.
  `admin.exercises` holds the 17 library exercises from `content/exercises/`, with their audio in the
  private `exercises` bucket (`scripts/seed_exercises.py`). A hosted project exists and its schema has
  drifted ahead of this code (see Open engineering).
- Models: `openai/gpt-6-luna` for chat and for summaries (`mani/config.py`), routed Azure first with
  OpenAI as the fallback. It is a reasoning model: it takes no `temperature` on any provider and reads
  `reasoning_effort` instead, so `mani/llm/chain.py` sends the sampling parameters an ordinary
  chat model takes only to models that accept them. Each of the five model calls names its own effort
  in its own prompt row's `model_parameters.reasoning_effort`: `mani_base` (the chat turn),
  `summarization`, `memory_fold`, `exercise_select` and `voice_translation`, all on `high`. There is no
  default: a call row with no valid level is refused by `scripts/seed.py`, by the admin prompt writes
  (422), and right before the call, as a config error that spends nothing (`mani/prompts/calls.py`). Effort is
  billed: measured against Azure, `high` spent 26 reasoning tokens where `low` spent 0, about three
  times the cost of the same call. The fallback keeps `data_collection: deny`, so
  training use stays refused, but a turn that cannot reach Azure is processed by a different company -
  a data protection question that is open, not settled.
- Every call to OpenRouter carries the same provider order and data policy, and the effort its own row
  names, from `chain.request_body`. The voice translation in `mani/stt.py` calls the SDK directly and used
  to send none of them, so a transcript went to whichever provider OpenRouter chose; it now uses the same
  body, with its instruction, model, budget and effort from the `voice_translation` row. A missing row or
  level returns the untranslated transcript. The exercise pick likewise reads `exercise_select`, and offers
  the first candidate when that row is missing or has no level.
  It is still not recorded in `admin.llm_calls`, which has no purpose for it.
- A reasoning model's output budget covers its thinking and its reply together. Every caller sizes
  `max_tokens` for the reply alone, so `chain.sampling` adds `REASONING_ALLOWANCE_TOKENS` (8,192) on top.
  Without it, at effort high, 4 of 61 chat calls ran out of tokens while thinking and the turn failed
  (2026-10-07). Measured at high: 12.6 s for an average turn, 41 s for the longest.
- `mani_base.md` and `response_format.md` are YAML rules rather than prose: about 10,600 tokens became 4,850,
  then 3,436 words became 2,403 (2026-10-07), with the duplicated rules, word lists and the exact must say lines
  gone. The Framework Index and the per-framework rules are not restructured yet.
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
  2. The grief veto (`vetoes.py`) rules a framework out when their words say it does not fit: a phrase of its
     `never_offer_when_said`, said as whole words anywhere in the context window, names it in `[ctx]` as
     `ruled_out`. Nothing else in code decides which set may be offered; the model judges that from the
     Framework Index (spec 0011).
  3. `context.py` builds the `[ctx]` block: style, offer timing, the stage in progress, and the lines Mani
     may say word for word (`after_framework_questions` after a framework ended), as keys from `CTX_KEYS`
     and values only. The code does not label what the person
     said; the model reads it.
  4. One model call (`mani/llm/`, LangChain on OpenRouter) returns a structured reply: `reasoning`, `style`,
     `heading_toward`, then `text`. The order is deliberate. The schema carries names and types only.
  5. `guards.py` stops a model supplied id or value from being stored unchecked: a technique button for an
     unknown framework, inside a running one, or on a turn that declines or retires an offer (with the
     offer's other buttons), a stage out of order, a library section that does not exist. The reply's
     words are not edited.
  6. A technique button still there after the guards, a safety concern and the ending is an offer, and
     `offer.py` writes it (spec 0013): the `replies` row's `offer.text`, the shared lead, then the
     framework's name and summary, the same for every set and style, and the buttons Try It · Tell Me More ·
     Keep Chatting. The model's line is dropped unless it answers a typed question about the offer, when it
     goes first; the model's style on that turn is dropped too (spec 0016). A tap on Tell me more is answered
     from `offer.more_text`, or, for a framework listed under `offer.by_framework`, its per style steps
     (spec 0015), with no model call, and leaves the offer open.
  7. Crisis, the reply, the framework state and the summary are written together.
- **Frameworks** (`content/frameworks/*.md`, seeded to `admin.frameworks`): six, each reviewed against the
  client's specification. An offer may come from the person's second message, of any set the model judges
  fits, once Mani knows what they are struggling with and what makes it hard, with no count beyond that
  floor (spec 0016). There is no nearest fit and no urgent case:
  DBT STOP waits for the second message like the others. The seed appends `somatic_checkin` and `somatic_practice`
  (`techniques.ENDING_PHASES`) to every framework's phases.
  The ending is rules in `mani_base.md`'s `ending` section (spec 0009): on the last own stage Mani asks
  how they feel, offers a short body check, guides it one step per reply with steps it picks, and asks
  again how they feel. The model ends it with the reply field `ending`: `choice` retires the framework and
  shows Chat More / Go to Library and the exercise card, `keep_talking` retires it with no buttons and no
  card. The code keeps `ending` only while the ending is open (`Registry.ending_open`) and when the reply
  does not also move the stage forward. A framework the model never ends retires after
  `ending_turn_cap` (12, in `tuning`) of the person's messages, counted from
  `thread_technique_state.ending_from`; a crisis turn retires an open ending too.
- **Memory**: per person, folded from earlier chats by `mani/memory.py`; idle threads fold through
  `scripts/fold_idle_threads.py`, which nothing schedules yet (scope feature 19).
  `GET /internal/cron/fold-summaries` catches up thread summaries, not memory.
- **Exercises**: catalog, completions and signed URLs (`mani/storage.py`). A completing framework picks one
  exercise from the whole active catalog with one bound tool call (`mani/llm/tools.py`): the framework's own
  exercises are listed first, and the pick sees the person's last three messages and the thread's current
  issue. `GET /v1/exercises` is the whole catalog, and responses never carry the storage path.
- **Admin**: prompt CRUD with versioning, exercise CRUD, crisis event review, a user's memory. A prompt
  write that would leave a model call's row without a valid level, renamed, or inactive, or a required row
  (`mani_base`, `response_format`, `replies`, `tuning`) broken, renamed, or inactive, is refused with 422,
  and the write and its version snapshot roll back together.
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
| GET | `/internal/cron/fold-summaries` | thread summary catch up (`summarize.reconcile_due`), bearer `CRON_SECRET`, no JWT |

## Decisions in force

- **A turn is one chat model call, and a malformed chat reply is not retried**. The person sees a retryable
  error instead. The one scoped extra call is the exercise pick at the end of a framework.
  `test_a_turn_makes_one_chat_call_and_does_not_retry_a_malformed_reply` holds it.
- **The reply goes out as the model wrote it, except an offer.** Code after the call only guards what is
  stored or sent to the app (`mani/chat/guards.py`: unknown ids, stage order, library sections, buttons that
  would overwrite a decline or a retirement, an `ending` set outside the ending). Offer timing is told in
  `[ctx]`, not enforced, and the grief veto is told as `ruled_out`. The one exception is an offer (spec
  0013): the model decides that it offers and which set, and the code writes the three buttons and the reply to
  Tell me more from seeded rows. Every set is offered in the same seeded words, the shared lead, the name
  and the description, with the model's line and style dropped unless the line answers a typed question
  about the offer (muhammad, 2026-10-09, spec 0016). A framework listed under `offer.by_framework` gets
  its per style steps for Tell me more, in the style `[ctx]` names (spec 0015).
  The buttons are the client's capsules, Try It · Tell Me More · Keep Chatting, and Try It · Keep Chatting
  after Tell Me More.
- **The ending is ended by the model's `ending` field, and the code never reads words to drive it** (spec
  0009). `choice` and `keep_talking` retire the framework; Chat More / Go to Library are written by the
  code on `choice` only; no code edits the reply or matches a message or reply to decide buttons, state or
  retirement. A 12 message cap (`tuning` `ending_turn_cap`, `ending_from`) is the backstop. Held by
  `test_turn.py`'s ending tests and `test_guards.py`.
- **The model judges which set fits, from the Framework Index; code only vetoes** (spec 0011).
  Mani offers a set once it knows what they are struggling with and what makes it hard, from their second
  message at the earliest, with no count beyond that floor (spec 0016), and only when
  `cooldown_passed: yes`, never one `ruled_out` names. The rule is told in `mani_base.md` and
  `response_format.md`, never enforced after the call; each offer is logged by id with `cooldown_passed`.
  There is no closest fit and no phrase list for what fits. Every reply before an offer asks one question.
- **No sentence the model reads is written in `backend/mani/`** (spec 0007). Python sends keys
  (`context.CTX_KEYS`), headings (`composer.LAYER_HEADINGS`) and data, the prompts explain them, and
  `tests/unit/test_prompt_contract.py` ties the two in both directions. The reply schemas carry no
  descriptions; field meanings live in `response_format.md` `fields` and in each call's prompt. The reply
  shapes live only in `mani_base.md` `reply_shapes` (`Config.reply_shapes`; migration 019 dropped the
  database check), and the grief veto's phrases in `behavioral_activation.md`'s `activation.never_offer_when_said`.
- **The lines Mani sends without the model live in the `replies` row, and the numbers that shape a
  conversation in the `tuning` row** (spec 0008). The offer, its button labels and the Tell me more reply
  are `replies` lines too, filled from the framework's `name` and `summary` (spec 0013), except a framework
  listed under `offer.by_framework`: its Tell me more is literal text per style, all three styles or none,
  with no `{` or `}`, and the seed refuses an id with no framework file (spec 0015). Both are required rows of `admin.prompts`, never sent to
  a model, with no default in code. `content_problem` in `mani/prompts/checks.py` checks them at seed, on
  every admin write (422, nothing stored) and at cache load (`CONFIG_ERROR`), and the four required rows
  cannot be deactivated or renamed in the portal. The files in `content/prompts/` are the source of
  truth: a portal edit lasts until the next seed. `REMOVED_NAMES` in
  `tests/unit/test_prompts_name_what_exists.py` fails when a moved constant comes back.
- **ABCDE is offered over Thought Reframe whenever both fit** (the client's ABCDE Framework doc,
  October 2026). Told in `abcde.md`'s Starts when and `thought_reframe.md`'s Skip when, never enforced in code.
- **ABCDE names each letter as it goes, A is for Activating Event to E is for Effective New Belief**, from
  the words on its Stages line. Its stage ids are the client's step names too, `activating_event`, `belief`,
  `consequences`, `dispute` and `effective_new_belief`, because the model reads an id as the stage's name. A
  Stages line may run to 420 characters (`seed.py` `MAX_STAGES_LINE`) to hold them.
- **Memory is per person**.
- Also settled: OpenRouter only, asyncpg not PostgREST, the
  `public` and `admin` split, the `mani_service` role, three security definer write functions, the
  deterministic safety screen as the only thing that locks a thread, no streaming.
- **The base prompt is short rules the model reasons from, not scripts.** No word lists and no example
  conversations. The only lines the model says word for word are the after framework questions, sent in
  `[ctx]` from the `replies` row, and the model tracks which it has already asked from its own replies in
  the history window; the client's consent and stage lines are examples. There is no size limit in a test.
- **Each style line is the client's behavior list in the client's phrases, and nothing else steers the
  style** (spec 0012). `mani_base.md` `styles` holds it; `[ctx]` names the style and carries no hint about
  what to ask. A rule that asks for one more question before an offer is cut, not balanced by another
  rule. The button says Directive; the stored value stays `direct`.
- **Every model call names its thinking level in its own prompt row; there is no default** (spec 0004).
  `CALL_PROMPTS` in `mani/prompts/calls.py` lists the call rows, and seed, the admin writes and the call
  sites share one check. The portal cannot pause a call by deactivating its row.
- **A prompt change is judged on numbers**: `eval_replies.py --baseline`, 3 runs before and 3 after, compared
  with `scripts/baseline.py compare` on the per scenario totals (spec 0002). One eval run is noise.
- **Code, columns, grants and packages nothing reads are removed, not kept in case; write only audit records
  stay because a person reads them** (spec 0014).

## Before it takes real traffic

Ordered by what breaks first.

1. **Hosted Data API settings.** `supabase/config.toml` configures local development only. On a hosted
   project set `auto_expose_new_tables` off and the exposed schemas to `public` and `graphql_public` by hand;
   `db push` does not carry them. Run `scripts/test_db.sh --local` against the hosted database first, or a
   user could clear their own crisis flag.
2. **Rate limit and cost ceiling.** `DAILY_MESSAGE_LIMIT` exists and defaults to 0 (off). It needs a number
   from muhammad. There is no per user cost ceiling; one would sum a person's tokens in `admin.llm_calls`. A retried
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
   tested.
8. **The backend's database role.** `001_initial_schema.sql` grants `mani_service` to `postgres`. If the
   deployed `DATABASE_URL` connects as anything else, `set local role mani_service` fails. Grant it to that role,
   never to `authenticator`.
9. **Email confirmation is not enforced** and **app attestation is absent.** Confirmation needs
   `enable_confirmations` in Supabase and SMTP; do not read `email_verified` from the token, because the user can
   write it. Attestation layers on after the rate limit, in front of the chat endpoint only.

## Open decisions for muhammad

- Crisis resources, `PROTOCOLS` and `CLARIFICATION` wording (point 3 above).
- Tell the client that the two check lines ("Do I have this right?", "What would you like us to focus on
  today?") are gone, and Mani checks its understanding in its own words, as their October 8 examples do
  (spec 0012).
- Tell the client that Mani no longer matches phrases to decide what to offer, so a plain sentence can be
  offered a fitting set, and that DBT STOP waits for the second message like the others; have them read
  about five real Supportive and Reflective transcripts.
- Tell the client: when a person asks Mani to pick, it offers one small draft step to accept
  or change, which the Behavioral Activation specification's "must not choose the activity" does not allow
  as written.
- Tell the client: after Try It Mani no longer asks the first stage's question when the person
  has already said it, and a person who cannot say what to do is offered up to three options at the first
  "I don't know". Both depart from the literal Structured Problem Solving example.
- Tell the client that every framework, ABCDE included, is offered in the same words: "We'll go through a few
  focused questions. By the end, you will have turned a problem that feels unclear or overwhelming into a
  practical next step. Would it help to work through it together?", then the framework's name and their
  intro document's description word for word. The name is shown although that document says not to give
  it, and ABCDE's per style offer wording is not used, both muhammad's call (spec 0013, 0016). A line of
  Mani's own goes before the offer only when it answers a question the person typed about it, so an offer
  does not respond to the person's last message. No count of exchanges is enforced beyond holding the
  first offer until the person's second message (spec 0016).
- Tell the client that ABCDE's Tell Me More uses their per style steps, and the other five show their name
  and description until their documents arrive (spec 0015).
- Tell the client that their Supportive and Reflective style lines were reworded so care is about what the
  person faces, never their feeling handed back: Supportive "Acknowledges what they are facing", Reflective
  "Reflects the meaning behind what they say, never its details" (spec 0016).
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
  same schema, and nothing reconciles them yet. Local now also has `018` (`llm_calls.reasoning_tokens`,
  numbered past 017 so it never collides). Code that writes that column must not reach hosted before
  `018` does: every cost row insert would fail, and `client._record` swallows the error.
- **Seed hosted before deploying spec 0004's code.** The code reads `exercise_select` and
  `voice_translation`, which only the seed writes (ids `...012` and `...013`; confirm no other row holds
  them first). Deployed before the seed, the exercise pick falls back to the first candidate and voice
  input stays untranslated, logged, until it runs. Seeding overwrites portal edits to prompts and
  frameworks, so check hosted's `updated_at` first. Waits on the 011 to 017 reconciliation above. Keep
  `REASONING_EFFORT` set on hosted until the deploy has proven itself: this code ignores it, and the
  code a rollback returns to still falls back to it.
- **Spec 0007 deploys in order: migration 019, then the seed, then the code.** Deployed before the seed, the
  model gets no field descriptions and no stage rules until it runs. Hosted waits on the 011 to 017
  reconciliation above like the rest. The portal skips the seed's checks, so a `mani_base` edit that breaks
  `reply_shapes` drops every shape and a broken `never_offer_when_said` is ignored, both only visible in the logs.
- **Spec 0011 deploys the other way round: the seed, then the code.** The `tuning` row loses its `router`
  block and `Tuning` refuses unknown keys, so new code on the old row fails on its first load, and old code
  on the new row fails when its cached snapshot next expires (300 seconds in production). Hosted waits on
  the 011 to 017 reconciliation above like the rest.
- **Offers on plain phrasing are unmeasured.** Specs 0007 and 0011 shipped on unit and contract tests, with
  no real run. Measure offers per conversation, offers where a Skip when line applied and offers before the
  cooldown under feature 11, with muhammad's yes for each real run.
- **Migration numbers were reused across the reverted branches.** `011` was both
  `technique_state_holds` and `technique_outcome_stopped`; `013` was both `llm_call_decision` and
  `llm_call_facts`. Reviving any of those branches collides again.


- **The body ending is unmeasured and the client has not seen it.** Spec 0009 replaced the client's fixed
  check in, per place practices and waves reply with rules the model follows (muhammad's design, 2026-10-08),
  and shipped on scripted tests alone. Nothing yet measures one step per reply, the step count, `choice`
  versus `keep_talking`, or how often the cap fires; that is feature 11, after muhammad's yes. The client's
  documents still describe a fixed check and fixed practices, so they need telling. `mani_base.md`'s
  `ending` section is reseeded only after muhammad's review of its wording.
- **Generated TypeScript types** for `web/` and `mobile/` from the OpenAPI schema, with a CI gate. No CI exists.
- **Admin audio upload.** The 17 seeded exercises come from `content/exercises/` through
  `scripts/seed_exercises.py`; there is no upload route, and the admin exercise CRUD takes an existing
  `audio_path`. The exercise card is also not kept on the message, so it is gone once a thread reloads.
- **A worker process** for summaries and the memory fold, for when there is more than one instance.
- **Admin conversation browser**: do not rebuild it as a general reader. Scope it to threads with an unresolved
  crisis event, log each read, and return metadata by default.
- **`GET /v1/admin/models`**, which the prompt editor's model dropdown needs.
- **Vague-reply pacing** is designed, not built, and has no column; it gets one with the code that uses it.
- The words "worried", "concerned" and "a lot" still reached about 1 reply in 10 in some scenarios when code
  checked for them. Nothing in `mani/` checks for them now, and the evals score them from
  `tests/evals/vocabulary.py`.

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
  That wait is gone: every offer may come from the second message (spec 0012, see Frameworks above).
- System prompt size, spec 0007, 2026-10-07, counted with tiktoken `o200k_base` from the seeded rows (no
  model call, no user layers): before 5,391 tokens plus a 1,416 token `Reply` schema, 6,807 together; after
  6,383 plus 590, 6,973 together (+166, 2.4%). The stage rules, layer meanings and field meanings moved
  into the cached prefix; `[ctx]` lost `stage_note` on every framework turn. `Extraction` 380 to 193,
  `Memory` 386 to 178, `StartExercise` 130 to 41. The bill depends on the provider caching the prefix.
- Client cadence, spec 0012, 2026-10-08, one real run each after the reseed, recorded as measured and not
  rerun. `client_anxiety` Directive: no offer in its three messages, a fail. Mani asked twice whether the
  chest tightness was new or severe, from the pain rule in `offers` and the `crisis` field's injury
  guidance, not from the style line. `client_overthinking` Reflective: offer at message 2
  (`thought_reframe`), a pass. `client_stress` Supportive: offer at message 2 (`structured_problem_solving`),
  a pass. None of "I hear you", "That makes sense" or "I'm here for you" in any reply; "I'm here with you"
  came in the Directive and Reflective runs. Prompts 150 lines and 3,616 words before, 148 and 3,460 after.
- Understand then offer, spec 0016, 2026-10-08, `client_job_decision` once per style after the reseed,
  recorded as measured and not rerun. All three fail. Every style asks what the decision is first and
  offers `structured_problem_solving` at message 3 (passes). Every style still opens a reply before the
  offer by handing back their feeling or words ("That sounds frustrating…", "you're worried about getting it
  wrong"), a fail in 3 of 3. The bridge line answers what they said with no question or recap only in
  Supportive ("Neither option feels simple when each offers something important."); Direct wrote an offer of
  its own and Reflective a recap plus one. No reply after Try It asked for what they told (passes), but
  Direct and Supportive said their reasons back first, which E7 forbids. Prompts 145 lines and 3,391 words
  before, 145 and 3,418 after; pytest 684 passed, 4 skipped, before and after.
- Understand then offer, round 2, spec 0016, 2026-10-08, `client_job_decision` three times per style after
  the reseed of E6, E8 to E11, recorded as measured and not rerun. AC-8 fails. Per bullet, out of 3, Direct /
  Supportive / Reflective: no restating before the offer 0 / 0 / 2; first reply asks what the decision is
  3 / 3 / 3; offer at message 3 or later 3 / 2 / 1; bridge answers with no question and no recap 0 / 0 / 0;
  after the yes asks nothing told 2 / 3 / 3. The restating is the `warmth lead` opener "That sounds
  frustrating" in 5 of 6 Direct and Supportive runs, with reasoning "they need to be heard" or "a kind
  acknowledgment", and "the fear of getting it wrong" at message 2 in 2 runs. Reflective's two passes come
  from offers at message 2, which left one reply to judge. Every one of the nine bridge lines makes an offer
  of its own and ends "Would you like…?", reasoning "offer it now", so the seeded offer reads twice. The say
  back after the yes came in 4 runs (measured only). Regression, `disclosure_no_question_needed` once per
  style: no offer in any; Direct opens twice with "I won't…" and ends "I'm here with you" (off style), Supportive
  ends "I hear you", Reflective retells twice. Prompts 145 lines and 3,424 words; pytest 684 passed, 4
  skipped, integration 147 none skipped. Twelve runs cost 0.03 dollars.
- Understand then offer, round 3, spec 0016, 2026-10-08, `client_job_decision` three times per style after
  the reseed of the offer rule, the card, E6, E5 and E12, recorded as measured and not rerun. AC-8 fails on
  restating in every style and on the offer turn in Reflective. Per bullet, out of 3, Direct / Supportive /
  Reflective: no restating before the offer 1 / 0 / 0; first reply asks what the decision is 3 / 3 / 3; offer
  at message 3 or later 3 / 3 / 3 (from 3 / 2 / 1); the offer turn steps from what they said, says how the
  questions help and asks, with no recap 3 / 2 / 1 (from 0 / 0 / 0); after the yes asks nothing told 3 / 3 /
  3. Every offer was `structured_problem_solving`, so ABCDE was not reached. "Frustrating" came back at the
  person's first message in 7 of 9 runs ("That sounds frustrating", "It can be frustrating", "that back and
  forth is frustrating"), now with reasoning that names their frustration as what they face; Reflective
  also opens by retelling ("It sounds like the decision keeps pulling you back…"). The three offer turns that
  failed recap their details ("The better pay and responsibility on one side, and the familiar people…").
  The say back after the yes came in 4 runs (measured only). Regression, `disclosure_no_question_needed`
  once per style: no offer in any, none cold; "I'm here with you" in Direct and Reflective (off style).
  Prompts 145 lines and 3,422 words; pytest 690 passed, 4 skipped, integration 147 none skipped. Twelve runs
  cost 0.02 dollars.
- Local Supabase answers on the 5434x ports set in `config.toml`. See `.claude/BACKEND.md`.
