# Port status

What the backend does today and what is still open. Stack notes: `.claude/BACKEND.md`. Database rules:
`.claude/SUPABASE.md`. Why it is built this way: `mani-vault/Decisions/_Index.md`. **Update this file in
the same change as the work.**

History (how the port went, what was fixed from review, old measurements) is in
`mani-vault/Journal/port-history-2026-09.md`. It is accurate as of the end of the port, not as of today.

## Status, 2026-10-01

- The TypeScript to Python port is complete. FastAPI is the only thing that touches the database.
- Tests: `pytest` runs 840 passed, 4 skipped (the four symmetric-token auth tests, which skip on a
  JWKS-configured project).
- Database: 10 migrations, 15 tables (8 `public`, 7 `admin`), 6 frameworks and 5 prompts seeded.
  `admin.exercises` holds the 17 library exercises from `content/exercises/`, with their audio in the
  private `exercises` bucket (`scripts/seed_exercises.py`). A hosted project does not exist yet.
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
     is a concern: it suspends frameworks and offers without locking.
  2. The router (`router.py`) shortlists frameworks from phrases over their last four messages. It is a hint, never a requirement. When the nearest fit falls due, the top of the shortlist carries its offer wording even if the router is not confident of it.
  3. `context.py` builds the `[ctx]` block: style, offer timing, the stage in progress, and `their_last`
     (a short reply of three words or fewer, with `answering`, the question Mani last asked; a correction; or a
     request only to be heard).
  4. One model call (`mani/llm/`, LangChain on OpenRouter) returns a structured reply: `reasoning`, `style`,
     `heading_toward`, `offer_fit`, then `text`. The order is deliberate.
  5. `redraft.py` may ask once more: a feeling word or size phrase the person never used, an offer before it is
     allowed or one their words rule out, or an offer that is due and missing. The notes never ask for a question.
     A repeated question and a reply with no question go through as drafted. ADR-006, ADR-007, ADR-012.
  6. `repairs.py` corrects what remains, in code: script leakage, buttons, an early offer. A second draft that still
     uses a feeling word they never used is logged and left as drafted, never trimmed.
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
  Inside a framework a reply to a stage is answered by asking the stage after it (spec 0003, ADR-013 proposed):
  whatever they say, "I don't know" included, `context.build` shows `answered` and the next `stage` without the
  old question, and `repairs.apply` records only the next stage or a hold (`held at <stage>` in the repair
  notes). The turn they accept, a stored `offering` and the body check keep the earlier rules. Stages with no
  `ready_when` after the first; 36 branches kept, 49 dropped; 26 stages carry an `if_earlier_missing` question for
  an earlier answer that never came; ABCDE and Thought Reframe have one more stage each (`evidence_for` and
  `evidence_against`, `facts_for` and `facts_against`). A local thread stored at the old `examine` or `facts` restarts
  at the offering.
  A stage may take one extra turn, counted in `thread_technique_state.holds` (migration 011): a question said
  again once in simpler words, one of the person's own options offered at Behavioral Activation `choose` and
  Structured Problem Solving `select` (those stages get a `stage_note` of their own that leads with the offer),
  and DBT STOP's five acting branches (`counted: true`). A redirect (safety, a framework that does not fit, the
  client's three lines) is not counted, and the code recognises it from the reply or Mani's message before it
  (`repairs.carries_redirect`); the model marks nothing. A second counted hold records the next stage
  (`hold limit at <stage>`). 27 stages carry `if_earlier_missing`.
- **Memory** (ADR-005): per person, folded from earlier chats by `mani/memory.py`; idle threads fold through
  `scripts/fold_idle_threads.py` or `GET /internal/cron/fold-summaries` behind `CRON_SECRET`.
- **Exercises**: catalog, completions and signed URLs (`mani/storage.py`). A completing framework picks one
  exercise from the whole active catalog with one bound tool call (`mani/llm/tools.py`): the framework's own
  exercises are listed first, and the pick sees the person's last three messages and the thread's current
  issue. `GET /v1/exercises` is the whole catalog, and responses never carry the storage path.
- **Admin**: prompt CRUD with versioning, exercise CRUD, crisis event review, a user's memory.
- **Account deletion**: `DELETE /v1/account` removes the user and everything they own.
- **Eval harness**: `scripts/eval_replies.py` runs scripted conversations through the real stack and removes
  the users it created. `tests/evals/` holds the deterministic checks every suite runs.
  `scripts/eval_client_style.py` runs the client's four style conversations (panic, a friend's text, compulsive
  scrolling, stress before a deadline) in all three styles, three runs by default. It does not pass or fail: it
  saves every transcript (`transcripts.md` and `transcripts.json`, with taps marked) and prints questions in
  Mani's own words, stock phrases per phrase, repeated openers, feelings and size phrases never used, dashes, replies over three
  sentences and the message at which the offer comes, per conversation and per style, with a figures block
  against specification 0002's criteria. `style_read.md` holds the panic replies to the first two messages, shuffled with the style hidden, for marking.
  `short_replies.md` lists every reply that follows a message of three
  words or fewer. The client's lines are in `client_style_conversations.yaml`;
  after the first, each line taps the offer when the last reply made one.

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

The record is `mani-vault/Decisions/_Index.md`. In short:

- **A turn is one model call, or one more when an offer is vetoed** (ADR-002, 006, 012). The one scoped extra
  call is the exercise pick at the end of a framework. `test_a_turn_costs_exactly_one_provider_call` still
  holds for a draft that needs no redraft.
- **Offers follow Mani's confidence** (ADR-007). A reply asks at most one question and may ask none; ADR-012
  (proposed) replaced ADR-008's question in every reply.
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
- Tell the client about ADR-007, which replaced their offer cadence, and have them read about five real
  Supportive and Reflective transcripts.
- Tell the client about ADR-011: when a person asks Mani to pick, it offers one small draft step to accept
  or change, which the Behavioral Activation specification's "must not choose the activity" does not allow
  as written.
- Tell the client about ADR-010: after Try it Mani no longer asks the first stage's question when the person
  has already said it, and a person who cannot say what to do is offered up to three options at the first
  "I don't know". Both depart from the literal Structured Problem Solving example.
- Spec 0003, redirects: the model's own mark was wrong 24 of 24 times and is removed; the code now recognises a
  redirect by its words. No scenario contains a real redirect, so how often the model quotes a safety branch or
  one of the client's lines is unmeasured. Open follow up work in the spec: end or pause the framework on a safety
  branch instead of holding, four redirect branches whose reply is scenario wording and cannot be recognised, the
  "I misunderstood" line used as an uncounted rephrase, and no exit state for the "stop here" line.
- Spec 0004 (row 37), the model's safety flag now names a kind (`Crisis.category`, the screen's eight kinds plus `other`).
  A real kind pauses a running framework as before; `other` is treated as no flag; a missing or unknown kind pauses.
  Built and tested; measured on 38 authored messages: urge messages flagged 11 of 40 before and 0 of 40 after, risk
  messages 148 of 150 both times. The nine kinds must be in the system prompt (`response_format.md`), not only the
  schema, or the model writes its own labels; that section also carries the rule that doubt goes to a danger kind and not
  `other`, and a test checks the prompt and the description name exactly the set the code reads. A threat or a wish to hurt a person
  is `harm_to_other` even when angry or vague, never `other`; six ambiguous threats (AC-9) paused 25 of 30 runs after
  that sentence (23 before), the one gap being a resentful wish, "I want her to suffer the way I did". The risk bar was accepted by muhammad on these numbers. DBT STOP run once (3 conversations): all reached the
  body check, and a model flag read as `other` let the framework go on. The client approved the kinds, both texts and
  the set (AC-10, an earlier page; the corrected page was not re-sent). Final wording measured: risk 176 of 180
  (every message but the known gap 5 of 5, none called `other`), urge pauses 4 of 40 (11 before). Done 2026-10-04.
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
- "a lot" still reaches about 1 reply in 18 in the stress before a deadline conversation, and meanings the word
  lists cannot see ("stuck in a loop") reach people. Open for the client: may "a lot" stay, as their own lines use it.

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
- Client style conversations, baseline taken 2026-10-04 with `scripts/eval_client_style.py` (three runs, model
  `google/gemini-3.1-flash-lite`, `mani_base` md5 `84627c5f`, commit `476edf0`; 36 conversations). This is the
  measurement Natural Mani (scope rows 33 to 35) is judged against:
  - Every reply asked exactly one question: questions equal replies in all 12 conversation and style rows.
  - The offer came at message 2 to 6. Three of 36 came after the client's two to four (panic Supportive and
    Reflective, stress Reflective). Direct was at 2 to 4 every time.
  - Stock phrases ("I hear you", "I'm here for/with you", "That makes sense") per conversation: Supportive 0.6,
    Reflective 0.4, Direct 0.1. Panic is the worst, 2.0 for Supportive.
  - Replies opening like the one before them, per conversation: Supportive 0.8, Reflective 0.4, Direct 0.2.
  - Dashes: 2 in all 36 conversations, both in panic Supportive.
  - The counts carry run to run noise (panic Reflective offered at 6, 4, 2), so compare means of three runs, never one.
- Client style conversations after specification 0002 (scope row 33), same check, same model, three runs each.
  Baseline recounted with the extended check, then the code change alone with the old prompt, then the rewrite
  (`mani_base` 120 lines). Full tables and what differs from the spec's figures: `mani-vault/Journal/natural-mani-build-2026-10-04.md`.
  - Questions per reply, Mani's own words: 0.59 baseline, 0.60 code alone, 0.48 rewritten. (The 0.7 bar was already met.)
  - Stock phrases per conversation: 0.08 / 0.42 / 0.58 (Direct, Reflective, Supportive) baseline, 0 / 0 / 0 rewritten.
  - Feelings never used: 0 baseline, 10 code alone, 0 / 2 / 2 across three prompt only checks, 0 with the feeling and
    size redraft restored (muhammad, 2026-10-04). AC-6's bar settled at under 0.5 own words (0.47 measured).
  - Offers: 36 of 36, 35 at exchange 2 to 4 (baseline 33). Dashes 0 (baseline 2). Replies over three sentences 0 (baseline 1).
  - Size phrases never used without "a lot": 0 (baseline 5); "a lot" 4 (baseline 16). Last check: own questions 0.49, 36 of 36 offered, 35 at exchange 2 to 4.
  - Final check (`style-lines-1`, the prompt in force: `mani_base` 120 lines with the restating rule and the three
    style lines, and the stock phrase ban repeated in `response_format.md`), same model, three runs: own questions
    0.54 per reply, stock phrases 0.83 / 0.00 / 0.67 (Direct, Reflective, Supportive), "It sounds like" or "It seems
    like" 14 in 36 conversations (baseline 49, 9 to 15 across the last checks), feelings and size phrases never used
    0, "a lot" 3, offers 36 of 36 all at exchange 2 to 4, dashes 0, replies over three sentences 0.
  - Read blind by a fresh model whose marks muhammad accepted as final (his choice, a departure from the spec as first written):
    restating 42% of eligible replies (8 of 19) against 88% before the rule (15 of 17), AC-14 met; meaning stated as
    fact 0 against 5 at baseline, AC-8 met. The same reader scored the same baseline 43%, 60%, 57% and 47% across
    four files, so compare only inside one file.
  - Not met: AC-9 (the three styles differ in what Mani does) reads 10 of 18 against a bar of 15, after both rounds
    the spec allows. The offer part of the base says the questions are ones "you could go through together" in every
    style, so offers read Supportive; scope row 6 rewrites that. AC-7's zero for "sounds like" and its per style
    bar of 0.3 are also not met; muhammad accepted the rate and the client is to be asked. `/architect` amends both.
- Moving a stage on after one answer (spec 0003), first real runs 2026-10-04 with `scripts/eval_replies.py`, one
  scenario per framework started inside it, three runs, every style (54 conversations, `mani_base` 120 lines):
  - One stage per reply, in order, in all 54. No stage stayed put without a hold and none was asked twice.
  - Reached the body check in 50 of 54; the four misses each followed a hold that used up a turn.
  - Four holds, none of them in the spec's list: three Behavioral Activation replies to "what do you mean?" at
    `barrier`, and one Structured Problem Solving reply that gave the hand off but reported `closing`, which dropped
    the Chat More buttons.
  - "Pick one for me" at Behavioral Activation `choose` gave one step in 9 of 9. "Tell me what to do" at Structured
    Problem Solving `options` got "that is yours to decide" in 8 of 9, because that framework's own boundaries say
    never choose for them. Changing the base prompt's wording did not move it.
  - Replies to "what do you mean?" were answered in a clause and moved on in 51 of 54.
- The two holds (spec 0003, tasks 6 to 8), 2026-10-04, 54 conversations, scenarios with a rephrase asked twice and
  "suggest something": reached the body check 54 of 54; no `hold limit`; 27 counted holds and 24 marked redirect, none
  of the 24 a real redirect; "I don't get it" held about four times in ten (ABCDE and Thought Reframe nearly always
  moved on); "suggest something" held 5 of 9 at Structured Problem Solving `select`, 1 of 9 at Behavioral Activation
  `choose`. muhammad read one transcript per framework on 2026-10-04: pass for all six.
- Same day after removing the redirect mark and adding the pick note, 54 conversations again: 54 of 54 reached the body
  check, no hold limit, no redirect hold, no stage held twice; "suggest something" held 7 of 9 at `choose` and 8 of 9
  at `select`; 63 counted holds. muhammad read one transcript per framework: pass for all six. ADR-013 accepted.
- A request to hear a question again (spec 0003, AC-17), 54 conversations: the code recognises it from phrases, shows
  the model only the stage's own question and records the counted hold; the first "I don't get it" was held 9 of 9 at
  every framework (was 25 of 54), the second never, 54 of 54 reached the body check, and after the note was reworded to
  ask one question no rephrase had two (was 20 of 54). muhammad read one transcript per framework: pass for all six.
- Local Supabase answers on 54321 to 54324 on this machine, not the 5434x in `config.toml`. See
  `.claude/BACKEND.md`.
