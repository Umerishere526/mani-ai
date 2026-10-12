# Port status

What the backend does today and what is still open. Stack notes: `.claude/BACKEND.md`. Database rules:
`.claude/SUPABASE.md`. **Update this file in
the same change as the work.**

## Status, 2026-10-01

- The TypeScript to Python port is complete. FastAPI is the only thing that touches the database.
- Tests: `pytest` runs 439 passed, 4 skipped (the four symmetric-token auth tests, which skip on a
  JWKS-configured project).
- Database: 11 migrations (001 to 010 and 018), 15 tables (8 `public`, 7 `admin`), 6 frameworks and 5 prompts seeded.
  `admin.exercises` holds the 17 library exercises from `content/exercises/`, with their audio in the
  private `exercises` bucket (`scripts/seed_exercises.py`). A hosted project does not exist yet.
- Models: `openai/gpt-6-luna` for chat and for summaries (`mani/config.py`), routed Azure first with
  OpenAI as the fallback. It is a reasoning model: it takes no `temperature` on any provider and reads
  `reasoning_effort` instead, so `mani/llm/chain.py` sends the sampling parameters an ordinary
  chat model takes only to models that accept them. A prompt row names its own effort in
  `model_parameters.reasoning_effort` and `mani/config.py` holds the default for the calls that have
  no row of their own; `mani_base` is on `low` (2026-10-12) and so is the exercise pick that follows
  it, while `summarization` and `memory_fold` are on `high`. Effort is billed: measured against Azure,
  `high` spent 26 reasoning tokens where `low` spent 0, about three times the cost of the same call. The fallback keeps `data_collection: deny`, so
  training use stays refused, but a turn that cannot reach Azure is processed by a different company -
  a data protection question that is open, not settled.
- Every call to OpenRouter carries the same provider order, data policy and reasoning effort, from
  `chain.request_body`. The voice translation in `mani/stt.py` calls the SDK directly and used to send
  none of them, so a transcript went to whichever provider OpenRouter chose; it now uses the same body.
  It is still not recorded in `admin.llm_calls`, which has no purpose for it.
- A reasoning model's output budget covers its thinking and its reply together. Every caller sizes
  `max_tokens` for the reply alone, so `chain.sampling` adds `REASONING_ALLOWANCE_TOKENS` (8,192) on top.
  Without it, at effort high, 4 of 61 chat calls ran out of tokens while thinking and the turn failed
  (2026-10-07). Measured at high: 12.6 s for an average turn, 41 s for the longest. Not measured at
  low: the target is a median of 4 s and a slowest of 10 s, and `scripts/scenario_check.py` now prints each
  turn's time, calls and tokens (`admin.llm_calls.reasoning_tokens`, migration 018) to check it.
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
  2. Which framework fits, and whether one fits yet, is the model's call from the Framework Index. Code owns only when an offer may come (`context.offer_window`) and the safety screen.
  3. `composer.py` builds the system prompt with the one style file the thread chose, and `context.py`
     builds the `[ctx]` block: style, offer timing, the stage in progress and the stages
     after it. Nothing in code classifies what the person said: whether a reply is vague, a correction or
     a wish only to be listened to is the model's reading (`response_format.md`, reasoning).
  4. One model call (`mani/llm/`, LangChain on OpenRouter) returns a structured reply: `reasoning`, `style`,
     `heading_toward`, then `text`. The order is deliberate.
  5. `reply_checks.py` costs no call: it sets `state.step` from the reply's own ledger when they disagree,
     and counts what code cannot fix (an offer that is due and missing, no question unless the draft chose a
     shape that asks nothing, the last reply's question asked again) in the logs and in `Turn.checks`.
  6. `repairs.py` corrects what remains, in code: script leakage, buttons, an early offer.
  7. Crisis, the reply, the framework state and the summary are written together.
- **Frameworks** (`content/frameworks/*.md`, seeded to `admin.frameworks`): only ABCDE is seeded and offered
  (the client's ABCDE document of 2026-10-09). The other five are kept in `content/frameworks/paused/`; the seed
  sets their rows inactive (never deleted, since threads and exercises refer to them), and moving a file back up
  brings it back. ABCDE ends on E and then the shared body check-in below (muhammad, 2026-10-09: the check-in
  is asked). The first offer may come from the person's third message; from their fifth it is due, which asks
  for an offer only if one fits, in every style. The shared body check-in and practice come from `content/prompts/somatic.md`.
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
  through the real stack in every style, including the four scenarios of the client's styles document. It flags
  questions that ask for what they already said, internal words, and offer mistakes, and removes the users it created.

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

- **A turn is one chat call at effort `low`, never a second to fix a draft** (muhammad, 2026-10-12). Because the
  client's R2 asks for no excessive latency, a turn waited on a reasoning model at `high` and up to two more
  full calls whenever a draft broke a rule (a median of 12.6 s and 41 s at worst, 2026-10-07), and the reply
  already carries its own written reasoning. Code shapes the reply instead of asking again: while no offer
  may be made a button has no `technique` (`schema.ReplyWithoutOffer`), `state.step` is set from the draft's
  ledger, and `repairs.apply` strips what remains. The checks that need another call to fix are logged, not
  asked for again, so how often each happens is known. The one scoped extra call is the exercise pick at the end
  of a framework, at the chat row's effort. `test_a_turn_costs_exactly_one_provider_call` and the
  `reply_checks` tests in `tests/integration/test_turn.py` hold it. Not yet measured live (needs muhammad's yes).
- **The first offer waits for the person's third message; from their fifth it is due, which never forces an
  offer that does not fit, in every style** (muhammad, 2026-10-12). Because the client rejected an offer on the
  first message (R1 in `docs/client/requirements.md`), their cadence puts about two to four exchanges between
  the issue and the offer and calls that "a range, not a required count" (styles document), and a forced offer
  at the fifth always meant ABCDE, the only set (2026-10-12). Code owns the window (`context.offer_window`:
  not_yet, open, due); `[ctx]` sends not_yet and due but never open, which the model read as "offer now"
  (18 of 18 offers at the third message). At due, a set that fits is offered, and otherwise Mani checks its
  understanding in one question. An offer made before the window opens is stripped (the reply shape has no way to make one). After Keep
  chatting it reopens six messages later and is never due. `test_offer_window_*` in
  `tests/unit/test_chat_context.py` hold it. Every
  reply before an offer asks one question, and what they say back about how it is for them is how the set
  is found. The set is chosen by what hurts, by its Use it when and
  Telling them apart; Structured Problem-Solving only once they say they want a decision or plan. No phrase
  matching ranks or shortlists them: the model chooses, code only checks the cooldown and what was already
  offered (muhammad, 2026-10-09; 2026-10-08: when a weak router
  guess stopped being the candidate, wrong SPS offers went from 4 of 10 live conversations to 0).
- **A framework fits once its offer can be filled from their own words; each fit rule lives once, in the
  framework's `central_indication`** (muhammad, 2026-10-12). Because rules written per case do not scale to what
  people actually say, and three copies of ABCDE's fit rule had drifted apart; ABCDE was offered at message 3 to
  someone who had only described what happened (2026-10-12). For ABCDE: what they are telling themselves, or how
  it is leaving them feeling, not what happened alone; the event stays optional, as the client's ABCDE document
  allows (its Situation 3). Scenario group `describes_only_what_happened` in `scripts/scenarios.json`. Not yet
  measured live.
- **Memory is per person**. Because Mani should learn each person's patterns across chats, while a new chat
  still starts with none of the last one's messages (2026-09-23).
- **An offer is one short line that names its framework** (the word may be said). Because the client's offers
  are one short mirror then the question, and the description belongs after Tell me more (2026-10-09); why
  the word may be said: reason unknown, muhammad to confirm. The line builds on the newest thing they
  said, then the client's permission question; the client's description is shown only when they ask to hear more.
- **One style file per thread, in the system prompt, written from the client's behavior lists** (muhammad,
  2026-10-12). Because the client separates the styles by what each reply is trying to do, and our own recipe per
  style, under shared rules that contradicted their examples, drifted from it (styles document, 2026-10-12).
  `content/prompts/style_directive.md`, `style_supportive.md` and `style_reflective.md` each hold that style's
  behavior, the client's within-framework list word for word, its consent line and two of the client's
  conversations as examples of the sound. `composer.compose` sends only the style resolved for the thread, after
  `mani_base` and `response_format`, so the prefix before it caches once for all three; the Framework Index lists
  only that style's offer and Keep chatting wording. `[ctx]` names the style and carries no recipe. The stored
  value is `directive` (migration 019), with no `direct` alias. All three rows are required at load
  (`cache.REQUIRED_PROMPTS`), so seed before deploying. `test_only_the_chosen_style_reaches_the_system_prompt` and
  `test_a_missing_style_row_is_refused_when_the_prompts_load` in `tests/unit/test_composer.py` hold it.
- **An offer carries the client's three buttons**, Try it, Tell me more, Keep chatting, set in `repairs.py`
  whatever the model labels them. Because the client's offer has three choices, two after Tell me more
  (2026-10-08); after Tell me more it comes back with the other two.
- **An offer the window allows is never dropped for a question beside it; the question goes** (muhammad,
  2026-10-12). Because the old rule dropped the buttons whenever a `?` appeared before the permission question,
  and a reflection quoting their "Why me?" lost a valid ABCDE offer: no buttons, no offered row, and the yes
  after it started nothing (2026-10-12). A question is a sentence that ends in `?`; one quoted inside a sentence
  is not. `repairs._asks_them`, `test_their_quoted_question_does_not_cost_the_offer` and
  `test_a_different_question_beside_an_offer_gives_way_to_it` in `tests/unit/test_repairs.py`.
- **Inside a framework, a stage their words already answer is skipped, with no check and no mention**
  (muhammad, 2026-10-09). Because the client says Mani never makes them repeat what they already said, yet
  people who said it all at once still walked every stage (2026-10-09). The model walks the stages in order from the one in force, skips each whose `ready_when`
  what they said (here or in the Conversation Context) already meets, and asks the first that is not, reporting
  that stage in `state.step` even several ahead. `[ctx]` carries the current and next stage in full and every
  later stage up to the closing as `later_stage` (`ready_when` and the style's `ask`). Before the text the model fills
  `stages_known`: from the stage in force, each stage with what they already said for it, in their short words,
  and whether it is met, stopping at the first that is not; the question asks only for what that stage's known
  does not hold. A draft whose `state.step` disagrees with its own ledger has the step set from it
  (`reply_checks.with_ledger_step`); a draft with no ledger is not judged by one. `Framework.may_skip`
  decides what is never skipped, the closing and the body route, and `Registry.clamp` corrects a jump over
  them to the closing. This holds from the turn they say yes. No stage question carries a button: a
  "Not sure" button was added by mistake and removed (muhammad, 2026-10-09). The chosen style holds inside
  a framework through its style file. A stage that is asked moves on once its `ready_when` is met, never needing
  complete or certain answers, and after two tries unless the stage says to stay. A question that makes them
  uneasy is let go and the next stage asked; memory records it. Unsure typed ("I don't know", "not sure") is
  still helped once before the stage moves on: Mani offers what their situation or feeling points to as a
  possibility to check, or the client's don't-know line, then weighs whatever they say against the stage
  (muhammad 2026-10-10; now the model's reading, not a phrase list).
- **Only ABCDE is offered, from the client's ABCDE document** (muhammad, 2026-10-09). Because the client's
  ABCDE document of 2026-10-09 is what we build to, and ABCDE's stages give the questions a target
  (2026-10-09); why the other five are paused and why the body check-in stays: reason unknown, muhammad to
  confirm. The chat never names a
  stage: no letter, no "A is for Activating Event.", no line for a stage already answered (a version that wrote
  those lines was removed the same day). What Mani knows lives in the stage ledger, and the chat only asks, in its
  own tone for the style, the next thing that is missing, with the document's question for the stage. A stage the
  conversation answers is bypassed without a word; the closing
  (E) is always asked. Step A confirms a possible event once ("Is that right?"), the one place anything is
  confirmed; where it is not known it asks, using the feeling word they gave if they named one. Tell me more is
  the numbered five steps in the person's style word for word (`stages.offering.explain`), the offer follows the
  client's pattern per style (`offer`), Keep chatting asks the client's question (`keep_chatting`), the permission
  question is "Would you like to try it?" in every style, and the body check-in is asked after E (muhammad
  decided to keep it). Supportive inside a framework adds no extra reassurance, validation or
  questions.
- **The stage ledger** (`stages_known`, written before the reply). Because what a stage needs is often half
  known already, so the question asks only for the missing part (2026-10-09). The ledger holds each stage with what they already said and a
  `status` of known (bypassed), partial (ask only the gap), confirm or missing. With `AI_DEBUG_MODE` on, a turn
  returns `ledger`: every ABCDE stage as bypassed, partial, confirm, missing, done earlier or not reached, with
  the stage the reply asks marked, and the chat tester shows it in the sidebar under "What Mani knows".
- **No phrase lists judge the conversation** (muhammad, 2026-10-09). Because literal phrase matching cannot
  read a paraphrase, so its judgments were silently wrong whenever people worded things differently
  (2026-10-09). Code holds no list of what people say
  (vague, unsure, correcting, wanting only to be heard), no list of feeling words, no list of self-judgments
  and no pain words. The rules for those live in the prompts, and a draft answers them itself: a reply that
  asks nothing says so by its shape (`schema.NO_QUESTION_SHAPES`). What code still checks is not about meaning:
  the crisis screen, script and internal-word stripping, the `[ctx]` injection guard, and the body route's
  place and decline words (scope feature 16 replaces those with reply fields). A paused framework moved back
  brings no phrase list with it; anything it needs to detect is designed when it returns (2026-10-12).
- **Questions before an offer ask for what is still missing** (muhammad, 2026-10-09; cut 2026-10-12). Because
  Mani re-asked what they had said and walked them into worst cases (2026-10-09), while the client's own questions
  ask what made them think it, what feels most pressing, and open on their words (styles document, 2026-10-12).
  What each question is trying to do comes from the style file. Shared by all three: when the basic what is
  missing (what happened, what they are deciding), it is asked first; a reflection only checks or shows
  understanding and never hands their words or feelings back (client's job decision feedback, 2026-10-12);
  never asking for something they already made clear, in any words; a feeling word only as a question to confirm
  or correct, never told to them as what they feel; one short question, never harder than the last, no menu of
  choices (a vague or unsure reply gets an easier question about one small part, not two ways it could go), and
  no advice or suggestion hidden in a question. Both sides of one decision in one question, and "what would it
  mean", are allowed: the client asks both (2026-10-12). `heading_toward` only decides what is offered. Mani never joins two things
  they said into a link they did not make. Told it got something wrong, in any words, it says it misunderstood and asks what would be
  more accurate (the client's line), never explaining what it meant.
- **Mani's language is plain, everyday English**. Because muhammad wants human-like language in plain
  everyday words (2026-10-07); why stage questions are not made about feeling: reason unknown, muhammad to
  confirm. Correct grammar and punctuation, each sentence short enough
  to say in one breath, as people talk in daily life (`mani_base.md` `voice`). Stage questions inside a
  framework keep the framework's own wording and are not made about feeling: the client's `ask` for the
  style is asked as written, or only its missing part, never reworded, because rewording it produced
  stacked lines like "What do you find yourself telling yourself about that?" (2026-10-12;
  `mani_base.md` `in_a_framework`, `context._stage_note`,
  `test_a_stage_question_is_asked_as_the_client_wrote_it`).
- **`[ctx]` explains itself.** Because a plain turn paid about 4,900 characters of key dictionary to explain a
  154 character block, and the two drifted apart (2026-10-09). Each line carries its meaning for this turn's value on the line under it
  (`context._MEANING`), so `response_format.md` holds only what the block is. A test fails if a key is sent
  without one.
- **An open offer is read from the database, not from the buttons on screen.** Because an offer can stay open
  with no buttons showing, and a typed yes to it then started nothing (2026-10-09). A yes to it starts it either
  way, and asking about it (Tell me more, or a typed question) is answered by offering it again.
- **"It hit me so hard" is not violence.** Because the client's own ABCDE signal "why it hit me so hard" was
  read as violence and Mani asked if they were in danger (2026-10-08). `safety.screen` sets aside "hit me" when a thing is its subject
  (it, that, this, what); a person hitting them still asks.
- **chat-tester resets a password on the page**: email and new password, set through the Auth Admin API with
  no email. Because the test tool should need no mail setup, accepting that the page stays non-public
  (2026-10-07); the seven day session: reason unknown, muhammad to confirm. Anyone who can reach the page can reset any account, so it stays non-public. A browser session
  is remembered for seven days.
- Also settled: OpenRouter only, asyncpg not PostgREST, the
  `public` and `admin` split, the `mani_service` role, three security definer write functions, the
  deterministic safety screen as the only thing that locks a thread, in process routing, no streaming.
  Because: one provider was ever used (2026-09-14); a turn's writes must succeed or fail together, which
  PostgREST cannot do (2026-09-15); anything PostgREST exposes is reachable with the anon key (2026-09-15);
  a backend acting as `authenticated` let users forge Mani's replies (2026-09-16); the definer functions write
  rows no plain grant should allow (2026-09-15); a small model over-fires the crisis flag on ordinary
  distress (2026-09-29); plain request and response is acceptable while turns stay short (2026-09-14; turns are no longer short,
  so muhammad to revisit streaming after the next measured run).
  In process routing no longer describes the code (`router.py` is gone and the model chooses the framework):
  muhammad to reword or drop it.

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
   tested.
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
- Tell the client what caused the first message offer (R1) and that the first offer now waits for the
  third message and is due by the fifth in every style, and have them read about five real
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

- **Hosted and local schemas match.** Checked read-only on 2026-10-07: the same migrations, columns,
  enums, functions and RLS policies, and the same prompts, frameworks and exercises (only seed timestamps
  differ). The production deployment is `45543ed`, the head of `main`. What prod's environment variables
  hold is not readable, so those are unchecked.
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
  them.

## Latest measurements

Taken 2026-10-01 with the earlier eval harness, since removed. `scripts/scenario_check.py` replaces it; its first
run is the next baseline. Re-measure after any change to prompts, framework content or the offer rules.

- Reached an offer: 36 of 36 conversations (grief had been 1 of 9). First offers at message 2 to 4.
- Redrafts (the loop is gone since 2026-10-12): 7% of replies across scenarios, 17 to 19% on the hardest
  chat (a colleague, an embarrassing meeting). Those are the turns that now go out as first written, and
  `Turn.checks` counts the three kinds that matter; read it in the next `scenario_check` run.
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
