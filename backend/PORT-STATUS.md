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
  2. Code decides one thing about which framework: an imminent action (`eligibility.py`) makes DBT STOP the candidate, with its offering stage in `[ctx]`. Every other choice is the model's, from the Framework Index.
  3. `context.py` builds the `[ctx]` block: style, offer timing, the stage in progress and the stages
     after it. Nothing in code classifies what the person said: whether a reply is vague, a correction or
     a wish only to be listened to is the model's reading (`response_format.md`, reasoning).
  4. One model call (`mani/llm/`, LangChain on OpenRouter) returns a structured reply: `reasoning`, `style`,
     `heading_toward`, `next_move`, then `text`. The order is deliberate.
  5. `redraft.py` may ask once more (twice for a missing question): an
     offer before it is allowed or one their words rule out, an offer the draft's `next_move` did not
     choose or a chosen offer with no button, no question (unless the draft chose a shape that asks nothing), or the last reply's question asked again.
  6. `repairs.py` corrects what remains, in code: script leakage, buttons, an early offer.
  7. Crisis, the reply, the framework state and the summary are written together.
- **Frameworks** (`content/frameworks/*.md`, seeded to `admin.frameworks`): only ABCDE is seeded and offered
  (the client's ABCDE document of 2026-10-09). The other five are kept in `content/frameworks/paused/`; the seed
  sets their rows inactive (never deleted, since threads and exercises refer to them), and moving a file back up
  brings it back. ABCDE ends on E and then the shared body check-in below (muhammad, 2026-10-09: the check-in
  is asked). The shared body check-in and practice come from `content/prompts/somatic.md`.
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
- **Scenario check**: `scripts/scenario_check.py` replays the client's test conversations (`scripts/scenarios.json`)
  through the real stack in every style. It flags replies that hand the person's words back, styles that ask the
  same question at the same point, internal words, and offer mistakes, and removes the users it created.

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

- **A question is sent back for asking what Mani already has** (`redraft.asks_what_is_known`, 2026-10-14) when, the
  words any question is put in (`_QUESTION_FRAME`: what, your, would, about...) left out, it shares 60% of its words
  with one of Mani's last four questions, or when every word of it (a final s aside) is in one slot of their read. One
  word of its own, such as whether something is still so, makes it a new question. With the frame counted, 17 of 26
  captured firings were different questions ("What did your manager do?" against "What are you afraid your
  colleagues think?"); without it 4 of 12, catching 8 of the 9 real repeats. The read check fired in no run.
- **A read still after the same unknown is noted, not redrafted** (muhammad, 2026-10-14; `redraft.same_unknown`). It
  shows in the debug read notes and the log. Of 17 captured firings about 12 followed "idk", a correction or a request
  for help, where wanting the same thing was right, and the redraft left it unchanged 11 times.
- **A yes typed to an open offer is held to the same first-stage checks as a tap** (2026-10-14): `redraft.reasons`
  judges each draft from the stage the draft itself starts when it accepts (`orchestrator._accepts`).
- **A token whose account is gone gets 401, not 500** (2026-10-14): a write it makes fails the `*_user_id_fkey` to
  `auth.users`, which `main.py` answers as an expired session; any other foreign key failure is still a 500. No
  per-request lookup of the user.
- **Production refuses to start with `AI_DEBUG_MODE=true`** (2026-10-14, `Settings._production_needs_its_secrets`):
  debug mode puts the model's reasoning about the person in every reply. The chat tester runs it against a local
  backend only.
- **Error reports carry nothing the person said** (2026-10-14): Sentry is initialised with `send_default_pii=False`,
  `max_request_body_size="never"` and `include_local_variables=False` in `main.py`; the SDK attaches request bodies
  and frame locals by default. `tests/unit/test_error_reports.py` holds it.
- **A turn's model calls share a 25 s budget** (`redraft.REDRAFT_BUDGET_MS`, 2026-10-14). A redraft is cut at what the
  budget has left and is not started when under 5 s is left (`REDRAFT_MIN_MS`). A degraded upstream made every
  call 20-60 s, and redrafts (about 60% of calls on this branch, against 3% on main) pushed turns past the client's wait.
  A failed or timed-out redraft keeps the first draft. A first call is cut at `llm_timeout_seconds` in total.
- **`[ctx]` carries each recent question with what they said back (`asked_and_answered`)** (muhammad, 2026-10-14). Question
  memory is required: with none, 9 flags in 12 scripted conversations against 2-3 with it. Question plus answer against
  question only was a tie on that measure; kept for the answer being in front of the model.
- **A reply is two parts that each stand alone** (muhammad, 2026-10-14): what Mani makes of it in whole sentences, a blank
  line, then one question with its subject named. `mani_base` voice rule plus a Readability step in `response_format`.
- **The question joins the feeling to the part of the situation Mani knows least, and the heard-or-help check waits for impact**
  (muhammad, 2026-10-14). A generic "how is this affecting you" is answered by the feeling already named, and a `response`
  that merely restates what they do ("they make the changes") no longer opens the check. Prompt rule in `before_an_offer`,
  `question_focus` for Supportive, and `support_check` requires `impact`.
- **A turn is one model call, or more when a draft is redrafted**. The one scoped extra
  call is the exercise pick at the end of a framework. `test_a_turn_costs_exactly_one_provider_call` still
  holds for a draft that needs no redraft.
- **A framework is offered when the model chooses next_move offer**: it fits and another question would not change
  what Mani understands (muhammad, 2026-10-13). No count holds a first offer back or forces one. After Keep chatting
  no offer comes in that reply or the two after it; urgent actions do not wait. Every
  reply before an offer asks one question, unless any question would be unreasonable, and what they say back about how it is for them is how the set
  is found. The set is chosen by what hurts, by its Use it when and
  Telling them apart; Structured Problem-Solving only once they say they want a decision or plan. No phrase
  matching ranks or shortlists them: the model chooses, code only checks (cooldown, already offered, what they
  said that rules one out) and owns the imminent action (muhammad, 2026-10-09; 2026-10-08: when a weak router
  guess stopped being the candidate, wrong SPS offers went from 4 of 10 live conversations to 0).
- **Mani carries a structured read of the person, every turn** (muhammad, 2026-10-13): `Reply.working_read` is slots (situation, feeling, meaning, since, impact, response, wants, support, underneath, unknown), stored as JSON in `thread_summaries.working_read` (migration 012, a `text` column: only the backend reads it, always whole, and `WorkingRead.stored` reads anything that is not a read as none) inside the turn's own transaction and shown in `[ctx]` as `read_*` lines, their words disarmed like the message. A slot of theirs a reply leaves empty keeps what the stored read held (`repairs.carried_read`); `underneath` and `unknown` are Mani's and are replaced. `feeling` keeps only words they used (`repairs.grounded_read` drops the rest), `since` is null unless they said it, and Mani adds no today or right now they did not say. The client's "What would you like us to focus on today?" is offered only before a read exists. A set is not offered until Mani has said what it makes of their situation and they have answered (`understanding_said` plus `redraft.stated_understanding`, a structural check on Mani's own earlier replies). `before_an_offer` in `mani_base.md` was trimmed from 24 bullets to 13 on the same day. Not yet measured across the full scenario set; `scenario_check.py` now flags an invented time frame, a repeated question and an empty reply.
- **Message 1 and questions follow context, not a pattern** (muhammad, 2026-10-13): with almost nothing said, such as only a feeling, Mani asks one gentle open question and makes no guess (`[ctx]` `read_so_far: nothing yet`); it offers a possibility once there is a situation, a person or an event to build on. A question is chosen by what a thoughtful listener would ask next. A choice between two readings is allowed only when both come from what they said and the answer tells Mani something it needs, never two replies in a row (`redraft._is_choice`). The heard-or-help question waits for what it is doing to them or what they do about it. The body practice wording and the exercise card at the end of a framework are unchanged. The behaviours are written in `docs/mani-behaviour-spec.md` (draft).
- **Memory is per person**.
- **An offer names the pattern, then its framework** (the word may be said), building on the newest thing they
  said, then the client's permission question; the client's description is shown only when they ask to hear more. The offer opens with two or three sentences naming the pattern Mani sees across the conversation, then the client's pattern line (muhammad, 2026-10-13).
- **Each style is its own way of talking.** Its recipe and its own question focus ride on every turn in `[ctx]`:
  All three ask about the core of what is going on for them (muhammad, 2026-10-13); Direct goes straight to the
  core, Supportive asks gently about the core and how it is for them, Reflective asks what sits behind it. Direct
  is never cold or interrogative: a short line of its own that shows it got the point, then the question, never
  more facts about the event for their own sake. Mani reflects only when it adds understanding, never as a formula before every question.
- **An offer carries the client's three buttons**, Try it, Tell me more, Keep chatting, set in `repairs.py`
  whatever the model labels them; after Tell me more it comes back with the other two.
- **Inside a framework, a stage their words already answer is confirmed with them, never skipped and never asked
  again** (muhammad, 2026-10-14, reversing 2026-10-09 and matching the client's ABCDE document): the model walks the
  stages in order from the one in force, and for each stage it has an answer for (here, in the `read_` lines or in the
  Conversation Context) says what it understands as a possibility and checks it with one of the `stage_check` lines,
  a different one each time, marking the stage `confirm`; when they agree the stage is `known` and the next reply goes
  on. One stage per reply, the first not yet confirmed, reported in `state.step`. `[ctx]` carries the current and next stage in full and every
  later stage up to the closing as `later_stage` (`ready_when` and the style's `ask`). Before the text the model fills
  `stages_known`: from the stage in force, each stage with what they already said for it, in their short words,
  and whether it is met, stopping at the first that is not; the question asks only for what that stage's known
  does not hold. A draft whose `state.step` disagrees with its own ledger is redrafted once
  (`redraft.ledger_stage`); a draft with no ledger is not judged by one. `Framework.may_skip`
  decides what is never skipped, the closing and the body route, and `Registry.clamp` corrects a jump over
  them to the closing. This holds from the turn they say yes. No stage question carries a button: a
  "Not sure" button was added by mistake and removed (muhammad, 2026-10-09). The chosen style rides on every
  framework turn in `stage_note`. A stage that is asked moves on once its `ready_when` is met, never needing
  complete or certain answers. A partial answer gets at most one more question. **No stage is asked a third time**
  (muhammad, 2026-10-12, after a dispute loop): `thread_technique_state.stage_asks` counts the replies on a stage,
  a reply that reports no `state` included (`repairs.apply` takes it as asking the stage in force),
  `[ctx]` says `stage_asked: twice` at two, the ledger check lets it go, a draft that stays is redrafted once
  first, and if the reply still stays the recorded phase moves on and the reply's closing question is replaced
  with the next stage's question, so the person is never asked it a third time. The closing and body route are exempt. A question that makes them
  uneasy is let go and the next stage asked; memory records it. Unsure typed ("I don't know", "not sure") is
  still helped once before the stage moves on: Mani offers what their situation or feeling points to as a
  possibility to check, or the client's don't-know line, then weighs whatever they say against the stage
  (muhammad 2026-10-10; now the model's reading, not a phrase list).
- **Only ABCDE is offered, from the client's ABCDE document** (muhammad, 2026-10-09; naming and confirming stages
  restored 2026-10-14). The offer lists the five stages after the permission question (`stages.offering.stage_list`,
  left out on the Tell me more re-offer). After Try it the reply opens with the consent line, then every stage
  message starts with its own label, "A is for Activating Event." through "E is for Effective New Belief."
  (`stages.<stage>.label`), put there by `repairs.with_stage_label` the first time the stage is asked, never on a
  re-ask. A stage already answered is stated as a possibility from a per-style pattern (`stages.<stage>.confirm`) and
  checked in one of about four equivalent lines per style (`stages.offering.check`); one stage per turn. The ledger
  still lives in the sidebar, and the closing (E) is always asked. Where a stage is not known it asks, using the
  feeling word they gave if they named one. Tell me more is
  the five steps as bullet points in the person's style, word for word (`stages.offering.explain`), the offer follows the
  client's pattern per style (`offer`), Keep chatting asks the client's question (`keep_chatting`), the permission
  question is "Would you like to try it?" in every style, and the body check-in is asked after E (muhammad
  decided to keep it). An imminent action points to no framework while STOP is paused (`urgent` is false
  unless `dbt_stop` is in the registry). Supportive inside a framework adds no extra reassurance, validation or
  questions.
- **The stage ledger** (`stages_known`, written before the reply): each stage with what they already said and a
  `status` of known (they confirmed it), partial (ask only the gap), confirm (checking it now) or missing. With `AI_DEBUG_MODE` on, a turn
  returns `ledger`: every ABCDE stage as confirmed, partial, confirm, missing, done earlier or not reached, with
  the stage the reply asks marked, and the chat tester shows it in the sidebar under "What Mani knows". While a
  framework runs it is always returned: a reply without `stages_known` shows the recorded stage as "no ledger sent"
  (and logs a warning). On the turn they say yes, their messages before it go in `[ctx]` as `said_before_yes`.
- **No phrase lists judge the conversation** (muhammad, 2026-10-09): code holds no list of what people say
  (vague, unsure, correcting, wanting only to be heard), no list of feeling words, no list of self-judgments
  and no pain words. The rules for those live in the prompts, and a draft answers them itself: a reply that
  asks nothing says so by its shape (`schema.NO_QUESTION_SHAPES`). What code still checks is not about meaning:
  the crisis screen, script and internal-word stripping, the `[ctx]` injection guard, the imminent-action
  phrases, the body route's place and decline words, and `never_offer_when_said` in the framework files.
- **Questions before an offer are about one part, and how it is for them** (muhammad, 2026-10-09). They now find the core of the concern, may offer two or three possibilities from the person's words, and may say an understanding to check (muhammad, 2026-10-13, after Lolly's ChatGPT conversation). The model
  listens for the core of what is going on for them, asks what happened only if it does not know,
  then asks about something real and present in it, in their words, and lets them find the word, never saying a
  feeling they did not say. Never a hypothetical ("what would it mean"), never "what would it be like if"; asking how something they said is affecting them is fine in their own words, and a feeling word may be used in a question to confirm or correct (muhammad, 2026-10-09), never told to them as what they feel; a
  fear of what may happen gets what they have noticed since, never why they think it. Before asking, the model
  splits their message into what happened, what they conclude and what is still unsaid, and asks only for the last
  (the reason they gave for a thought is already answered). Direct goes straight to the core, Supportive
  asks gently about the core and how it is for them, Reflective asks what sits behind it. Direct opens with a
  short line of its own that shows it got the point, then the question, never their sentence handed back. One
  question, never harder than the last, no two-part questions. Two or three possibilities taken from their words
  are allowed in one question, and a vague or unsure reply may get them. No advice or suggestion hidden in a
  question. `heading_toward` decides which set is offered, and questions may reach for what that set still needs,
  always through their words (`context._MEANING["conversation_phase"]`). Mani never joins two things they said into a link
  they did not make. Told it got something wrong, in any words, it says it misunderstood and asks what would be
  more accurate (the client's line), never explaining what it meant.
- **"Just tell me what to do"** gets: Mani cannot hand over a solution but can help them work it out, then the question that leads there; Structured Problem-Solving stays paused (muhammad, 2026-10-13).
- **Mani's language is plain, everyday English**: correct grammar and punctuation, each sentence short enough
  to say in one breath, as people talk in daily life (`mani_base.md` `voice`). Stage questions inside a
  framework keep the framework's own wording and are not made about feeling.
- **`[ctx]` explains itself.** Each line carries its meaning for this turn's value on the line under it
  (`context._MEANING`), so `response_format.md` holds only what the block is. A test fails if a key is sent
  without one.
- **An open offer is read from the database, not from the buttons on screen.** A yes to it starts it either
  way, and asking about it (Tell me more, or a typed question) is answered by offering it again. A typed message counts as asking only when the reply reports the offer with `accepted` left null; any other typed message is Keep chatting.
- **"It hit me so hard" is not violence.** `safety.screen` sets aside "hit me" when a thing is its subject
  (it, that, this, what); a person hitting them still asks.
- **chat-tester resets a password on the page**: email and new password, set through the Auth Admin API with
  no email. Anyone who can reach the page can reset any account, so it stays non-public. A browser session
  is remembered for seven days.
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

- Tell the client (2026-10-08): "overwhelming" was removed from the Structured Problem Solving description,
  since every offer showed a feeling the person had not named; Supportive and Reflective questions were
  written for the 26 stages whose three styles were identical (the client's wording is kept as Direct, or as
  Reflective for ACT `present`); the offer buttons read Try it / Tell me more / Keep chatting, not the
  specification's "Yes, let's try it" / "I want to keep talking". Have them review the new lines.

- Crisis resources, `PROTOCOLS` and `CLARIFICATION` wording (point 3 above).
- Tell the client that offers now follow Mani's judgement that another question would not change what it understands, with no count of messages, which replaced their offer cadence, and have them read about five real
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

- **Hosted is one push behind local.** Checked read-only on 2026-10-14: hosted ends at migration `010` with
  neither `stage_asks` nor `working_read`, and its five prompts are the 2026-10-09 seed. RLS is on every public
  table and `authenticator` cannot assume `mani_service`. Production's Vercel environment sets no
  `AI_DEBUG_MODE`, `SENTRY_DSN` or `DAILY_MESSAGE_LIMIT`. The push order (migrations, then code, then seed and
  cache invalidation) and its rollback are in
  `docs/superpowers/plans/2026-10-14-prod-runbook-stage-asks-and-working-read.md`.
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
- **A reply may still jump several stages in code.** The prompts say one stage per reply, never skipped, but
  `techniques.validate_transition` accepts a multi-stage step and only `redraft.ledger_stage`, which trusts the
  model's own ledger, stands in the way. The comments in `techniques.py` and `repairs.py` give the older reason.
  muhammad chose to leave it on 2026-10-14; the options are in `mani-vault/Journal/local-audit-before-merge-2026-10-14.md`.
- The words "worried", "concerned" and "a lot" still reach about 1 reply in 10 in some scenarios; repairs log
  them. The feeling check now redrafts the ones in `repairs.FEELING_WORDS`.

## Latest measurements

Re-measure after any change to prompts, framework content or the offer rules.

`scripts/scenario_check.py`, 2026-10-14, 36 conversations in 3 styles (the script logs nothing itself; run it
under `logging.basicConfig(level=logging.INFO)` to count redrafts). Redrafts on 45 of 198 and 51 of 192 replies,
then 18 of 189 and 21 of 190 once the earlier-question check left the question frame out and the same-unknown
check stopped redrafting (main: about 3% of calls). Now by reason: an earlier question 4 and 8, an offer instead
of what they asked for 8 and 5, a choice twice 1 and 6. Flags 31 and 39, mostly two styles asking the same
question; "asks a question it already asked" went from 7 and 6 to 8 and 10, but that flag counts the question
frame as the redraft check used to: of the 11 flagged pairs in the last run one was a real repeat. Offers at their
message 2 to 6 in 11 to 12 conversations, none in the rest. A full ABCDE walk in
each style through the HTTP API reached Chat More / Go to Library in 14 to 15 messages with no stage but the
closing asked a third time, and the place buttons when the check-in answer named no place.

Taken 2026-10-01 with the earlier eval harness, since removed:

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
