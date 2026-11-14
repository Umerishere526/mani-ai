# Port status

What the backend does today and what is still open. Stack notes: `.claude/BACKEND.md`. Database rules:
`.claude/SUPABASE.md`. **Update this file in
the same change as the work.**

## Status, 2026-10-01

- The TypeScript to Python port is complete. FastAPI is the only thing that touches the database.
- Tests: `pytest` runs 451 passed, 4 skipped (the four symmetric-token auth tests, which skip on a
  JWKS-configured project).
- Database: 32 migrations (000 to 010 and 018 to 038), 19 tables (10 `public`, 9 `admin`), 2 frameworks and 7 prompts seeded.
  `admin.exercises` holds the 30 library exercises from `content/exercises/` (as "mani-app" holds them on 2026-11-13;
  the other hosted project was not compared), with their audio in the
  private `exercises` bucket (`scripts/seed_exercises.py`). Two hosted projects held every migration of the time and
  the same data (2026-11-06): `heqenombgkihfeggrxqc` (muhammad's org, ca-central-1, the Hobby deployment's database)
  and `aipgficduzufstilndbw` "mani-app" (the Mani org, us-east-1, for the Vercel Pro deployment). Migration 037 has
  run only on this machine's databases (2026-11-13).
- Models: `openai/gpt-6-luna` for chat and for summaries (`mani/config.py`), routed only to OpenAI,
  the fastest endpoint first. It is a reasoning model: it takes no `temperature` on any provider and reads
  `reasoning_effort` instead, so `mani/llm/chain.py` sends the sampling parameters an ordinary
  chat model takes only to models that accept them. A prompt row names its own effort in
  `model_parameters.reasoning_effort` and `mani/config.py` holds the default for the calls that have
  no row of their own; every chat turn reads the effort of `voice`, on `medium` (in prod since 2026-10-29, confirmed by
  `docs/latency-report-2026-11-05.md`), and a body check-in turn its `body_reasoning_effort`, on `low` (2026-11-05;
  `mani_base` was on `medium` from 2026-10-22 until it was retired), while `summarization` and `memory_fold` are on `high`. Effort is billed: measured against Azure,
  `high` spent 26 reasoning tokens where `low` spent 0, about three times the cost of the same call. Every endpoint keeps `data_collection: deny`, so
  training use stays refused, and one company, OpenAI, processes the conversations.
- Every call to OpenRouter carries the same providers, data policy and reasoning effort, from
  `chain.request_body`. The voice translation in `mani/stt.py` calls the SDK directly and used to send
  none of them, so a transcript went to whichever provider OpenRouter chose; it now uses the same body.
  It is still not recorded in `admin.llm_calls`, which has no purpose for it.
- A reasoning model's output budget covers its thinking and its reply together. Every caller sizes
  `max_tokens` for the reply alone, so `chain.sampling` adds `REASONING_ALLOWANCE_TOKENS` (8,192) on top.
  Without it, at effort high, 4 of 61 chat calls ran out of tokens while thinking and the turn failed
  (2026-10-07). Measured at high: 12.6 s for an average turn, 41 s for the longest. Not measured at
  low: the target is a median of 4 s and a slowest of 10 s, and `scripts/scenario_check.py` now prints each
  turn's time, calls and tokens (`admin.llm_calls.reasoning_tokens`, migration 018) to check it.
- Every turn's prompt is prose read after `voice.md` (`conversation.md`, `framework.md` or `moments.md`). The YAML
  rules of ADR-012 (`mani_base.md`, `response_format.md`, the style files) were retired on 2026-10-27.
- Web and mobile do not call this API yet; they run on placeholder data.

## What the service does

- **Auth** (`mani/auth/`): HS256 or JWKS, audience checked, `alg: none` refused. Admin is
  `app_metadata.admin_role == 'admin'` and `user_metadata` cannot grant it.
- **Database** (`mani/db/`): `as_user()` opens a transaction as `mani_service` with the caller's claims set, so RLS
  applies to real traffic. `as_admin()` is the named exception. A turn's writes share one transaction, and no
  transaction is open while the model thinks (`chat/runner.py`).
- **A chat turn** (`mani/chat/orchestrator.py`), in order:
  1. Safety comes first. Every reply's first field judges from the whole conversation whether anyone is in danger
     now (`SafetyRead`); the thread holds it as clear, unsure or danger (`threads.safety`), a refusal never settles it,
     and the free phrase screen (`safety.py`) makes a turn unsure before the model is asked. While it is not clear the
     turn is the safety moment. A phrase never locks anything; danger that continues with nothing in place pauses the
     person's chat for `CRISIS_PAUSE_MINUTES` (see Decisions in force), and while a pause runs every chat route and the
     turn itself refuse with 423 `chat_paused`.
  2. Which framework fits, and whether one fits yet, is the model's call from the Framework Index. Code owns only when an offer may come (`context.may_check`; since the client meeting of 2026-11-03 the chat's reply that moves to the set is the offer itself, with no check before it, and `context.check_open` serves only checks stored before then) and the safety screen.
  3. `composer.py` builds the system prompt: `voice.md` and `conversation.md` for Mani's own conversation
     (`_converse`), `voice.md` and `framework.md` for a framework's stages, and `voice.md` and `moments.md` with
     the Framework Index for the turns in between (the answer to a check, the offer, the body check-in, a safety
     concern). `context.py` builds the `[ctx]` block for every turn but the chat's own: style, offer timing, the stage in progress, what is stored for each stage
     and what this reply's text is for. Nothing in code classifies what the person said: whether a reply is vague, a correction or
     a wish only to be listened to is the model's reading.
  4. One model call (`mani/llm/`, LangChain on OpenRouter) returns a structured reply: `reasoning`, the answers
     that decide the moment (`check_answer`, `offer_answer`, the stage fields), then `text`, then `picture`,
     `heading_toward`, `offer`; on the answer to a check, `heading_toward` and `offer` come before `text`.
     Mani's own conversation replies in `ConversationReply` instead: what the turn calls for, then the text, with the
     reading and the picture read by a second call after the reply is sent (`orchestrator.read_understanding`, see
     Decisions in force).
     The order is deliberate: with the reading of the person written first, the reply came out as a case note (2026-10-13). Its shape is picked from the database for the
     turn's moment (`context.moment`, `schema.reply_for`): the offer's slots only while an offer may be made,
     `offer_answer` only while one is open or was declined, `body` only on the body route.
  5. `walk.py` costs no call: inside a framework it merges the reply's `stage_updates` into the stage store,
     moves at most one stage on its `stage_answer`, and renders the stage reached (spec 0004).
     `reply_checks.py` counts what code cannot fix (an offer that is due and missing or could not be rendered, no question
     unless the draft chose a shape that asks nothing, the last reply's question asked again) in the logs and
     in `Turn.checks`.
  6. `repairs.py` corrects what remains, in code (script leakage, internal words), and renders the client's
     fixed text from the reply's fields: the offer, Tell me more, Keep chatting and the body route's branches.
     Every button is set by code.
  7. Crisis, a pause, the reply, the framework state, what Mani understands of them and the summary are written
     together.
- **Frameworks** (`content/frameworks/*.md`, seeded to `admin.frameworks`): ABCDE and Thought Reframe are seeded and
  offered (the client's ABCDE document of 2026-10-09; Thought Reframe moved out of `paused/` by muhammad, 2026-10-21). The other four are kept in `content/frameworks/paused/`; the seed
  sets their rows inactive (never deleted, since threads and exercises refer to them), and moving a file back up
  brings it back. ABCDE ends on E and then the shared body check-in below (muhammad, 2026-10-09: the check-in
  is asked). An offer comes only on a clear yes to Mani's check of its understanding, which may come from
  the person's second message, in every style (spec 0006). The shared body check-in comes from `content/prompts/somatic.md`
  and is the client's document "SOMATIC SECTION OF MANI" (2026-10-16), sent word for word in one voice (muhammad,
  2026-10-22). **The body check-in is the client's six steps, owned by code (`mani/chat/body.py`):** after the
  framework's last stage Mani asks whether they would like to check in with their body (Yes / Not right now, phase
  `somatic_ask`; muhammad, 2026-10-27, see Decisions in force), then Step 1 with Chest, Stomach, Head, Somewhere Else
  and No Tension (No Tension is the way out), one of the nine
  exercises sent whole with the check for change (Feel Better / Feel the Same / Feel Worse), the fixed reply, the
  overall question (Yes, It Helped / Somewhat / No, Not Really), and Keep Chatting, Go to Library and Finish for Now.
  The phases are `somatic_ask`, `somatic_body`,
  `somatic_practice`, `somatic_effect` and `somatic_closing`;
  the last is final, so the turn after it retires the run. Taps decide by their label; a typed answer is the `body`
  value the reply read, valid only at the step that accepts it, and `unclear` re-asks with the same buttons and never
  moves the route. Somewhere Else asks where (the model's words, with the six other places as buttons); a place with
  no exercise gets the closest one offered in the model's words, Yes or No thanks. No Tension skips the exercise and
  sends its own block, whose Somewhat line differs from Step 5's, as the document places them. Pain, trouble breathing
  or feeling faint ends the route with the client's line. The physical response (better, same, worse, no_tension) and
  the conversation effect (helped, somewhat, not_really) are separate columns on `thread_technique_state` (migration
  025), each written once per run, cleared when a new offer starts a run. Replaces the 2026-10-02 flow: Chat More, its
  three follow-up questions, the Library nudge and the automatic exercise pick (a second model call) are deleted
  (`tests/unit/test_removed_names.py`); `exercise` is gone from the turn response.
- **Memory**: per person, folded from earlier chats by `mani/memory.py`; idle threads fold through
  `memory.fold_idle`, run by `scripts/fold_idle_threads.py` or `GET /internal/cron/catch-up` behind `CRON_SECRET`.
- **Exercises**: catalog, completions and signed URLs (`mani/storage.py`). A completing framework picks one
  exercise from the whole active catalog with one bound tool call (`mani/llm/tools.py`): the framework's own
  exercises are listed first, and the pick sees the person's last three messages and the issue Mani
  understands (`threads.understanding`). `GET /v1/exercises` is the whole catalog, and responses never carry the storage path.
- **Admin**: prompt CRUD with versioning, exercise CRUD, crisis event review, a user's memory, and every
  person's conversations read-only (each full read logged in `admin.thread_reads`). An admin cannot send a chat
  message (`Participant` in `mani/auth/deps.py`). `scripts/grant_admin.py <email>` grants or `--revoke`s it.
- **Account deletion**: `DELETE /v1/account` removes the user and everything they own.
- **Scenario check**: `scripts/scenario_check.py` replays the client's test conversations (`scripts/scenarios.json`)
  through the real stack in every style, including the four scenarios of the client's styles document. It flags
  questions that ask for what they already said, internal words, and offer mistakes, and removes the users it created.

## The API

| Method | Path | |
|---|---|---|
| GET | `/health`, `/health/ready` | liveness, readiness |
| GET PUT | `/v1/profile` | onboarding answers, and `chat_paused_from` and `chat_paused_until` while a pause runs |
| GET POST | `/v1/threads` | list (only conversations they have written in), **start from the first message** (creates the thread with its greeting, the chosen style and the first turn) |
| GET | `/v1/threads/opening` | the greeting, the style options, each style's opener, `chat_paused_from` and `chat_paused_until`; writes nothing |
| GET | `/v1/threads/current` | the conversation to show on opening the app, or none; writes nothing |
| GET PATCH DELETE | `/v1/threads/{id}` | fetch, set `conversation_style`, soft delete |
| GET POST | `/v1/threads/{id}/messages` | history (paged), **send a turn** |
| POST | `/v1/threads/{id}/messages/{message_id}/follow-up` | the reading and summary a turn left, asked for once its reply is shown (`follow_up_pending`); a part that fails stays waiting (`pending`) |
| POST | `/v1/threads/memory-fold` | folds finished chats into memory, asked for when the app opens a new conversation; leaves out any chat written after the request arrived |
| GET | `/v1/exercises`, `/home`, `/{id}` | catalog with signed audio |
| GET POST | `/v1/exercises/completions` | a user's completions |
| PUT DELETE | `/v1/exercises/{id}/feedback` | the person's 👍/👎 on an exercise, with an optional reason; replaces any earlier one |
| GET | `/v1/crisis/resources` | three US reference numbers (911, 988, Crisis Text Line) and the Find A Helpline directory, each with its `kind` (`emergency`, `support`, `directory`), until the client supplies her list; the directory is listed for every country |
| DELETE | `/v1/account` | delete the account and its data |
| GET POST | `/v1/admin/prompts` | portal |
| GET PATCH | `/v1/admin/prompts/{id}` | patch snapshots the old version first |
| GET | `/v1/admin/prompts/{id}/versions` | history |
| POST | `/v1/admin/prompts/cache/invalidate` | publish now |
| GET POST, PATCH DELETE | `/v1/admin/exercises`, `/{id}` | catalog CRUD |
| GET | `/v1/admin/crisis-events` | review queue |
| GET | `/v1/admin/users/{id}/memory` | what is remembered about a person |
| GET | `/v1/admin/threads` | every person's conversations they have written in, newest activity first; `search` by email or user id |
| GET | `/v1/admin/exercise-feedback` | every person's library ratings, newest first; `search` by email or user id |
| GET | `/v1/admin/threads/{id}` | one conversation in full, oldest first; logs the read |
| GET | `/internal/cron/catch-up` | summaries behind, follow-ups the app never asked for, quiet chats folded into memory (`mani/catch_up.py`); bearer `CRON_SECRET`, no JWT |

## Decisions in force

- **Every chat reply ends on one question, in its own field, on a line of its own** (muhammad, 2026-11-10: "a
  question, always"). Because a reply that asked nothing ("We can stay with the shock for now", "Of course, you don't
  have to make sense of it all tonight") left a conversation with nowhere to go, and muhammad's chats stalled before a
  framework was ever offered; it replaces the 2026-11-05 decision that "a chat reply may support without asking"
  (manasa: "mainly driven by questions"), knowingly. `ConversationReply.forward` follows `text`; the text gives first
  (an acknowledgment, an observation, an insight: R78) and asks nothing itself. The field's pattern, a trailing
  question mark, goes to the provider and not to pydantic, which holds the reply to it as it is generated (checked
  2026-11-10) so no second call repairs a missing one, and a reply that still comes without one is counted
  (`no_forward`, "asks no question") and never padded by code. `orchestrator._with_forward` joins it after the text with
  a blank line: a deliberate exception to the 2026-10-26 "no line breaks added by code" rule, for this part only. A
  sentence of the text that is the same question (compared without case, spacing or punctuation) is dropped wherever it
  stands, so it is said once: the owner's chat (2026-11-13) got the question before the direction and again after it,
  because only a text ending on it gave it up (`test_the_closing_question_asked_earlier_in_the_text_is_said_once`). The
  reply that moves to the set of questions is joined the same way; the offer takes the question's place
  (`repairs.transition_offer` drops the last question) and, when no offer can be made, the reply still ends on one.
  Someone who wants to stop is asked whether they would like to leave it here for now. Traced: `no_forward`,
  `text_asks` (a question in the text too), `forward_asks_many`. A safety reply and a reply that stays on a stage end
  on one too (muhammad, 2026-11-11): `Reply.forward`, sent on those two shapes only, may be empty and is joined only
  when the text asks nothing, so a stage's own question, a stage just reached and the client's lines are untouched
  (`test_a_safety_reply_that_asks_nothing_ends_on_its_question_on_its_own_line`,
  `test_a_reply_that_stays_on_an_earlier_stage_and_asks_nothing_ends_on_its_question`). Offers, the answer to a check
  and the body check-in keep their own rules. The client has not been told.
  Tests: `test_every_chat_reply_ends_on_its_question_on_a_line_of_its_own` and its neighbours in `test_turn.py`.
- **What is explored stays explored, and a message's length decides nothing** (muhammad, 2026-11-10). Because the
  after-reply reading re-judged the list of explored areas every turn and dropped ones it had counted (8, 6, 8, 6, 7, 9
  in one chat), so "attempts or pattern" was still to explore on most turns and a chat of 21 turns never reached a set
  of questions; and three messages of three words or fewer pressed toward the framework whatever they meant ("he
  lied", "she left", "i quit"). `converse._explored_so_far` keeps areas until a new issue; `converse.toward` presses on
  `quiet` (the reading's own judgment that two messages added nothing) only once a situation is known, and the
  word-count rule, `SHORT_WORDS` and `SHORT_IN_A_ROW` are gone. The chat's note names what is still unexplored while
  they are still telling it. With several concerns and no core, Mani weighs them itself and says which seems the main
  one as a guess they can correct; with vague answers it offers two or three possibilities (`conversation.md`).
- **A reading that never lands is visible** (2026-11-10). Because a timed-out reading leaves no `llm_calls` row and a
  new turn replaces one nobody asked for. The next turn's trace carries `reading_before`: `dropped`, `failed:timeout`,
  `failed:error` or `running` (`orchestrator._reading_before`). Counted, not recovered.
- **The ledger of a framework is shown on every turn it is running, also while a concern is open** (muhammad,
  2026-11-10). Because the ledger was built from the stage walk, which a safety turn skips on purpose
  (`orchestrator._ledger_as_stored`).
- **A scheduled catch-up finishes what the app never asked for** (muhammad, 2026-11-06). Because on Vercel the app
  triggers the work after a reply and a new chat, so a closed tab lost a reading and someone who never taps New chat
  was never remembered. `mani/catch_up.py`, every 5 minutes from `backend/vercel.json` (Vercel Pro): summaries behind,
  follow-ups waiting on a reply quiet for `QUIET_AFTER` (5 min) and given up after `GIVE_UP_AFTER` (1 h), and quiet
  chats folded (`memory.fold_idle`, longest-quiet people first, the limit counting paid folds), each as its person
  (`Claims.acting_as`). Each job starts at most `catch_up.LIMIT` (10) items a run and stops at `RUN_SECONDS` (240),
  inside the function's 300 s. Nothing failing is retried forever: a follow-up for `GIVE_UP_AFTER` (1 h), a summary
  while its thread had a message in `summarize.CATCH_UP_FOR` (1 day), a fold for `memory.FOLD_RETRY_FOR` (1 day) after
  `IDLE_AFTER`; past that a summary waits for the thread's next turn and a fold for the person's next New chat. Work
  a request has claimed is passed over. Tests: `test_follow_up.py`, `test_memory.py`, `test_queries.py`
  (`due_for_summary`), `test_catch_up.py`, `test_cron.py`.
- **The hosted chat-tester runs as it does locally, Forgot password included, for testing only** (muhammad,
  2026-11-06). Because testers need it now and the safe flow can wait. It is a public Streamlit Community Cloud app
  from the public repo, holding mani-app's Supabase secret key, so anyone with the link can reset any non-admin
  account's password and read that person's conversations, and create accounts that spend model calls. Accepted for
  test accounts only; before any real person signs up, remove the Forgot password tab and the secret key from the
  hosted copy (sign-up works with the publishable key alone, since mani-app auto-confirms) and make the app private.
- **`content/exercises/exercises.json` is production's library, its 30 rows; the audio stays off GitHub, and
  `seed_exercises.py` checks categories against its own `ExerciseCategory`, not `LibrarySection`** (muhammad,
  2026-11-13). Because a local setup could not play the library, the recordings are client content that should not
  be in a public repo (and Vercel builds from the repo root, where `backend/.vercelignore` does not apply, so committed
  audio rode in every function bundle), and three of production's categories (LoveRelationships, ManagingWorry,
  Sleep) are not places a chat button opens; adding them to `LibrarySection` would change the reply schema the model
  reads. The MP3s are gitignored: local copies at 64 kbps mono sit in `content/exercises/`, copied from production's
  bucket, and the seed stops and names any that are missing. The 12 older recordings the repo held were replaced by
  production's re-recordings of 2026-11-09 (same ids, new files, lengths and three titles) and removed from git; they
  remain in `main`'s history. The seed uploads with `x-upsert`, so running it against production would replace
  production's 192 kbps files with the 64 kbps copies; production was only read from.
  `tests/unit/test_seed_exercises.py`.
- **A person rates a library exercise 👍 or 👎 with an optional reason, one rating per exercise that a new tap
  replaces, and admins review every rating by email** (muhammad, 2026-11-14). Because muhammad wants the library's
  feedback recorded as the replies' is (`feat/feedback-per-response`, not merged): the same `FeedbackIn`/`FeedbackOut`
  shapes, a tap that saves at once and a reason that follows, and the reply's row as in his reference (thumbs, a
  one-line "[Optional] Please provide an explanation" field, Submit). `public.exercise_feedback` (migration 038), RLS
  so a person reads only their own, writes only through the backend (`mani_service`), and only on an active exercise.
  `exercise_completions.helpful` is a different thing (a row per completion) and was not reused. In the tester the row
  is a fragment, so a tap never reruns the page and a playing exercise keeps playing; the admin screen's Library
  feedback view lists who rated what. `tests/integration/test_exercise_feedback.py`, `tests/unit/test_feedback_input.py`,
  `chat-tester/test_library_feedback.py`.
- **In the chat-tester's library, every exercise plays in one player of our own, run by the browser: seek bar, 10 s
  back and forward, play, mute and time. Only stories (`type` "Story") also get a 0.5x, 1x, 1.5x or 2x speed menu**
  (muhammad, 2026-11-13). Because `st.audio` has no speed setting in Streamlit 1.64, a speed item in the
  browser's own player menu is unconfirmed on any browser, muhammad asked for the look of his reference player, and
  he wants the speed feature on stories only; the speed menu was chosen over four buttons per exercise. No backend or
  database change: the signed link plays straight from Storage, which answered a range request with 206 (local
  Storage only). Exercises still play only in the library, never in the chat. `chat-tester/audio_player.py` (with
  its `.css` and `.js`), `library.py` (`STORY`), `test_audio_player.py`, `test_library.py`.
- **The migrations alone make a project safe; nothing depends on a hand-run revoke** (2026-11-06). Because a new
  Supabase project grants anon, authenticated and service_role everything on each table, sequence and function
  `postgres` creates in `public`, and the hosted project was safe only because someone had removed those defaults by
  hand: built from the migrations, "mani-app" let any signed-in person call `create_message_pair` and forge Mani's
  reply. `000_supabase_defaults_off.sql` turns the defaults off before 001; `034_backend_only_state.sql` pins the
  definer functions to `mani_service`, hides `threads.understanding`, `rewind_snapshot`, `pending_follow_up` (the
  reading's whole call, system prompt included), `vague_streak`, `check_at_message_count` and `memory_folded_at` from
  `authenticated` (they were readable through the Data API with the person's own token), and moves `admin` schema
  usage with `admin.exercises` and `admin.frameworks` from `authenticated` to `mani_service`. `035` takes `public`
  away from PUBLIC and names each role that uses it, `supabase_auth_admin` included: the hosted project had lost
  PUBLIC's usage by hand, so deleting an account failed in GoTrue's cascade. `test_harness.sql` now
  grants the defaults, so `scripts/test_db.sh` proves the migrations undo them. Tests: `tests/sql/test_grants.sql`.
- **No conversation content in an error report or a stored error** (2026-11-06). Because the request body is their
  message, the failing frames' locals hold transcripts, and a provider's error body can quote their words. Sentry runs
  with `send_default_pii=False`, `include_local_variables=False`, `max_request_body_size="never"` (main.py); a
  provider HTTP error is stored and logged as its type and status only (`client._QUOTES_THEIR_WORDS`). Tests:
  `test_app.py::test_an_error_report_carries_no_request_body_and_no_local_variables`,
  `test_client.py::test_a_provider_error_is_stored_without_the_body_that_can_quote_their_message`.

- **One home per rule, and no reply shape is a formula** (muhammad, 2026-11-06, P2). `voice.md`'s "Mirror, then
  acknowledge" (mirror, acknowledge, question, and "Mirror in most replies") is "Showing you understand": only when it
  helps, some replies are an acknowledgment alone, some start with an observation or a question; each style's example
  is one natural reply, and the style table compares understanding and warmth, not mirror and acknowledge.
  `framework.md` no longer acknowledges "before the next question" by habit. Merged to one home: questions and
  asking for what is known (`voice.md`), the reply kinds (`conversation.md` Choosing the reply; "Choosing the next
  question" is gone), examples about someone else (`voice.md`), safety (`moments.md` and the [ctx] lines; one line in
  `conversation.md`). The five "conversational moves" are the areas a question can open, shortened. Frustration (one
  rule, `voice.md`): stop the pattern, name what went wrong, move differently; the framework only when the note says
  enough is understood, never as a way out of frustration before that (muhammad). Before the framework, help is one
  small idea, then working it through together (the client, 2026-10-29; the `practical` kind follows it). Lolly's
  "steps 4 and 5 before the offer" moved into code: attempts or pattern is the fourth group in
  `converse.EXPLORED_BEFORE_MOVING`. The six unit tests left failing by earlier rewrites hold the same decisions against
  the current wording (notes in each). The four chat prompts went from 80,665 to about 76,000 characters.

- **Every question earns its place; Mani reasons before each reply and gives several aha moments** (muhammad,
  2026-11-06, after manasa's tests, superseding the one-extra-turn cap of the same day: "the goal is not to reduce the
  number of questions, it is to make every question earn its place"). Mani reasons in its own hidden reasoning before
  each reply, chat and stages alike, on what it knows, understands, can infer and does not know, what would help most
  and where the turn takes them (`conversation.md` Before every reply; `framework.md` How a turn goes), at the voice
  row's medium effort. Every reply reports `progress` (discover, deepen, belief, connect, need, pattern, insight,
  toward_goal, and what it adds); the record keeps the last four (`context.PROGRESS`), shown as recent_progress, and a
  reply that adds nothing is counted ("adds nothing new"). The after-reply reading also returns `exploration`: the
  areas explored (emotion, belief, behaviour, external, outcome, need, attempts, pattern, relationships, meaning), up to
  three worth exploring next with why, and up to three connections Mani can infer and has not said; it runs on stage
  turns too (`ReadAfter.picture=False`: there it brings only the map, never the picture, core or heart). Each stage
  lists the parts it can open (`explore` in `abcde.md` and `thought_reframe.md`); the reply reports `explored_now`, kept
  on the stage as `covered` and shown as stage_explored, and a stage stays while a part not yet opened would help, with
  no cap (`walk.EXPLORE_TURNS` is gone; two turns with nothing new still offer to step out). Insights are tracked across
  the chat and the questions (`context.INSIGHTS`), several per conversation, each new; never on the first reply (was
  the first two: Lolly's point kept without a count). The chat's reply kinds are chosen, not a formula: open_ask,
  window, insight, reflect, acknowledge, practical; no reply has to start with a mirror or end with a question. Moving
  to a set of questions keeps the five-message floor and the confirmed core, and now also needs the emotion, the belief
  or meaning, and the behaviour, need or outcome explored, from the map (`converse.still_to_explore`; with no map yet
  the heart decides alone). Outcome, what they want to happen, joined that group 2026-11-11: the father chat's "I want
  him to see what I did for them" was read as outcome, in no group, and held the offer for ten turns
  (`test_what_they_want_to_happen_counts_with_what_it_does_to_them_or_what_they_need`).
- **Plan Next Step: help preparing what they chose, when something practical is ahead** (muhammad, 2026-11-06, after
  manasa's tests: nothing helped her work out how to raise it with her boss or her partner). The picture keeps what
  they asked for help with (`asked_for`). The reply that closes the questions reports `follow_through`: conversation,
  action, decision or none. Anything but none puts Plan Next Step first among the closing choices (`somatic.md`
  `plan_buttons`, ours, not the client's). Choosing it, tapped or typed (`body: plan`), stores `preparing` on the
  record, and the chat after it helps them prepare the way a therapist would for its kind (`context` meanings
  `follow_through`: for a conversation, what they want understood, an opening in their words, what if the other person
  gets defensive, and an offer to practise it), with no check or offer meanwhile, until the reply sets `prepared`.

- **Safety is the model's judgment of whether anyone is in danger now, held by the conversation; a phrase never locks,
  and danger that continues with nothing in place pauses the chat (a symptom in the body only on a refusal of the help).** Because a concern must outlive the reply that
  raised it and must not give way on a refusal (manasa's safety test, 2026-11-06), and because sign lists with a
  rule per kind of danger held concerns open against what the
  model understood: "I mean my workplace", "my friend is with me and stops me", a symptom that has passed (muhammad's
  and Lolly's chats, 2026-11-10). Spec: `docs/specs/0007-safety-follows-what-they-said/`.
  - Every reply's first field, `SafetyRead`, judges from the whole conversation as it stands now whether anyone is in
    danger: `danger` none, unsure or now; `about` themselves, someone_else, from_someone or body; a line of why, never
    traced and stored only as the reason of a pause it starts (`chat_pauses.reason`); `declined` when they refuse the
    help, say again they will do it, or push the question away, never for a doubt, a question or a step under way; for a
    symptom in the body only an outright refusal of the help is `declined`, pushing back or doubting never is (2026-11-13,
    which narrows the 2026-11-11 "never a symptom"); and `help_in_place` (2026-11-13): help called or on its way, someone with them, the means away from
    them, or moved away from the danger, the same for every kind of danger.
  - `threads.safety` is clear, unsure or danger (migration 036). Code applies the judgment with two rules of its own
    (`safety.after`, `safety.screened`): a refusal never settles a concern, and a phrase the free screen catches makes
    an untroubled turn unsure before the model is asked, never more.
  - While it is not clear the turn is the safety moment: one instruction per state in [ctx] (`context._MEANING`,
    `safety`), which names no kind of danger. Unsure is main's listening more than asking, with one open question about
    what they meant and no direction to call anyone while Mani does not know. The direction (`context.DANGER_DIRECTION`:
    what would make them or the other person safe now, said once, never a step already taken) goes with every turn
    that can judge danger: the clear line, the unsure instruction, the chat's note and another conversation's return
    check, so the first reply that judges danger carries it (the audit, 2026-11-13: it was chosen from the state before
    the model judged and never reached the model;
    `test_a_clear_turn_is_told_to_give_the_direction_if_it_judges_danger_now` and
    `test_an_unsure_turn_is_told_to_give_the_direction_if_it_judges_danger_now` in `test_chat_context.py`,
    `test_a_chat_turn_is_told_to_give_the_direction_if_it_judges_danger_now` in `test_converse.py`). It settles
    (muhammad, 2026-11-11) on a step they took (the means handed over, someone with them, help called), or once Mani
    has asked and they go on about their situation with nothing pointing
    at danger, also after plain words (asking twice made Mani ask in every reply, live). Brushing the question off is
    `declined`, held like a refusal. Danger is now only with a plan, the means or now; "I want to kill myself" alone is
    unsure, answered with warmth and one question. A symptom in the body is danger only when they said it is happening
    now: the model reports `symptom_now` (yes, no, unsaid) and code holds anything else at unsure (`safety.danger_of`;
    Lolly's chest chat, replayed 2026-11-11, read "a tightening in my chest" as now and gave the emergency number four
    times). Once settled, only their newest message reopens it, said on every kind of turn (`context.SETTLED_LINE`); for a
    symptom in the body, code holds a reading that is not `symptom_now: yes` at none instead of unsure once settled
    (`safety.danger_of(reopening=...)`; the stroke chat, 2026-11-11, flipped back to danger on "I am afraid of losing
    him" from the father's earlier symptoms; 4 of 4 replays stable, but one wife-chat replay read "either or both" as
    the symptom happening: the model's yes is not checkable in code). The danger direction holds only what keeps them
    safe, in one sentence of the text, never what to say to anyone (emergency services included) or how to feel, with one
    question in the whole reply (muhammad, 2026-11-13: the owner's chat got "Tell them you may hurt your boss"), and the one check on it is only on that step
    (muhammad's chest chat: "tell your wife you're worried" was chased). The chat never invents an exercise, activity
    or distraction of its own: exercises are the library's (muhammad: "library only"; his chat got "a strange animal
    fact" and "pick one thing you can see" from Mani's own plan and need).
    Danger says it once: from the second danger turn [ctx] gives `danger_said` (code knows the previous reply was a
    danger reply), which never repeats the direction and answers what they said first, a doubt like "could it be
    stress?" included (muhammad, 2026-11-11: understand and discuss first). That reply goes out only when the turn does
    not pause (below); a doubt like "could it be stress?" never pauses. A symptom they push back about is never
    `declined`; for a symptom Mani asks once whether it is now, says once what to do if it is, then follows them.
    No framework, offer or library, never the message limits, and `crisis.CRISIS_REPLY` if the model fails. A
    framework's stage waits (`paused_stage`) and resumes where it stood.
  - When a concern that was open settles, `understanding.safety_settled` is kept and the chat note says so
    (`converse.SETTLED_LINE`), so Mani does not raise it again from the history it reads every turn.
  - The first turn judged danger now, or opened by an explicit phrase, is recorded in `admin.crisis_events` with whose
    danger it is, never their words. `threads.crisis_at` (migration 037) keeps when it was last flagged, and
    `recent_crisis` counts its 30 days from it (`test_recent_crisis_counts_from_the_crisis_not_the_last_message`). An
    edit restores the state (`rewind`).
  - **When danger continues with nothing in place after the direction, the chat pauses for `CRISIS_PAUSE_MINUTES`
    (default 15); a refusal is required only for a symptom in the body; nobody is signed out, every conversation is
    closed, the Library stays open, and the backend is the whole lock** (muhammad, 2026-11-13, and 2026-11-14 for the
    refusal; this replaces "nothing locks" of 2026-11-06 and "help refused is the only block" of 2026-11-11). Because
    once a crisis is certain Mani must stop rather than go round a loop of "please get help", and the production chat of
    2026-11-14 never paused in 11 turns: "i want to kill myself", about to act right now, nobody with them, nobody
    called, every question answered honestly and so never `declined` (2026-11-14).
    The rule is `pause.pauses_now`: the state before the turn was danger (so Mani's last reply already gave the
    direction), the state after is danger, and `help_in_place` is false; or it is the answer to a return check that
    leaves such danger. For danger to themselves, to someone else or from someone nothing more is needed. A read whose
    danger has no kind (no `about` in the read and none stored) needs `declined` too, so it cannot pause a body chat by
    accident. Accepted with it: a `help_in_place` misread can now pause someone who has help (2026-11-14);
    `test_danger_that_goes_on_after_the_direction_with_no_one_there_pauses_without_a_refusal`,
    `test_danger_that_goes_on_with_someone_there_never_pauses`.
    **A danger about the body pauses only on an outright refusal of the help for a symptom happening now**: the turn's
    own read is `declined` with `danger` now and `symptom_now` yes ("I'm not calling an ambulance"); a read with only
    `declined`, a doubt or pushback never pauses it (the controller's ruling, 2026-11-13). Because a doubt paused 5 of 6
    body chats live, and Lolly's 2026-11-11 replay read body pushback as `declined` with no danger value, yet someone who
    refuses the ambulance for chest pain happening now needs the pause too (2026-11-13). Whose danger it is comes from
    the read, else whose the conversation last reached (`understanding.danger_about`);
    `test_refusing_the_ambulance_for_a_symptom_happening_now_pauses_with_the_body_text`,
    `test_pushback_about_a_symptom_read_as_declined_never_pauses`. The first danger message, an unsure concern, a
    doubt or a question about a symptom in the body, a reply that reads no safety (no danger value and no `declined`, `orchestrator._judgment`),
    help on its way and the return check itself never do. On the pausing turn a `chat_pauses` row (migration 037: thread,
    `started_at`, `ends_at`, `reason` from the judgment's why, `checked_at`) is written in the turn's transaction, the reply is `crisis.pause_reply(about)` (whom Mani worries for and the
    help that fits whose danger it is: "your safety", 911 and 988 for themselves or an unknown kind; "everyone's
    safety" and 911 for someone else; "your safety" and 911 from someone; "your health" and 911 for the body; Crisis Text
    Line is named neither here nor on the pop-up, and stays in `RESOURCES` for the API) and nothing about another conversation, the response carries `paused_from` and `paused_until`, and no follow-up is asked for. One gate,
    `auth/deps.require_chat_open` (`ChatOpen`), answers 423 `chat_paused` with `error.details.paused_from` and `paused_until` on
    `POST /v1/threads`, send, edit and follow-up, and the turn checks again under the message lock before its
    duplicate lookup, so a retry or another tab cannot slip past. The profile and the opening carry
    `chat_paused_from` and `chat_paused_until`; reading conversations, the crisis resources and the Library stay open. A pause's reason is
    loaded only by turns of the conversation it began in (`threads.load_turn_context`), never by another
    conversation, the memory fold or the profile, and the person's own role has no SELECT on it (the Data API hands
    out every other column of their pause). An edit never undoes a pause.
    **Every conversation asks after a pause, until they say they are all right** (muhammad, 2026-11-13; this reverses
    the ruling of the same day that a conversation created before the pause asks nothing). Because a person who comes
    back and chats in another conversation, new or older, must not bypass the check (2026-11-13).
    **A pause owes the check only while it ended within `RECENT_CRISIS_DAYS` (30)**, the window `recent_crisis` uses
    (the controller's ruling, 2026-11-13). Because without a bound every old unchecked pause, muhammad's local ones
    included, would make every conversation ask, however long ago (2026-11-13);
    `test_a_pause_owes_the_check_only_within_the_recent_crisis_window`.
    The return check: the first message after a pause, in any conversation, is a safety turn that never pauses. It is
    for the person's latest pause that has run out (`threads.load_turn_context` loads it and the conversation's own).
    A conversation with a pause of its own it has not asked about asks whether they are all right now and says that
    pause's reason (`[ctx]` `safety: returning`); every other conversation asks with no details (`returning_new`,
    trace `other_thread`) until the pause is checked. Each conversation asks once per pause (`understanding.return_check`).
    A settled answer (a danger value judged none) clears that conversation and marks the pause checked, after which the
    other conversations stop asking (a paused one still asks); danger with nothing in place pauses again, as above;
    an unsure answer is not asked again. Only the fact that a pause ran crosses conversations, never its reason or words. The chat-tester shows
    a centred "Let's make sure everyone is safe" pop-up drawn from the resources by `kind` (call and text 988, emergency
    911, the helpline directory) with a countdown that ticks every second and a bar of how much of the pause has run
    (from `paused_from` to `paused_until`); at 0:00 the page runs again and the chat opens, and its close opens the
    Library (`chat-tester/crisis_pause.py`). Not measured live yet.
    `config.crisis_pause_minutes`; `chat/pause.py`, `db/pauses.py`, `routers/threads.py`, `auth/deps.py`;
    `tests/unit/test_pause.py`; in `test_turn.py` `test_danger_that_continues_with_nothing_in_place_pauses_the_chat`,
    `test_danger_with_help_on_its_way_never_pauses`, `test_a_push_away_on_a_danger_thread_with_no_help_in_place_pauses_the_chat`,
    `test_a_turn_refuses_while_paused_even_past_the_route`, `test_the_first_message_back_asks_and_never_pauses`,
    `test_a_new_conversation_after_a_pause_asks_without_details`, `test_a_second_pause_asks_again`,
    `test_a_later_pause_in_another_conversation_never_hides_the_paused_ones_question`,
    `test_help_being_called_never_pauses_even_when_the_read_misses_it`,
    `test_saying_again_they_will_do_it_after_the_direction_pauses_the_chat`,
    `test_danger_in_the_answer_with_nothing_in_place_pauses_without_a_refusal`, `test_an_older_conversation_asks_after_a_pause_without_details`,
    `test_a_conversation_that_answered_its_own_pause_asks_again_after_a_later_one_elsewhere`,
    `test_pushback_about_a_symptom_read_as_declined_never_pauses`; in `test_threads_api.py`
    `test_every_chat_route_refuses_while_paused`, `test_the_library_and_profile_stay_open_while_paused`.
  - After a framework's last stage, a conversation in which a turn reached danger asks about safety once, as a reply
    of its own (`crisis.END_CHECK`), before the closing choices; their answer is a safety turn, and the reply that
    settles it carries the close and the choices (muhammad, 2026-11-11; `understanding.safety_end_check`;
    `test_after_the_last_stage_a_chat_that_held_a_concern_asks_about_safety_before_the_closing_choices`). It keys on
    `understanding.danger_reached`, set when a turn ends in danger, not on the crisis flag, which a phrase judged only
    unsure also sets (the audit, 2026-11-13; `test_the_end_check_comes_only_after_danger`). Conversations that reached
    danger before this code ran hold no `danger_reached` and get no end check (no backfill). A false alarm that never
    reached danger ends as usual; pushing the question away holds the close, like any refusal.
  - Pain in the body is asked about first, whether it is happening now, in `voice.md`.
  - Still the client's: the approved safety wording and resources (`crisis.RESOURCES` holds three US reference
    numbers and the Find A Helpline directory until then, and `pause_reply` names only numbers from it), and whether
    anything alerts a person.
  - Tests: `test_safety.py`, `test_pause.py`, the safety blocks in `test_chat_context.py`, and the safety conversations
    in `test_turn.py` (manasa's test, the roof chat, harm to someone else handled, the chest chats, a strong first
    message explained, a concern inside the questions, the pause and the return check). Scenario groups `reflective_tests_2026_11_06`,
    `chest_tightness_2026_11_10` and `cases_2026_11_10`.

- **The body check-in is paused: chat, then the framework, then the closing choices** (muhammad, 2026-11-05: "chat ->
  framework (not somatic)", and at the end Keep Chatting, Go to Library and Finish for Now as they come today). `paused`
  in `content/prompts/somatic.md` leaves `somatic_ask` to `somatic_effect` out of every framework's phases
  (`seed.somatic_phases`); their scripts stay seeded. The last stage moves straight to `somatic_closing`: Mani's close,
  without its question or any body offer (`body.close`), and the three buttons; the next turn answers them as it did
  after the check-in. `walk.next_line` tells the reply the closing choices follow; `voice.md` names two parts, and the
  ABCDE and Thought Reframe files name the closing instead of the check-in. No "did our conversation help" question
  (muhammad: straight to the three buttons). To bring it back: empty `paused`, restore those three prompt lines, and
  reseed. The body route's tests run with it unpaused (`body_check_in` fixture).

- **A turn reads, thinks, then writes: no database connection is held while the model thinks** (muhammad,
  2026-11-05). Because a turn held its transaction across the model call (6 to 30 s) and `client._record` took a
  second connection inside it, so ten turns in flight on one instance emptied its pool of 10, and with no acquire
  timeout the instance hung. `chat/runner.py` runs `orchestrator.send` twice: the read, in a transaction that rolls
  back, ends where the turn asks the model (`runner.Model` records the request and the thread's version, its message
  count and newest message id); the model is called holding nothing; the write runs the same steps in a fresh
  transaction under `_lock_thread` and answers them with that reply. A turn that never asks the model (a style
  button, a duplicate, their own message sent back) commits in the read, and one refused by a pause writes nothing.
  At the write, a message id
  already stored returns that turn; a thread whose version moved, or a reply asked for in another shape, is refused as
  `CONFLICT` 409, retryable, "Mani is still answering your last message. Please try again." The write rebuilds from the
  thread as it is then, so a reading that landed during the call is merged, never written over. The edit route takes
  the turn back in both passes (`runner.edit`), so a failed edit leaves the original. A retry with the same
  `client_message_id` waits in process for the first (`runner._one_at_a_time`) and pays nothing; one that reaches
  another instance pays once more and still stores one turn. The pre-model reads run twice (a few queries, about
  150 ms cross-region). `tests/integration/test_read_think_write.py`; `test_a_second_message_sent_while_the_first_waits_
  on_the_model_is_refused_and_stores_one_turn` in `test_turn.py`; [[read-think-write-2026-11-05]].
  The rule holds everywhere and is enforced (muhammad, after the 500-person load test, 2026-11-05): a task holding a
  pool connection may not take a second one (`pool._acquire`), call the model (`client.complete`) or read the prompt
  cache (`cache.load`, which reloads on its own connection); each raises `RuntimeError`, so a test finds it. Because the
  turn's read still called `cache.load()`, which on a stale cache took a second connection under a process-wide lock:
  at 500 people every connection was held by a read waiting on it, and 3,694 of 3,708 sends failed `busy`. The runner
  reads the prompts first and passes them in (`orchestrator.send(config=...)`). Summaries (`summarize.update`) and the
  memory fold (`memory.fold_one`) read, call the model, then write only onto what they read; the fold no longer claims
  its thread ahead (`memory_db.next_to_fold`, `mark_folded_through(was=...)`), so a fold that fails or dies leaves the
  thread waiting. In one process a second summary or fold waits for the first (`mani/one_at_a_time.py`).
- **The backend reaches Postgres through Supabase's transaction pooler (port 6543), with small pools** (muhammad,
  2026-11-05). Because each instance opened its own pool against the session pooler, so connections multiplied with
  instances; the transaction pooler shares backends across every instance. `mani/db/pool.py`: `statement_cache_size=0`,
  every statement inside a transaction (the jsonb codecs' type lookup and the readiness ping included), asyncpg's
  session reset replaced by a rollback of a transaction left open, and a 10 s per-statement `command_timeout` now that
  no transaction spans a model call. Nothing needs a session: no LISTEN, no session-level SET, no session advisory lock
  (`set local`, `set_config(..., true)` and `pg_advisory_xact_lock` are all transaction-scoped). Settings
  `DB_POOL_MIN_SIZE` 0, `DB_POOL_MAX_SIZE` 5, `DB_ACQUIRE_TIMEOUT_SECONDS` 5: an empty pool answers `BUSY` 503,
  retryable, "Mani is busy right now", never a hang. The whole integration suite passes through local Supavisor in
  transaction mode. `test_an_empty_pool_refuses_quickly_as_busy_instead_of_hanging`.
- **An instance has at most 100 model calls in flight, and a person at most 10 paid replies a minute** (muhammad,
  2026-11-05). Because nothing bounded either: a burst queued behind the provider until every turn timed out, and one
  client could send as fast as it liked. `client.complete` takes one of `MODEL_CALLS_IN_FLIGHT` slots (chat and
  background calls alike) or, after `MODEL_SLOT_WAIT_SECONDS` 2, refuses with `RATE_LIMITED` 429, retryable.
  `MINUTE_MESSAGE_LIMIT` 10 is counted from the messages they sent, beside `DAILY_MESSAGE_LIMIT`, after the safety
  screen, so a crisis is always answered. `test_a_call_that_finds_every_slot_taken_is_refused_quickly_as_busy`,
  `test_past_the_minute_limit_a_turn_is_refused_and_a_crisis_still_answered`.
- **Every wait on a turn adds up under 90 s** (muhammad, 2026-11-05). Because the chat-tester gives up at 90 s and a
  person sooner; Vercel Hobby allows 300 s. Worst case, each wait at its limit: JWKS fetch on a key-cache miss 5
  (`JWKS_TIMEOUT_SECONDS`; PyJWT's default was 30), pool acquire for the read 5, the read's statements about 0.5, a
  model slot 2, the model 65 (`CHAT_BUDGET_SECONDS`, the first attempt's cost row inside it), the last cost row's
  acquire 5, the write's acquire 5 and statements about 0.5: about 88 s. A statement is capped at 10 s, so a database
  slow on every statement could still pass 90. The JWKS fetch is blocking, and stays off the event loop because
  `auth/deps.current_user` is a plain `def` dependency, which FastAPI runs in its threadpool.
- **Only the backend creates a thread or records an offered framework** (migration 031, 2026-11-05). Because with
  INSERT on `threads` a user's own token, through PostgREST, could create a row with any `understanding`,
  `rewind_snapshot`, `check_at_message_count`, `memory_folded_at` or `message_count`, which the backend reads back as
  its own state. `authenticated` loses INSERT and DELETE on `threads` and INSERT on `thread_techniques_offered` and
  `thread_response_styles`; `mani_service` is granted the INSERTs it makes. No frontend writes these tables
  (checked 2026-11-05). `tests/sql/test_grants.sql`, `tests/sql/test_rls.sql`. Hosted needs `supabase db push`.
- **A conversation exists only once the person sends it their first message; opening the app, New conversation and a
  style tap write nothing** (muhammad, 2026-11-13).
  Because a page load and a New conversation click each wrote a thread and its greeting before the person said
  anything, and a style tap alone made a thread count as written in (the reuse rule, a paid memory fold, the rate
  limit) (2026-11-13).
  `GET /v1/threads/opening` returns the greeting, the style options, each style's opener, `chat_paused_from` and
  `chat_paused_until`.
  `POST /v1/threads` takes the first message (`content`, `client_message_id`, `style`) and writes the thread, the
  greeting, the tap and its opener when a style was chosen, then runs the message as a turn (`runner.start`): the
  rows a tapped style and a sent message write, so every message count holds. A retry with the same `client_message_id` gets the same
  conversation; a first turn that fails soft-deletes the one it created. `GET /v1/threads/current` returns the
  conversation last written in, or none. The lists, `most_recent` and the admin list show only conversations with a
  message the person wrote (`threads.WRITTEN_IN`; a style tap does not count), so greeting-only threads already stored
  are hidden, not deleted. `threads.create` always inserts a new conversation. The greeting says "good to see you again" only
  when an earlier conversation was written in (`orchestrator.has_written_in_earlier_thread`). `POST
  /v1/threads/memory-fold` takes no thread and folds only conversations last written before the request arrived.
  `tests/integration/test_threads_api.py`: `test_opening_writes_nothing`,
  `test_the_first_message_creates_the_thread_with_its_opening`, `test_a_retried_first_message_returns_the_same_thread`,
  `test_a_failed_first_turn_leaves_no_thread_in_view`, `test_a_chat_begun_while_the_memory_fold_runs_is_not_folded_by_it`.

- **Every call that has a thread sends `session_id` and `prompt_cache_key`, both `<thread_id>:<purpose>`.** Because
  OpenRouter recorded `session_id` null on every call of 2026-11-01 to 05 and turn 2 of a thread was cached in 1 of 8
  threads, while turn 3 always cached turn 1's whole input; without a key OpenRouter pins a conversation only after a
  cache hit, and OpenAI may send turn 2 to a machine without turn 1's prefix (`docs/latency-report-2026-11-05.md`,
  section 6). `session_id` is OpenRouter's sticky routing key (the endpoint that served stays pinned until 10 minutes
  pass with no call); `prompt_cache_key` is OpenAI's, which OpenRouter's docs (2026-11-05) describe only as the
  sticky key used without a `session_id`, not as passed on to OpenAI. Per purpose, not per thread (muhammad,
  2026-11-05): chat may use the priority endpoint and the other calls may not, so one shared key would re-pin the
  conversation after every call, and their prompts share no cached prefix (each starts from its own reply schema).
  `chain.build` binds them to the call (`chain.sticky`), merged into the model's `extra_body`, never into the cached
  model's key, so there is still one model per configuration. Evidence after deploy: `session_id` set on
  `/api/v1/generation`, and turn 2's cache ratio. `test_a_call_with_a_thread_carries_its_sticky_keys_beside_the_
  provider_reasoning_and_usage`, `test_a_call_with_no_thread_sends_no_sticky_keys` in `tests/unit/test_client.py`.
- **A body check-in turn thinks at `low`; every other chat turn at `medium`.** Because thinking before the first
  token is 75% of a chat call's wait (p50 6.0 s of 9.3 s) and latency follows output tokens almost exactly (r = 0.94),
  while the body check-in's steps are the client's fixed script (muhammad, 2026-11-05;
  `docs/latency-report-2026-11-05.md`, sections 1 and 7). The `voice` row carries it as
  `model_parameters.body_reasoning_effort` beside `reasoning_effort` (`content/prompts/voice.md`, seed after editing),
  and `composer.model_settings` reads it only when the moment is `Moment.BODY`; the chat, `may_move`, the answers to a
  check or an offer, a concern and `in_stages` keep `medium`. `test_a_body_check_in_turn_thinks_at_the_voice_rows_body_
  effort_and_every_other_turn_at_its_own` in `tests/unit/test_composer.py`, `test_a_body_check_in_turn_thinks_at_low_
  while_the_chat_and_the_stages_keep_medium` in `tests/integration/test_turn.py`.
- **Mani's text is not streamed to the person; the call is.** Because 75% of a chat call's wait is thinking before
  the first token, and only about 1.6 s p50 comes after it, so streaming the text would show the reply about 1.6 s
  sooner for the cost of a streaming API in the backend and both frontends (muhammad, 2026-11-05;
  `docs/latency-report-2026-11-05.md`, section 7). Revisit if the time after the first token grows.
- **A reply follows Lolly's cadence, and the check is her barometer.** Because the 2026-10-29 meeting
  ([message](../docs/client/messages/2026-10-29-meeting-cadence-and-role-plays.md), R41 to R48) gave the shape in
  her words: acknowledge, open the window (from them to the situation and the challenge), insight, ask; never
  summarise, never show the notes. `voice.md` says so, adds "I don't know" (situation or yourself?) and two feelings
  (which is more pervasive, or both?), and makes Directive about the challenge and what they can control. The
  summary-style check in `conversation.md` is now `# The barometer`: the insight into the core, then "Do you want to
  work through it with a framework?" with why it fits; for something really happening, whether they want to work
  out what to do. A yes still brings the client's offer (Try it / Tell me more / Keep chatting), which names the
  set; agreeing but wanting to keep talking is followed, not treated as a miss (`moments.md`, the check's [ctx]
  line, `check_answer`). Test: `test_mani_follows_lollys_cadence_and_checks_by_her_barometer`.
- **The person can edit their last message: it and Mani's reply are replaced, and the thread state returns to what it
  was before that turn.** Because muhammad wants ChatGPT's edit for the chat-tester (2026-11-03): replace, last message
  only, also inside a framework, chat-tester only for now. Every turn saves the state it will overwrite (title,
  understanding, check position, framework row, offered list) in `threads.rewind_snapshot` (migration 029);
  `POST /v1/threads/{id}/messages/{message_id}/edit` deletes the pair through `delete_last_message_pair`, restores the
  snapshot and runs the new text in one transaction (`chat/rewind.py`). Refused: a message sent by
  tapping an option, the style tap, a message already inside the thread summary. A crisis thread is edited wherever a
  message can still be sent: the edit has no crisis rule of its own; while a pause runs the edit route's gate and the
  send that runs the new text both refuse as `chat_paused`, and the whole edit rolls back (muhammad, 2026-11-10: a
  thread flagged once refused every edit as "paused" while it still took messages). The crisis record in `admin.crisis_events` outlives an edited message. The overnight memory fold is not
  undone, so an edit after it leaves the old words in memory (accepted for the tester). Tests:
  `test_editing_the_message_that_answered_a_check_takes_back_the_offer_and_runs_the_new_text`,
  `test_editing_the_last_message_inside_a_framework_puts_the_walk_back_where_it_was`,
  `test_a_message_that_cannot_be_taken_back_safely_is_refused_and_nothing_changes`,
  `test_a_message_in_a_crisis_thread_is_edited_wherever_one_can_still_be_sent`.
- **A message is cleaned to its visible text before anything reads it, and an empty one is refused with what to do.**
  Because a zero-width character inside "kill myself" turned into a space in the safety screen and the phrase was no
  longer matched, and the same hid a typed `[ctx]` block from its guard (muhammad, 2026-11-04). `text.clean_message`
  folds full-width and compatibility letters, drops zero-width, control and unassigned characters, makes every space a
  plain one and collapses runs; `SendMessageIn` and `EditMessageIn` apply it, and `safety.normalize` applies it again.
  Nothing visible left gives 422 "Write a message first. It can't be empty or only spaces."; over 4000 characters gives
  "That message is too long..." (`main.py` `_what_to_fix`). Not covered: look-alike letters from other alphabets.
  Tests: `tests/unit/test_text.py`, `test_an_empty_or_too_long_message_is_told_what_to_do`.
- **Mani runs the chat like a therapist runs a session, with Lolly's role-played session as its example.**
  Because three days of rules on `feat/identify-the-connection` did not change the shape of the replies: the model
  copied the mirror-then-question turns of the two ChatGPT conversations at the end of `voice.md` over every rule
  against them. That branch was deleted and this one started from `feat/understand-then-help` (muhammad,
  2026-10-29). `voice.md` now asks for a session that is neutral, empathetic and always moving somewhere, ending on
  a step they choose; never asking what can be inferred; a line of acknowledgment, then what Mani has, then one
  plain therapist's question only when it needs to know something; concrete suggestions with the words to use. Its
  example is Lolly's role play with manasa, lightly cleaned (one line of hers read "easy to do if they were
  narcissistic" and is given as "easy if they weren't"); the ChatGPT conversations are gone, their tone kept as one
  line. `conversation.md` holds muhammad's five principles: three questions before every reply (`need`,
  `needs_info`, `insight`, filled before the text with a `plan` of where the conversation is heading), internal and
  external dependencies (picture `dependencies`), suggestions aimed at what is in their control, a progression to a
  step and to the framework, and simple questions only when needed. The note carries the last plan and no list of
  questions to ask. Chat turns reason at `medium`. Tests: `test_mani_works_like_lollys_role_played_session`,
  `test_the_conversation_prompt_holds_the_five_principles_and_nothing_pushes_a_question`,
  `test_the_three_answers_and_the_plan_are_kept_and_the_note_carries_the_plan`,
  `test_what_the_outcome_depends_on_is_kept_inside_or_outside_them`.

- **Mani looks for the core, and the check is about the core alone.** Because in the 2026-10-28 weight-loss run
  Mani named fear of failing as the heart of it, when her thoughts ("I've ruined everything", "I lack discipline",
  "I'll never change") led to "I'm not capable of change", and shame under the guilt was never named; B then took the
  first thought instead of that belief (muhammad, 2026-10-28). The conflict template (what they are torn between, what
  they want, what is stopping them) forced every story into two pulls. Now the picture holds `core` (the belief the
  other thoughts lead to, the feeling underneath as Mani's reading, and whether it is about them, someone else or the
  situation), kept apart from the feelings they named. `conversation.md` adds the step "what it says about them" and
  "Finding the core": follow the thoughts down, name the core and the feeling underneath as an invitation, then talk
  about it rather than its effects. `heart` is exploring, `core_named`, ready (a stored `conflict_named` reads as
  `core_named`). The check says the core alone (muhammad chose this over core plus want and what is in the way); code
  stores it only when the reply's `core` is filled, and the confirmed case is that core with the feeling underneath.
  ABCDE's B and Thought Reframe's thought start from the confirmed core, and a deeper core found mid-framework takes
  that stage. A belief about themselves ("incapable") is never a feeling. Tests:
  `test_the_core_is_kept_whole_replaced_when_seen_deeper_and_rendered_as_a_reading`,
  `test_a_reply_is_stored_as_the_check_only_when_allowed_flagged_and_it_says_the_core`,
  `test_a_stored_check_is_ready_and_its_core_becomes_the_case_with_the_feeling_underneath`,
  `test_a_deeper_core_found_mid_framework_is_what_b_looks_at`,
  `test_the_conversation_prompt_goes_down_to_the_core_and_checks_it_alone`.

- **Every turn speaks in `voice.md`; the old path is gone.** Because the turns between the chat and a framework (the
  answer to a check, the offer, the body check-in, a safety concern) still read `mani_base.md`, `response_format.md`
  and a style file, so Mani sounded different at exactly the moments that decide what happens next (muhammad,
  2026-10-27). Those turns are composed by `composer.compose_moment`: `voice.md`, then `moments.md` (what each of
  those moments asks, the [ctx] block, the reasoning notes, staying in role), then the Framework Index; model and
  effort come from the `voice` row. `mani_base.md`, `response_format.md` and the three style files are deleted;
  `scripts/seed.py` switches their rows off by name (`RETIRED_PROMPTS`), so seed before deploying. The reply shapes
  went with them: no reply reports a `style`, `[ctx]` carries no `recent_styles`, and `public.thread_response_styles`
  is no longer written or read (the table stays, for the rows already in it). Tests:
  `test_every_turn_starts_with_the_same_voice_so_it_caches_once`, `test_the_old_layers_are_gone_and_switched_off_on_seed`,
  `test_the_moments_prompt_keeps_what_the_old_one_held_for_these_turns`, `test_config_tables_are_readable_and_seeded`.

- **Mani asks before the body check-in.** Because the 2026-10-27 review found the check-in arriving unasked straight
  after the last stage, and muhammad chose to ask permission first and tell Lolly (2026-10-27). This replaces
  2026-10-22's "no question before Step 1". After the last stage the reply is Mani's one-sentence reflection, then
  "Before we finish, would you like to take a moment to check in with your body and notice what you're feeling
  physically?" with Yes and Not right now (`somatic_ask`, the first stage in `content/prompts/somatic.md`; the
  wording is ours, not the client's document). Yes is Step 1, or the question about a place when their feeling points
  to one; Not right now goes straight to the overall question, with no physical response recorded. Tests:
  `test_after_the_last_stage_mani_asks_before_the_body_check_in`,
  `test_answering_the_last_stage_asks_before_the_body_check_in_and_yes_opens_step_one`,
  `test_not_right_now_skips_the_body_and_asks_whether_the_conversation_helped`.

- **A framework that stops helping offers to step out, named by code and the reply together.** Because the
  2026-10-27 review found Mani pressing on with a framework that no longer helped, and the coworker case questioned
  something really happening as a belief (muhammad, 2026-10-27). Each stage reply reports `framework_fit` (helping,
  confused, real_not_belief, already_balanced, disengaging); anything but helping is logged and its text offers to step
  out. Code counts stalls on the stage in force (`walk.after_turn`): a turn that adds nothing to the picture or to the
  stage's words is one, talking something through never is. Two stalls (`walk.STALLS_TO_STEP_OUT`) or a picture whose
  kind of problem is a situation put `not_helping` in `[ctx]`; the turn after an offer reads `exit_offered`, and their
  yes is `stop`, which ends the framework into the chat. D counts as answered when their words already hold both
  sides. Tests: `test_a_turn_with_nothing_new_is_a_stall_and_talking_it_through_never_is`,
  `test_ctx_says_when_the_questions_stopped_helping_and_when_stepping_out_was_offered`,
  `test_two_turns_with_nothing_new_offer_to_step_out_and_a_yes_ends_the_framework`.

- **Every conversation turns from understanding to helping, and code names the turn and the help move.** Because the
  2026-10-27 review found people heard but not helped: question after question, no progression, the styles alike
  in how they moved, and a direct request for help answered with another question (muhammad, 2026-10-27). The turn is
  `toward_framework` on the understanding record, set by `converse.toward` when the reply flags `asked_for_help`,
  their message added nothing new (`picture.quiet`), they answered in a few words three times running,
  or they said yes to a check about something really happening; another situation or a finished framework clears
  it. Once helping, the note gives each reply the move from `converse.HELP_MOVES` (kind of problem from the picture x
  style), a risk to someone else first; for a thought the check comes as soon as it may, as the way to ABCDE or
  Thought Reframe, and a yes to a check about a real situation brings help in the conversation, never a framework.
  Ideas they choose from are allowed in the chat (Lolly's "we do not fix" motto of 2026-10-18 to be confirmed with
  her, docs/client/requirements.md). The note also lists the questions already asked and, before helping, what is
  still unknown. The three styles in `voice.md` are three ways of moving, not three tones. Tests in
  `tests/unit/test_converse.py`, `test_a_yes_to_the_check_about_something_really_happening_brings_help_not_a_framework`,
  `test_asking_for_help_turns_the_conversation_and_the_next_note_carries_the_help_move`. Frustration with Mani does
  not turn it (muhammad, 2026-11-03): in Lolly's chat of that day "that is not the point" set it, and with no offer yet
  allowed the reply named the framework at her fourth message, against R27 and R28; a frustrated turn repairs and
  offers clarifying options or an insight, never the framework. `test_the_conversation_presses_toward_the_framework_
  when_it_stops_moving_or_they_ask`.

- **A framework's stages speak in the chat's voice; the framework gives the direction, never a script.** Because the
  2026-10-27 review found frameworks mechanical: questions predetermined, the stage ruling over what the person said,
  and the framework carrying on when it no longer helped (muhammad, 2026-10-27). A turn on a stage
  (`Moment.IN_STAGES`) is composed by `composer.compose_framework` from `voice.md` and `framework.md`, never
  `mani_base.md`, `response_format.md` or a style file; [ctx] still carries the stage. Its reply shape has no
  reasoning and no reply shape to pick. Something new mid-framework is talked about on the stage in force (not_yet),
  a stage already passed takes it from the picture with one short line saying so, the model question is a direction,
  and another situation is a choice: on switching, stop ends the framework and the chat carries on in
  `_converse`. Letter lines, confirm-once, when a stage is done, the options line and the body check-in stay code's.
  Tests: `test_a_framework_stage_speaks_in_the_chats_voice`,
  `test_switching_to_another_situation_ends_the_framework_and_the_chat_carries_on`,
  `test_a_framework_turn_is_a_conversation_the_stage_only_gives_the_direction`.

- **One picture of the person, shared by the chat and every framework, updated on every reply.** Because the chat's
  understanding did not run during a framework and the framework's step store forgot everything outside its steps,
  so a new feeling or belief mid-framework was lost and the two never informed each other (muhammad, 2026-10-27).
  Every reply shape carries `picture` (`PictureUpdate`: situations, feelings with what they are about, beliefs marked
  thought or happening, wants, what is in the way, risks, drop, focus, shift, problem type); `chat/picture.py` merges
  it into `threads.understanding.picture`, and `understanding.merge` derives the feeling line from it. The chat note
  and `[ctx]` both show it each turn. A framework stage names the part of the picture that feeds it (`picture:
  thought` or `picture: feelings` in `abcde.md` and `thought_reframe.md`); `walk.from_picture` brings stages already
  passed up to date when a turn adds a thought or a feeling, and stages ahead are judged from the whole picture when
  reached. Tests: `test_picture.py`, `test_a_new_thought_or_feeling_brings_the_stages_already_passed_up_to_date`,
  `test_the_framework_reads_the_chats_picture_and_a_new_thought_at_d_updates_b`.

- **Only a declined offer holds the next check back; a finished framework does not, and its reading is cleared when it
  finishes.** Because muhammad removed the 45-message wait after a finished framework, and without clearing the heart of
  it Mani could check again at once on the case it had just worked through (2026-10-27). `context.may_check`,
  `orchestrator.send` (retiring); `test_only_a_declined_offer_holds_the_next_check_back`,
  `test_finishing_a_technique_retires_it_without_losing_the_turn`.

- **An admin reads every person's conversations in full and takes part in none; each full read is logged.**
  Because the client and we review beta users' chats for their cadence, which a crisis-only browser could not show
  (muhammad, 2026-10-26; replaces the note "scope the conversation browser to unresolved crisis threads"). The list
  carries no content; `GET /v1/admin/threads/{id}` writes `admin.thread_reads` in the read's transaction. The send
  endpoint refuses an admin token (`test_an_admin_can_read_conversations_but_not_send_a_message`), the chat-tester
  shows an admin only the read-only viewer, and its on-page password reset refuses an admin account, since
  anyone who reaches the page can use it. `tests/integration/test_admin_threads.py`, migration 026.
- **Before a framework, Mani is its own conversation in the cadence of Lolly's two ChatGPT chats, and it overrides
  every older decision below about how the chat before a framework talks** (muhammad, 2026-10-26: "forget every
  previous decision in force, R, spec or document that stops MANI's cadence being exactly like the ChatGPT cadence the
  client provided"). Whenever no framework, offer or check is open (`Moment.CHATTING`, including after they stepped out
  of a framework, since 2026-10-27), the turn goes to `orchestrator._converse`: the `voice` prompt row
  (`content/prompts/voice.md`: Lolly's instruction, how a reply sounds, all three styles, both chats as examples) and the
  `conversation` row (how the chat moves, the heart of it, the check), the transcript, their message and a short note
  (style, the picture of them, what is understood, whether this reply may check, the framework they stepped out of),
  with the reply shape `ConversationReply` (text first, then heart, the case's three parts, a checking flag, picture,
  back_to_framework, crisis, title; no reasoning, no options, no [ctx] block). The check is Mani's own words; code
  stores it only when allowed (their 5th message on, cooldowns, and an earlier reply judged `conflict_named` or
  `ready`), flagged, and with all three parts, which become the case. After stepping out of a framework, asking for it
  again offers it with Try it (`back_to_framework`). Journal: `mani-vault/Journal/story-before-guess-2026-10-26.md`.

- **Mani reads their whole message against what it already understands and says what is new and how it changes its
  reading, in their words** (muhammad, 2026-10-22; 2026-10-26, see "Each reply says what is new"). Because in his Directive chat about a boss who does not lead, Mani mirrored one clause ("your boss doesn't
  seem to understand the work you show him") and dropped the headline the person named, "lack of leadership"; the mirror
  rule ("what matters", "never hand their whole message back") and the problem step's "who, what, how often" both
  select, and nothing says what to keep. Cut and replaced, not added: `mani_base.md` `how_you_talk` and `core issue`,
  `response_format.md` first reasoning step, `context.py` `understanding_next`, `schema.py` `issue` and `core_issue`. Not
  measured live (needs muhammad's yes, replay of that turn); [[direct-questions-have-no-target-2026-10-09]].
- **A turn waits on one chat call at the `voice` row's effort (`medium`, `low` for the body check-in), never a second to fix a draft; a chat turn's reading of them is
  one more call after the reply is sent** (muhammad, 2026-10-12; the reading after, 2026-11-03). Since 2026-10-29 the chat
  reply wrote its whole reading (14 fields, re-read every turn) and the picture (16) before its text, so its output grew
  with the conversation until attempts passed `chat_deadline_seconds`; two of Lolly's chats of 2026-11-03 ended in
  "504 llm_timeout" on her 11th and 7th messages (R53). Now `ConversationReply` holds what the turn calls for and the
  text, the note carries the picture as it stood before their message, and `ConversationUnderstanding` (reading and
  picture) is asked for after the reply, with the same system prompt and the reply in the messages, and recorded as
  purpose `understanding`. Since 2026-11-05 nothing runs after a response (Vercel stops the instance once it is
  sent, and cut off 15 of 49 readings; muhammad chose the app's own request, 2026-11-05; it works the same on AWS).
  A turn stores what it leaves for after its reply in `threads.pending_follow_up` (migration 032: the reading's call
  and whether the summary is due, keyed by Mani's reply, set or cleared by every turn), says `follow_up_pending`, and
  the app posts `/v1/threads/{id}/messages/{reply id}/follow-up`, which runs the reading and the summary side by side
  (`orchestrator.follow_up`). The request claims the work for `FOLLOW_UP_CLAIM_SECONDS` (120, in the row's
  `claimed_at`), so a second request meanwhile does nothing, and clears what finished; a part that fails stays
  waiting alone and unclaimed (`pending` in the response), so asking again runs only that part, and a request that
  died frees its work when the claim runs out. Each part stops at `FOLLOW_UP_DEADLINE_SECONDS` (90), inside the claim.
  A reading whose reply an edit took back is dropped, not merged onto the restored record (`_reply_stands`). Interim (muhammad, 2026-11-06): this is the app asking, for as long as
  the backend runs on Vercel; on a stateful host (Render, AWS) delete both endpoints, `follow_up_pending`
  and `pending_follow_up`, and run the work in the process after the response. Only the chat
  tester calls these today; `web/` and `mobile/` are not wired to the API. The call link and the trace are database writes only,
  awaited side by side before the turn's response. The app posts
  `/v1/threads/memory-fold` when it opens a new conversation. `mani/background.py` is gone. The chat tester asks on threads of its own
  (`client._in_background`); work the app never asks for is not done (the summary cron route can catch up summaries).
  Purpose `understanding` is migration 028, so `latency_report.py`, which reads `chat`, is the person's wait. Tests:
  `test_follow_up.py`, `test_follow_up_endpoint.py`, chat-tester `test_follow_up.py`. It merges onto the record as it is when it lands, under the thread's turn lock
  (`orchestrator._lock_thread`), so a message sent before it lands is never overwritten; that turn's note then has the
  picture one message behind. A reading that fails costs that message's picture, never a reply. The move to the offer
  builds its case from the picture as it was before the message. `test_a_chat_reply_waits_on_one_call_and_mani_reads_
  the_picture_after_it`, `test_a_reading_that_lands_after_the_next_turn_adds_to_it_and_overwrites_nothing`,
  `test_a_reading_that_fails_costs_the_picture_and_never_the_reply`. Not measured live (needs muhammad's yes); the
  hosted database needs migration 028, or the reading's cost row is refused (logged, the reading still lands). Because the
  client's R2 asks for no excessive latency, a turn waited on a reasoning model at `high` and up to two more
  full calls whenever a draft broke a rule (a median of 12.6 s and 41 s at worst, 2026-10-07), and the reply
  already carries its own written reasoning. Code shapes the reply instead of asking again: the reply's shape
  is picked from the database each turn (`schema.reply_for`), so while no offer may be made it has no offer
  field, the step through a framework is code's (`walk.py`), and `repairs.apply` strips what remains. The checks that need another call to fix are logged, not
  asked for again, so how often each happens is known. The one scoped extra call is the exercise pick at the end
  of a framework, at the chat row's effort. `test_a_turn_costs_exactly_one_provider_call` and the
  `reply_checks` tests in `tests/integration/test_turn.py` hold it. Not yet measured live (needs muhammad's yes).
- **A chat reply is streamed: a call silent for 15 s is cut and tried once more, one attempt has a deadline of
  45 s, and both attempts share a 65 s budget** (`chat_first_token_seconds`, `chat_deadline_seconds`,
  `chat_budget_seconds`, 2026-10-21; the deadline since 2026-10-14, 45 s and the budget since 2026-11-05). Because at 30 s three messages were lost at exactly 30.0 s while the slowest reply that made it took
  29.2 s, and the first-token cut never fired in that window (`docs/latency-report-2026-11-05.md`, sections 4 and 5).
  A retry gets the deadline or what is left of the budget, whichever is shorter, so the model costs a turn 65 s at
  most where 45 + 45 s could follow a malformed first attempt that ran to the deadline (0 of 154 chat calls in that
  window); every wait on a turn then adds up under the chat-tester's 90 s (see "Every wait on a turn adds up under
  90 s"; muhammad, 2026-11-05). Because
  `medium` effort makes some turns think 15 to 30 s before the first token (70 percent of output tokens were hidden
  reasoning, p50 9.7 s, 3 of 161 calls timed out), and a flat deadline around a blocking call could only fail them.
  muhammad kept `medium` on purpose. `chain.build` streams through `langchain-openai`'s `astream`, whose
  `stream_chunk_timeout` (set to `chat_first_token_seconds`; background calls keep `llm_timeout_seconds`) ends a
  silence between chunks, keepalives not counting; `client.complete` folds the stream into the one reply it used to
  get, records the cut attempt as its own `timeout` row, and retries once, sharing `MAX_SCHEMA_ATTEMPTS` with a
  malformed reply and a provider blip. Past the deadline or after the second silence the turn fails as `LLM_TIMEOUT`,
  retryable, "Mani took too long to answer. Please try again."; nothing was written, so a resend is safe. It does not
  make a thinking-heavy call faster (the median stays about 9.7 s) and a cut attempt is probably billed. `low` effort was
  taken for the body check-in only (2026-11-05); plain conversation turns stay on `medium`. `pytest.ini` ignores one
  third-party warning the stream emits (`field_name='parsed'`). Not measured live (needs muhammad's yes: his
  next chat turns, then read `admin.llm_calls`). `test_a_call_that_sends_nothing_for_too_long_is_cut_and_tried_once_
  more`, `test_a_call_silent_twice_fails_as_too_slow_after_two_tries_only`, `test_a_streamed_reply_records_its_usage_
  and_generation` in `tests/unit/test_client.py`.
- **Calls go only to OpenAI, its fastest endpoint first, never a pinned order and never flex; the chat reply asks for
  OpenAI's priority tier** (`openrouter_providers: ["openai"]` with `sort: latency`, muhammad, 2026-10-26; the tier,
  muhammad, 2026-11-05). Because the priority endpoint (`openai/fast`) ran at 109 tokens a second against the standard
  endpoint's 65, and thinking before the first token is 75% of a chat call's wait, for about $0.06 a day more at the
  traffic of 2026-11-03 to 05 (chat cost $0.18 in that window at the standard price, which priority doubles;
  `docs/latency-report-2026-11-05.md`, sections 7 and 8). A purpose `chat` call sends `service_tier: "priority"` and
  `provider.only: ["openai", "openai/priority"]` (`Settings.routing(priority=True)`; OpenRouter's docs name
  `openai/priority` and `openai/fast` as one endpoint). OpenRouter tries the priority endpoints first and falls back to
  the default ones in the list, so a turn is never failed for want of priority capacity and is billed at the endpoint
  that served it; the explicit slug is there because a base slug never matches a tier endpoint, and nothing else is
  allowed, so never Azure, Bedrock or flex; `data_collection: deny` stays; no `provider.order`, which turns off sticky
  routing. `understanding`, `memory_fold` and `summarize` stay on the default tier. `OPENROUTER_CHAT_SERVICE_TIER=default`
  turns it off with no change to code. Evidence after deploy: `service_tier` is `priority` on `GET /api/v1/generation`
  for chat generation ids (`scripts/llm_call_providers.py` prints the endpoint; see the report's section 7 for the
  call). `test_only_the_chat_reply_asks_for_the_priority_tier_and_each_purpose_keeps_its_own_key`,
  `test_the_priority_tier_is_switched_off_by_configuration` in `tests/unit/test_client.py`. Because Azure's content filter,
  which OpenRouter configures and we cannot, stopped every reply in an ordinary conversation about a boss (10 of
  28 calls on 2026-10-26, each after about 13 tokens), and a filtered reply is not an error, so neither
  OpenRouter's fallback nor our retry left Azure. An order is avoided because it turns off OpenRouter's load
  balancing and falls back only on an error (2026-10-14). Base slugs never match the tier endpoints
  (`openai/flex`, `openai/fast`). Every call records OpenRouter's `generation_id` (migration 024), and
  `scripts/llm_call_providers.py` resolves it to the endpoint that served it, so a slow turn is traced, not
  guessed. A timeout has no id (no reply came back); match it by time on OpenRouter's Activity page. If slow
  turns persist, the next step is streaming with a first token deadline, not hedged requests (see
  `mani-vault/Journal/provider-tail-latency-2026-10-14.md`). `test_routing_sends_a_turn_only_to_openai_fastest_first` in `tests/unit/test_config.py`, `test_each_call_records_the_generation_that_served_it` in
  `tests/unit/test_client.py`. Not yet measured live (needs muhammad's yes).
- **ABCDE's D asks what supports the belief and what might challenge it as two questions, one at a time, and code
  remembers which is still to ask** (muhammad, 2026-10-21). Because in the sister thread D was one stage with one
  stored status, `walk.merge` dropped the gap on every update, and the model alone chose each question: it never
  asked what might challenge the belief and asked "do you have enough information" three times. A partial stage
  now keeps the part still to ask (`StageUpdate.gap`, an id in the stage's `if_unclear`: `challenge`, then
  `information`) until the stage is known, and `[ctx]` shows it (`stages_known`: `dispute partial, still to ask
  challenge`). The model words the question from their belief and the feeling underneath; D's boundaries say each
  question asks one part, never says what it is for, never leads. The client's lines stay the fallback when the
  model asks nothing. Not measured live (needs muhammad's yes). `test_the_part_still_to_ask_is_kept_while_the_stage_
  is_partial_and_dropped_when_it_is_known` in `tests/unit/test_walk.py`, `test_what_is_still_to_ask_at_d_is_stored_
  and_sent_on_the_next_turn` in `tests/integration/test_turn.py`.
- **A message that asks something never moves a framework stage** (muhammad, 2026-11-05). Because manasa's "should I
  look at this thought or my numbness? Does one affect the other?" was reported as answered, the stage moved, and the
  reply opened on "Step 2 is..." with her answer under it. `walk.held_by_question` turns agreed, answered or corrected
  into not_yet when their message has a question mark or opens like a question; explore and stop are kept. Push back is
  not a code rule (muhammad: Mani stays with them and course corrects, never ends the questions for them).
  `test_a_question_inside_the_questions_is_answered_and_the_stage_waits`, `test_a_message_that_asks_something_never_
  moves_the_stage`.
- **"Ready" is a confirmation, never a deepening** (the client meeting, 2026-11-05). Because a vulnerable disclosure
  ("I don't remember the last time I did something just because it made me happy") counted as deepening the core, so
  the reply judged it ready and moved to the offer on it. A deepening keeps it core_named and gets a reply of its own.
  Once the move is allowed, it may come at core_named, not only at ready (muhammad, 2026-11-11): the father chat had
  the move allowed for four turns and no offer, waiting on a confirmation no reply asked for; the offer says the core
  back and they can correct it there, unless their message brings something new and painful (`converse.MOVE_MAY`,
  `test_once_the_core_is_named_the_reply_may_move_without_waiting_for_a_confirmation`). The wording alone was not
  enough (replayed: allowed three turns, no offer), so a move allowed and not made makes the next reply due
  (`converse.due`, `held_back` in the reply's thinking): at most one reply of waiting.
  Saying the core back is due too (muhammad, 2026-11-11): once every group is explored, a reading has landed and
  nothing else holds the move, the note says the core now, not "hold it until they have said what they came to say"
  (`converse.naming_due`, `test_naming_the_core_is_due_once_everything_is_explored_and_nothing_else_holds_it`). His
  chest chats had every group explored from turn 9 and no core said back in twelve chat turns; replayed, the core is
  named at turn 12-13 and the framework offered at 15.
  The chat's note no longer asks for a core from their second message and never asks a reply to ask because the last
  one did not. (A chat reply with no question was no longer counted as a miss; superseded 2026-11-10, see "Every chat
  reply ends on a question".)
- **A yes to the body check-in always gets the client's Step 1: its introduction, its general question and its five
  buttons, with no question of ours before them** (muhammad, 2026-11-04). Because the step that asked how a feeling
  they named was now (`somatic_check`, added 2026-11-03 after Manasa's comment, itself replacing the 2026-10-21
  question about a place) had no buttons, and testers saw the check-in arrive with nothing to tap. The step, its script
  and its code are gone; migration 030 moves any thread waiting on it to Step 1. A word in chat or inside a framework
  still never starts a body question. `test_a_yes_to_the_check_in_gets_the_clients_step_one_with_its_five_buttons` and
  `test_a_feeling_word_in_chat_or_inside_a_stage_never_starts_a_body_question` in `tests/integration/test_turn.py`.
- **An offer comes only on a clear yes to Mani's check of its understanding; the check comes from their 5th message,
  on a reply that judges the heart of it ready: the central conflict agreed, and what they want and what is stopping
  them known** (muhammad, 2026-10-26, replacing the three steps of 2026-10-13). Because Lolly's ChatGPT conversations
  of 2026-10-26 reached the heart of it at about the tenth exchange and she wants a framework to begin there (R30,
  R33), while the three steps (problem, core issue, feeling underneath, one an exchange: `understanding.STEPS`,
  `advance`, `found`, `[ctx] understanding_next`, all deleted) aimed each question at the next empty slot and checked
  at message 3 to 4 (baseline 2026-10-26, `chatgpt_reference`, Directive: "what does that mean to you?" three turns
  running in the boss chat, the friendship chat checked at message 6 before what she wants was known). Every chatting
  reply reports `heart` (`exploring`, `conflict_named`, `ready`), one closed value that must never grow back into a
  record (muhammad's guardrail). Since 2026-10-26 the check is made in Mani's own conversation (`_converse`): it may
  come only from `context.CHECK_FROM` (their 5th message), with no framework live, no check waiting, the cooldowns
  passed and an earlier reply that judged `conflict_named` or `ready` (`converse.check_allowed`); the note says so,
  and a `ready` reply that did not check makes the next note say the check is due, so code names the turn (journal
  2026-10-16: a step the model may take never fires). The check is the model's own text, flagged `checking`, with the
  conflict, what they want and what is stopping them as fields; those become the `case` the framework is about. Code stores when the last check was made (`threads.check_at_message_count`, migration 023); the next turn
  is `Moment.CHECK_OPEN`, whose shape alone carries `check_answer`, `heading_toward` and `offer`. A clear yes makes
  that reply the client's offer; anything else keeps chatting, and the check is used either way. A new check waits
  `COOLDOWN_AFTER_DECLINE` after the last check and `cooldown_for(outcome)` after the last offer, and a set just
  finished may be offered again on a new confirmed check. Before that: the client rejected an offer on the first
  message (R1, 2026-10-12), and check-then-offer comes from the meeting of 2026-10-13 (R14), which stands.
  `test_no_check_before_their_fifth_message_and_ctx_names_only_a_check_waiting_for_its_answer` and
  `test_a_check_is_answered_on_the_next_turn_only_and_then_waits_its_cooldown` in `tests/unit/test_chat_context.py`;
  `test_a_check_comes_from_their_fifth_message_once_the_heart_of_it_was_agreed`,
  `test_a_check_from_a_reply_that_did_not_judge_the_heart_of_it_ready_opens_nothing` and
  `test_a_reply_that_judged_the_heart_of_it_ready_without_checking_makes_the_check_due` in
  `tests/integration/test_turn.py`. Measured once, 2026-10-26, Directive: the boss chat checked at their 6th message
  and the friendship chat at their 9th; ChatGPT reached the same point at about the 12th. The set is chosen by what hurts, by its Use it when and
  Telling them apart; Structured Problem-Solving only once they say they want a decision or plan. No phrase
  matching ranks or shortlists them: the model chooses, code only checks the cooldown and what was already
  offered (muhammad, 2026-10-09; 2026-10-08: when a weak router
  guess stopped being the candidate, wrong SPS offers went from 4 of 10 live conversations to 0).
- **Which framework fits comes from the client's Framework Selection Cheat Sheet, one line per framework in
  its `central_indication`; while ABCDE is the only active set, every confirmed check offers it** (muhammad,
  2026-10-13, R15). Because the client's cheat sheet (2026-10-13) says to select only once the underlying
  concern is understood, never from the opening feeling, and gives one line per framework; and muhammad chose
  to offer ABCDE for now even for a concern the cheat sheet gives to another framework (the client's own sample
  conversation is Structured Problem Solving by it), which the client must be told. No framework id is in code:
  the offer goes to `heading_toward` when it is active, else to the only active set (`repairs.offer_framework`).
  The paused files carry their cheat sheet line too, and the seed refuses to activate a framework missing what
  the chat reads (`seed.missing_for_activation`), so bringing one back is a content change. Scenario group
  `pinpoint_and_check` in `scripts/scenarios.json`. Not yet measured live.
- **Memory is per person**. Because Mani should learn each person's patterns across chats, while a new chat
  still starts with none of the last one's messages (2026-09-23).
- **An offer is the client's template for its set, and the model fills only the slots** (spec 0003). Because
  a line the model wrote drifted from the client's wording and needed regex repair, while rendering makes it
  exact in every style (2026-10-12). The reply's `offer` carries `going_through`, and `lead_line` where the
  style's template opens with a whole line, for the set in `heading_toward`; code sends `offering.offer[style]`
  with them and the permission question, and Try it, Tell me more and Keep chatting (`repairs.offer_template`).
  The offer no longer lists the five steps, which R11 (2026-10-13) had added: they are told only on Tell me more
  (muhammad, 2026-10-22; `offering.steps` is gone from both files and from the seed check); `going_through` is the feeling they named, read from
  `understanding:` in `[ctx]`, as a short noun phrase ("your frustration"), and their worry only when they named
  no feeling (spec 0005). Tell me more is the client's longer `offering.explain[style]`; a no is `offering.keep_chatting[style]` with `their_words`. An offer that cannot
  be rendered is dropped, the model's text goes, and `offer unusable: <reason>` is logged.
  `tests/unit/test_repairs.py`, `tests/integration/test_turn.py`.
- **Superseded 2026-10-27 (every turn speaks in `voice.md`, see the decision above). One style file per thread, in the system prompt, written from the client's behavior lists** (muhammad,
  2026-10-12). Because the client separates the styles by what each reply is trying to do, and our own recipe per
  style, under shared rules that contradicted their examples, drifted from it (styles document, 2026-10-12).
  `content/prompts/style_directive.md`, `style_supportive.md` and `style_reflective.md` each hold that style's
  description in the client's words, with what to do and avoid. Their example conversations were removed
  (muhammad, 2026-10-13): the client's terse Directive examples pulled against the newer way of communication
  document, and the model copies examples over rules. Since 2026-10-26 Directive carries Lolly's two ChatGPT
  conversations as `examples` (R34, muhammad), edited only to drop the announced questions, ChatGPT's two slips and the
  figures the prompt bans; Supportive and Reflective carry none, so they do not copy Directive's voice. `composer.compose` sends only the style resolved for the thread, after
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
- **Inside a framework, a stage their words already answer is said back and confirmed once, never asked; one
  stage per reply, stepped by code** (muhammad, 2026-10-13, spec 0004). Because the client wants each letter
  introduced as it is reached and never to be asked again what they already said (R6, R12), and the model's own
  walk past answered stages asked them again once their words left the history window and could name a stage
  it never asked (2026-10-13). The reply reports `stage_answer`, then `stage_updates` (the stage in force from
  their message, and any earlier stage they correct), then `next_stage`: on every turn that can start or move the
  walk, its judgement of the stage after the one in force (A on a start) as known, possible (A only), partial
  with its `gap`, or missing, from everything they said about the issue they confirmed, before or after the check,
  by that stage's `ready_when` and `reach` (sent in `[ctx]` as `next_stage_ready_when` and `next_stage_reach`).
  It is applied only when the walk moves. Because a reach judged in an optional entry, scoped to after the check,
  was left out and C and D were asked though their feeling and what supports the belief came before the check, and
  a stage never judged looked the same in the logs as one judged missing (thread 4b93d612, 2026-10-14; the client's
  ABCDE document: "Use what the person has already shared"). A missing judgement on a move is logged as the reply
  check "reach unjudged". Nothing is reported or stored for a stage before the walk reaches it, so nothing goes
  stale (2026-10-13: the seed of every stage at the yes went stale twice; reviewed by Fable 5.1 and the
  architecture reviewer, and again 2026-10-14). `walk.py` merges the stage in force, then moves at most one phase,
  then merges the stage reached; an update for any other stage is dropped, logged: `agreed` counts only on a stage reached as a check,
  `answered` and `corrected` only with words for it ("yes, and more" with no new words reads as `agreed`). Not
  knowing never moves it: `not_yet` stays however often it is said, and only `stop`, their clear wish to leave the
  questions, ends the framework (declined, so it returns only when they ask for it). No stage is skipped. Every
  stage reached is one `[ctx]` told the reply about (a start or a move on its answer), so the model's text is used for it when it asks something; a partial D missing its challenge falls
  back to the client's own line for it (its `if_unclear` id, `NextStage.gap`). E is done only when they have a more
  realistic way to see it and one clear path, a plan ("raise it with HR") counting as the path and a permission or
  intention ("trust them more") never counting, and Thought Reframe's
  last step (`replacement`) only when they have a balanced thought they say they believe, which need not be positive,
  and have said, asked once, what they would like to do with it (gap `step`; muhammad, 2026-11-03, the friendship and
  daughter reviews: E closed with nothing to act on). The close carries that one thing forward and never puts what they
  want off to another time (`framework.md` Ending, `walk.next_line`). E and Thought Reframe's last step ask for the new view in
  plain words, both sides and the thought in their words, never "a more balanced way", and a clarification is one plain
  question with no options (muhammad, 2026-11-04: the father chat's "I don't think I understand your question"; the
  Tell me more list keeps Lolly's wording). The last stage, while it waits, always asks: a reply that stays there with no question and no question of its own in `forward` gets the stage's own (every stage that stays ends on a question since 2026-11-11, reversing the client meeting of 2026-11-05),
  not only after a body offer is dropped (the friend chat, 2026-11-04: a close written while E waited ended the
  conversation with nothing to answer; `test_a_reply_that_stays_on_a_stage_and_asks_nothing_gets_the_stages_question`).
  Where the new view forms and in the body check-in, a reported want or desire is ignored like the core (R70). Mani's own
  last reply sent back gets `greeting.COPIED_BACK` with no model call and changes nothing but the saved pair (R67,
  `test_manis_last_reply_sent_back_gets_the_fixed_line_and_changes_nothing`)
  (the client's Thought Reframe document, matched by muhammad, 2026-10-21; it replaced his earlier "and hopeful" gate,
  and the old `closing` stage is gone: one acknowledging sentence, then the body check-in; Mani may still offer loose
  possibilities when they are unsure, the person decides; safety and danger boundaries stay); The stage reached opens with its `intro` line, then: for a known or possible stage, A to E, Mani's own
  confirmation, saying back only what they said for that stage and asking in its own words whether it is right
  (muhammad's team lead, 2026-10-13: the fixed "Is that right?" phrases read as canned; `walk.CONFIRM_ASK`), with
  A's client `confirm` line or their words and a phrase from `confirm_phrases` only as the logged fallback
  ("confirm text unusable") when Mani's text is empty, asks nothing or was written for another branch; for partial, the
  model's question for only the gap; judged missing, A's client `missing` line with the feeling word in the
  running understanding (spec 0005) when they named one, otherwise Mani's own question built on the client's
  `ask` and about their situation, with the client's `ask` as the logged fallback ("missing asks nothing");
  reached unjudged, the client's line. A reply that stays is the model's text with no letter line. Each falls back to fixed text when the
  model's does not fit, logged by name. Leaving the last stage enters the body check-in. No stage
  question carries a button: a "Not sure" button was added by mistake and removed (muhammad, 2026-10-09). The
  chosen style holds inside a framework through its style file. A question that makes them uneasy keeps the
  stage, asked more gently from another side; unsure typed ("I don't know", "not sure") is helped with two or three
  loose possibilities, thinking aloud, each a different set, until they have it or stop (muhammad 2026-10-21; the
  model's reading, not a phrase list). Every stored word that is said back
  (`said`, the understanding and the check) is defined as said to them as you, a dozen words at most, because a
  third person note pasted into A's client line read "From what you've shared, their boss criticized their…"
  (muhammad's live run, 2026-10-13); `scripts/scenario_check.py` flags it as "talks about them, not to them".
  `tests/unit/test_walk.py`, the walk scenarios at the end of `tests/integration/test_turn.py`, and the live
  `frustrated_work_full` and `overtime_full` in `scripts/scenarios.json`.
- **A framework walk never skips and helps when they don't know** (muhammad, 2026-10-21). Because "I don't know" was
  routed around three ways in a row (silent skipping, the Not sure button, `let_go` after a second `not_yet`) and ended
  frameworks having helped no one. A known stage is confirmed by them before the walk moves; an unclear one keeps the
  conversation on it, with two or three loose possibilities from what they said, never the same twice, and no cap; only
  `stop` ends it (`test_not_knowing_never_moves_the_walk_however_often_it_is_said`,
  `test_a_wish_to_stop_leaves_the_framework_and_it_comes_back_only_when_asked_for`). What was found before the offer,
  the feelings they named and the case they confirmed, reaches every stage turn as `their_case` in `[ctx]`
  (the stored understanding, relabelled while a framework runs or is about to start), and every stage question and
  possibility is about it, in their words (muhammad, 2026-10-22; `test_the_findings_are_their_case_once_a_framework_is_running_or_about_to_start`).
  Every feeling they name is kept, none twice, in a framework too. The case is the confirmed check and does not grow:
  the problem, core issue and underlying feeling that grew add-only from 2026-10-22, because the boss chat's D and E
  were built on a first read that missed details said later, are gone with the three steps (muhammad, 2026-10-26: the
  record must not grow back into a form). What they add later is in the transcript, which the model sees whole
  ("The transcript is the memory within a thread"); whether D and E still use it is not yet measured.
  The stages their case can answer (ABCDE A, B and C; Thought Reframe's thought and why it hurts) are judged against it
  through their `reach`, so they are said back and confirmed once, never asked again.
- **ABCDE is offered from the client's ABCDE document** (muhammad, 2026-10-09; Thought Reframe joined it 2026-10-21). Because the client's
  ABCDE document of 2026-10-09 is what we build to, and ABCDE's stages give the questions a target
  (2026-10-09); why the other five are paused and why the body check-in stays: reason unknown, muhammad to
  confirm. Each stage opens with its letter and name ("A is for Activating Event."), as the document shows
  (muhammad agreed 2026-10-13, R12), and nothing comes before it, so the styles' consent lines are no longer
  sent (the document goes from Try It straight to "A is for"). What Mani knows lives in the stage store; a stage
  already answered is confirmed once, as the decision above says, and one not known is asked with the document's
  question about their situation, as the decision above says, using the feeling word they gave for A if they
  named one. Tell me more is
  the numbered five steps in the person's style word for word (`stages.offering.explain`), the offer follows the
  client's pattern per style (`offer`), Keep chatting asks the client's question (`keep_chatting`), the permission
  question is "Would you like to try it?" in every style, and the body check-in is asked after E (muhammad
  decided to keep it). Supportive inside a framework adds no extra reassurance, validation or
  questions.
- **The stage store** (`thread_technique_state.stages_known`, migration 020, written by code after the reply).
  Because the stages reached so far must be remembered by code, the walk's record, not a stand-in for memory: the
  model sees the whole thread (the decision below), and each stage is judged when it is reached (R6, 2026-10-13). Keyed by framework id
  then stage id: `said` (their short words, at most 200 characters), `status` (partial, possible for A only,
  known, done) and `tries`. On the stage in force the latest words win and the status never drops; elsewhere only
  a higher status replaces what is stored, or a correction, which keeps the higher status (`walk.merge`).
  An entry
  stored ahead of the stage in force, by an earlier version, is ignored and shown as not reached. It has
  its own update, never part of the shared upsert, so a later offer row keeps it; it is kept when a run retires,
  cleared for one framework when that framework starts again, deleted with the thread, never logged, and sent
  only in that thread's `[ctx]`, disarmed. With `AI_DEBUG_MODE` on, a turn returns `ledger`, built from the
  store: every ABCDE stage as known, possible, partial, done, missing or not reached, with the stage the walk is
  on marked, and the chat tester shows it under "What Mani knows". `Turn.stage_trace` carries the ids and
  statuses alone, for `scripts/scenario_check.py`.
- **The transcript is the memory within a thread** (muhammad, 2026-10-13, after the architecture reviewer's
  comparison of seven designs). The model sees the whole thread up to `CONTEXT_BUDGET_CHARS` (40,000 characters
  of message content, `messages.for_context`); past it the oldest messages leave in blocks of
  `CONTEXT_DROP_BLOCK` (20), so what is shown, and its cached prefix, stays the same between drops, and only then
  is the thread summary sent and refreshed (`needs_summary` when more messages have left than any summary
  covers; the cron backstop uses the same rule). Because the 20 message window was inherited, a thread reaches
  ABCDE's E at about message 23 to 30, and every store built to outlive the window had to guess ahead and went
  stale or thin (the seed, the understanding record). The budget is the rollback lever. The app's thread view
  has its own tail (`routers/threads.OPENING_TAIL`). OpenAI, when it serves a turn, receives the whole thread,
  the same open data protection question as before. `test_the_model_sees_the_whole_thread_until_the_budget_then_
  loses_whole_blocks` in `tests/integration/test_queries.py`.
- **The running understanding** (`threads.understanding`, migration 022, written by code after the reply;
  muhammad, 2026-10-13, specs 0005 and 0006; cut to three keys 2026-10-26). Because the feeling they open with was
  said once and then lost (the frustrated chat, 2026-10-13, R4, R6). It holds `feeling`, every feeling word they
  name, gathered, the first kept when full; `heart`, the last reply's judgement of the heart of it, replaced each
  turn; and `case`, the summary of the last stored check. `understanding_update` reports only `feeling` (muhammad,
  2026-10-26: the record had grown to seven fields the model filled before it spoke, and Mani filled in a form instead
  of listening). Nothing is merged on a concern turn. It is sent back every later turn as the `understanding:` line in
  `[ctx]`, or `their_case:` once a framework is running or about to start, disarmed; code reads `heart` to make the
  check due, `feeling` for A's feeling slot and the body place check, and `feeling` with `case` for a stage that
  carries the case. Its own update, only by `mani_service`; never logged; sent only in its own thread; deleted with
  the thread. With `AI_DEBUG_MODE` on, a turn returns `understanding` and the chat tester shows it under "What Mani
  knows". `tests/unit/test_understanding.py`, the spec 0005 tests in `tests/integration/test_turn.py`,
  `tests/sql/test_grants.sql`.
- **No phrase lists judge the conversation** (muhammad, 2026-10-09). Because literal phrase matching cannot
  read a paraphrase, so its judgments were silently wrong whenever people worded things differently
  (2026-10-09). Code holds no list of what people say
  (vague, unsure, correcting, wanting only to be heard), no list of feeling words, no list of self-judgments
  and no pain words. The rules for those live in the prompts, and a draft answers them itself: a reply that
  asks nothing says so by its shape (`schema.NO_QUESTION_SHAPES`). What code still checks is not about meaning:
  the crisis screen, script and internal-word stripping, and the `[ctx]` injection guard. The model reports
  its own judgments in typed fields that exist only in the moment the database picks (spec 0003): the answer
  to an offer (`offer_answer`), the offer's slots, and the body route branch (`body`). A paused framework moved back
  brings no phrase list with it; anything it needs to detect is designed when it returns (2026-10-12).
- **Each reply says what is new and how it changes Mani's reading, offers that reading as a guess for them to confirm
  or correct, and asks one question that tests or deepens it, which may hold two possibilities; now and then an
  observation takes its place; a question is never announced** (muhammad, 2026-10-09; cut 2026-10-12; spec 0005,
  2026-10-13; 2026-10-26). Because Lolly's ChatGPT conversations (2026-10-26, R30 to R32) got to the heart of it
  with readings and questions that test a guess ("Was it the disagreement itself, or how she treated you?"), which
  our rules banned ("You never explain people to themselves", "never leads them to a conclusion", "Mani never joins
  two things they said into a link they did not make", all cut), and the required `options` line made every reply
  end on two questions; `options` is gone from the chat shapes, and stage and body replies keep it. Kept: never an
  event, person or motive they did not give, and never a general statement about how people are (the "explains
  people" voice of 2026-10-13); every feeling they named stays in view and the reasoning reads each message against
  them (muhammad, 2026-10-25); never asking for what they already made clear, in any words; no advice hidden in a
  question; told it got something wrong, it says what it missed and never asks them to explain again (R26). The
  preamble Lolly flagged is not quoted in the prompt, because a quoted ban gets spoken (R3); `scenario_check` flags
  "announces a question". Before that, Mani re-asked what they had said (2026-10-09) and ABCDE's checklist steered
  the questions toward its own needs (the frustrated chat, 2026-10-13, R4). `test_questions_follow_their_answers_from_one_rule_with_no_checklist_or_ban_beside_it`,
  `test_the_heart_of_it_replaced_the_steps_and_the_prompt_did_not_grow` (`mani_base.md` held to 9,180 characters),
  `test_before_the_check_one_question_carries_its_own_possibilities_and_nothing_is_added_under_it`.
- **Mani's voice is the shared shape in `mani_base.md` `how_you_talk` plus the chosen style's file; there is no
  shared example conversation** (muhammad, 2026-10-22, replacing "Mani talks like the client's sample conversation",
  2026-10-13). Superseded on 2026-10-27: every turn now speaks from `voice.md`, which carries the client's two
  example conversations, and `mani_base.md` is retired. Because all three styles read the same: one sample was copied in every style, one line blended
  Supportive and Reflective for everyone, and each style file was one sentence. The shape stays (what is new and the reading it changes, in their words, one question on its own line,
  three to six short sentences since 2026-10-26, no dashes), and
  each style file now says what its replies are for, in the client's own words, with what to do and avoid and the reply
  shape it reaches for. The client's sample stays in `docs/client/messages/2026-10-13-way-of-communication.md`. Not
  measured live (needs muhammad's yes; the case-note voice of 2026-10-13 may return). The sample replaced rules
  that produced lines like "can make it hard to separate one piece of feedback from what you think it says about your
  ability" (live, 2026-10-13; diagnosed by a second model), because they forbade the sample's own moves;
  `recent_openers` is gone from `[ctx]` for the same reason, and `scripts/scenario_check.py` flags "explains people".
  The lines saying what Mani wants to understand or does not want to assume stay out: the client liked the mirror, not
  that line (muhammad, 2026-10-21). Because muhammad wants human-like language in plain everyday words (2026-10-07),
  and the client's way of communication document (R13, 2026-10-13) shows the voice: up to four short sentences in
  short paragraphs, a direct ask answered plainly first, and an understanding
  of how things fit together said for them to confirm or correct. Inside a framework the options for answering a stage's question are the reply's `options` field, which the model must fill (or leave null
  for a yes or no question) and code puts on a line of their own under the question; before a framework there is no
  `options` field since 2026-10-26 (R30), because the prompt
  rule for them was lost to "one question" lines elsewhere three times (muhammad, 2026-10-22;
  `test_the_options_go_on_the_line_under_the_question_and_only_where_the_reply_is_free_text`); framework stage replies carry it too, under the model's own stage question and never under the
  client's fallback line (`test_the_possibilities_go_under_the_models_own_question_and_never_under_the_clients_line`).
  The check reads as one flowing summary of the conflict, what they want and what is stopping them, then asks whether it
  captures it or something was missed (muhammad, 2026-10-26). Its paragraphs are laid out in code, not left
  to the model, which broke the line before its question in some replies and not others: Mani's own text
  before a framework goes out with each closing question on a line of its own (muhammad, 2026-10-21: the model put them on one line despite the prompt), unless a single question has
  fewer than 8 words before it (`repairs.laid_out`, gated in `orchestrator.send`; stage replies stay one paragraph, as the ABCDE
  document writes them; `test_manis_own_text_goes_out_as_the_client_lays_it_out`, 2026-10-14). It never adds a fact they did not give, which
  the sample's own summary does (muhammad, 2026-10-13). Correct grammar and punctuation, each sentence short enough
  to say in one breath, as people talk in daily life (`mani_base.md` `voice`). Stage questions inside a
  framework carry the feeling underneath (muhammad, 2026-10-21, after the sister thread, where B and D dropped the
  guilt they had confirmed): a stage reached as missing is a short mirror of their situation and the feeling
  underneath, then its question in the model's own words with the possibilities under it, and the client's `ask` only as the logged
  fallback when the model asks nothing (muhammad, 2026-10-22, replacing "as written": the E line said "both sides"
  with no side in view). Stage A says back what happened together with the underlying feeling they confirmed, so
  they do not say it twice. Naming what the question refers to stands (2026-10-14):
  the bare question ("…about what was happening?") was met with "regarding?" (thread 425f6a55) and the
  client's document adapts it the same way ("What makes you believe your manager is planning to replace you…").
  Free rewording stays out: it produced stacked lines like "What do you find yourself telling yourself about
  that?" (2026-10-12). `walk.reply_text`,
  `test_a_missing_stage_is_its_letter_line_then_manis_own_question_about_their_situation`.
- **`[ctx]` explains itself.** Because a plain turn paid about 4,900 characters of key dictionary to explain a
  154 character block, and the two drifted apart (2026-10-09). Each line carries its meaning for this turn's value on the line under it
  (`context._MEANING`), so the prompt (`framework.md`, `moments.md`) says only what the block is. A test fails if a key is sent
  without one.
- **An open offer is read from the database, not from the buttons on screen.** Because an offer can stay open
  with no buttons showing, and a typed yes to it then started nothing (2026-10-09). A yes to it starts it either
  way. A tap on its buttons decides by itself; otherwise the reply's `offer_answer` does (spec 0003). Asking
  about it is answered with the client's explanation and the offer again; any other answer declines it.
- **"It hit me so hard" is not violence.** Because the client's own ABCDE signal "why it hit me so hard" was
  read as violence and Mani asked if they were in danger (2026-10-08). `safety.screen` sets aside "hit me" when a thing is its subject
  (it, that, this, what); a person hitting them still asks.
- **chat-tester resets a password on the page**: email and new password, set through the Auth Admin API with
  no email. Because the test tool should need no mail setup, accepting that the page stays non-public
  (2026-10-07); the seven day session: reason unknown, muhammad to confirm. Anyone who can reach the page can reset any ordinary account, so it stays non-public; an admin account is refused, because it reads every conversation (2026-10-26). A browser session
  is remembered for seven days.
- Also settled: OpenRouter only, asyncpg not PostgREST, the
  `public` and `admin` split, the `mani_service` role, three security definer write functions, the
  deterministic safety screen as the only thing that locks a thread (superseded 2026-11-06, when nothing locked, and
  2026-11-13: no phrase locks, and danger that continues with nothing in place pauses the chat, see the safety
  entry), in process routing, no streaming.
  Because: one provider was ever used (2026-09-14); a turn's writes must succeed or fail together, which
  PostgREST cannot do (2026-09-15); anything PostgREST exposes is reachable with the anon key (2026-09-15);
  a backend acting as `authenticated` let users forge Mani's replies (2026-09-16); the definer functions write
  rows no plain grant should allow (2026-09-15); a small model over-fires the crisis flag on ordinary
  distress (2026-09-29); plain request and response is acceptable while turns stay short (2026-09-14; measured
  2026-11-05, see "Mani's text is not streamed to the person").
  In process routing no longer describes the code (`router.py` is gone and the model chooses the framework):
  muhammad to reword or drop it.

## Before it takes real traffic

Ordered by what breaks first.

1. **Hosted Data API settings.** `supabase/config.toml` configures local development only. On a hosted
   project set `auto_expose_new_tables` off and the exposed schemas to `public` and `graphql_public` by hand;
   `db push` does not carry them. Run `scripts/test_db.sh --local` against the hosted database first, or a
   user could clear their own crisis flag.
2. **Rate limit and cost ceiling.** `DAILY_MESSAGE_LIMIT` exists and defaults to 0 (off); muhammad sets it in the
   environment. `MINUTE_MESSAGE_LIMIT` is 10. There is no per user cost ceiling; `llm_calls.spend_since()` is what one would read. A retried
   send with the same `client_message_id` returns the first reply for free.
3. **Crisis resources are reference numbers, US only.** `crisis.RESOURCES` holds 911, the 988 Suicide & Crisis
   Lifeline and Crisis Text Line (muhammad, 2026-11-13); `crisis.pause_reply` names 911, and 988 for themselves or an
   unknown kind; the pop-up shows 988 (call and text) and 911; neither names Crisis Text Line;
   the pop-up also links Find A Helpline (findahelpline.com), listed for every country. The specifications refer to an
   approved protocol and helpline list and contain neither. Needs the client's list, by country; until then the pause
   text gives US numbers to everyone, wherever they are.
4. **Migrations are not run by anything.** `supabase db push` is manual.
5. **The catch-up cron needs Vercel Pro.** `backend/vercel.json` calls `/internal/cron/catch-up` every 5 minutes,
   with `CRON_SECRET` set on the project. Vercel Hobby refuses to deploy a cron that runs more than once a day, so the
   file must not reach a branch a Hobby project deploys from.
6. **`CORS_ORIGINS` must name the deployed web origin**, or `web/` gets no browser response. Mobile is
   unaffected.
7. **Pool and load.** Set the hosted `DATABASE_URL` to the transaction pooler: host
   `aws-0-ca-central-1.pooler.supabase.com`, port **6543** (today 5432, the session pooler), same user and database.
   Then `supabase db push` for migration 031. Load-tested offline only (Latest measurements): one instance served
   100 people with no errors; at 500 the database held and 30% of sends were refused by the 100 model-call slots.
8. **The backend's database role.** `001_initial_schema.sql` grants `mani_service` to `postgres`. If the
   deployed `DATABASE_URL` connects as anything else, `set local role mani_service` fails. Grant it to that role,
   never to `authenticator`.
9. **Email confirmation is not enforced** and **app attestation is absent.** Confirmation needs
   `enable_confirmations` in Supabase and SMTP; do not read `email_verified` from the token, because the user can
   write it. Attestation layers on after the rate limit, in front of the chat endpoint only.

## Open decisions for muhammad

- R2's 4 s median (2026-10-14; resolved 2026-11-05): muhammad chose `openai/fast` for chat replies at double the
  price, with body check-ins at `low` (see Decisions in force). The 2026-11-05 median was 9.8 s, mostly thinking at
  `medium`, so 4 s is not expected from the tier alone; tell the client the measured median once the change is live.
- Tell the client (2026-10-13, spec 0004): inside ABCDE, Mani goes one stage per reply, and a stage the person
  already explained is said back and confirmed once ("Is that right?" or a similar short phrase) rather than
  named and passed, as the ABCDE document's Situation 1 shows for A. Only A has a "possible" event; for B to
  E a guess is asked, never said back.
- Tell the client (2026-10-08): "overwhelming" was removed from the Structured Problem Solving description,
  since every offer showed a feeling the person had not named; Supportive and Reflective questions were
  written for the 26 stages whose three styles were identical (the client's wording is kept as Direct, or as
  Reflective for ACT `present`); the offer buttons read Try it / Tell me more / Keep chatting, not the
  specification's "Yes, let's try it" / "I want to keep talking". Have them review the new lines.

- The client's crisis resources and safety wording (point 3 above).
- Tell the client what caused the first message offer (R1) and that an offer now comes only on a yes to
  Mani's check of its understanding, at their fifth message at the earliest and only once Mani knows the conflict,
  what they want and what is stopping them (R33), in every style, and have them read about five real Supportive
  and Reflective transcripts.
- Send the client a short written summary of the flow (no transcript of the 2026-10-13 meeting exists) so they
  can confirm it: Mani works toward the heart of it with readings and questions that test them, checks once it
  knows the conflict, what they want and what is stopping them, and offers only on a yes (R14, R30, R33).
- Tell the client (2026-10-26): the Directive examples are her two ChatGPT conversations with the announced
  questions, ChatGPT's two slips (23 years, "he") and the figures Mani avoids taken out (R34).
- Tell the client (2026-10-13): Mani's check uses only the person's words. The summary in their sample
  conversation adds facts the person never said ("acknowledge the problem when you confront them, promise to
  improve"), and Mani does not copy that (R13).
- Tell the client (2026-10-21): the third step before the check is now the feeling underneath, not what is in their
  control. A feeling the person did not name appears only as a possibility inside the check (R17, R34, R35).
- Tell the client (2026-10-13): by their own cheat sheet, their sample conversation is Structured Problem
  Solving, which is paused, so it gets ABCDE for now, as does every confirmed check (R15).
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

- **Production is Vercel Hobby functions in iad1, with the database in ca-central-1.** Work started after a response
  was lost there: it suspends or ends the function (Vercel's `waitUntil` is Node and Edge only). Nothing runs after a
  response any more (2026-11-05); the app asks for it (see the reading entry in Decisions in force). The rest of this
  entry is the evidence from before that: 15 of 49 `understanding` calls of
  2026-11-01 to 05 timed out at 61 to 335 s against a 60 s wait, background calls spent p50 6.3 s between OpenRouter
  finishing and our row being written (chat: 0.33 s), and both memory-fold retries never wrote a row, so the person's
  picture and memory are being lost (`docs/latency-report-2026-11-05.md`, sections 5 and 9). Every database round trip
  also crosses from iad1 to ca-central-1. Kept on Vercel for now by muhammad, 2026-11-05. The fix is a container host
  near ca-central-1 (the `Dockerfile` is ready) or a queue for the background work.

- **Hosted and local schemas match.** Checked read-only on 2026-10-07: the same migrations, columns,
  enums, functions and RLS policies, and the same prompts, frameworks and exercises (only seed timestamps
  differ). The production deployment is `45543ed`, the head of `main`. What prod's environment variables
  hold is not readable, so those are unchecked.
- **Migration numbers were reused across the reverted branches.** `011` was both
  `technique_state_holds` and `technique_outcome_stopped`; `013` was both `llm_call_decision` and
  `llm_call_facts`. Reviving any of those branches collides again.


- **Body check-in, tell the client (2026-10-22):** the buttons for the six places a Somewhere Else answer can name,
  Mani offering the closest exercise for a place that has none, and the personal question about a place (2026-10-21)
  with its word list, are ours, not in their document; the exercises are
  unreviewed by their clinician. Keep Chatting continues from their case and where they ended up (`landed_on`), in the
  same mirror, question and possibilities shape, never "what would you like to talk about".
- **Generated TypeScript types** for `web/` and `mobile/` from the OpenAPI schema, with a CI gate. No CI exists.
- **Admin audio upload.** The 30 seeded exercises come from `content/exercises/` through
  `scripts/seed_exercises.py`; there is no upload route, and the admin exercise CRUD takes an existing
  `audio_path`.
- **A worker process** for summaries and the memory fold, for when there is more than one instance.
- **Model-call capacity at 500 people.** One instance's 100 slots run out (Latest measurements). Either more
  instances (Vercel adds them on its own; each has its own 100), a higher `MODEL_CALLS_IN_FLIGHT` once OpenRouter's
  rate limit for the key is known, or the reading after a reply given a share of the slots it cannot exceed so it
  never refuses a person's reply. Unmeasured on Vercel.
- **A `busy` 503 or a slot 429 logs at ERROR or WARNING per request**, and 5xx goes to Sentry with a traceback. Under
  load that is one report per refused request; consider logging them without `exc_info`.
- **`GET /v1/admin/models`**, which the prompt editor's model dropdown needs.
- **`threads.vague_streak`** is granted to the backend and written by nothing; the pacing it belongs to is
  designed, not built.
- **`appropriate_when` and `not_when`** in the framework files are read by nothing (each file says so).
- The words "worried", "concerned" and "a lot" still reach about 1 reply in 10 in some scenarios; repairs log
  them.

## Latest measurements

**Offline load test, 2026-11-05** (`scripts/locustfile.py`, one backend process on this machine, local Supabase
through its Supavisor in transaction mode, `scripts/fake_openrouter.py` at the production profile: first token p50
6 s and p90 12 s, then 1.6 s of text; each person sends every 30 to 60 s for 10 minutes, after a 20 s ramp):

| people | sends | errors | turn p50 / p95 / max | pooled DB backends, peak (active) | backend CPU mean / peak |
|---|---|---|---|---|---|
| 100 | 1,140 | 0 | 7.7 / 16 / 15.8 s | 5 (3) | 17% / 43% |
| 500 | 5,786 | 1,766 `429 rate_limited` (31%) | 7.6 / 17 / 17.8 s | 5 (5) | 35% / 68% |

At 500 the first thing to break is the instance's 100 model-call slots: about 9 sends a second, each holding a slot
for the reply (~8 s) and again for the reading after it (~8 s), need ~150. 977 readings were refused too, so those
people's pictures went unread. No `busy`, no database error. Before the prompt-cache fix the same run failed 3,694
of 3,708 sends `busy` (Decisions in force, the read-think-write entry). Not measured: Vercel's own concurrency per
instance, the cross-region round trips (local is ~0 ms), and a real provider's tail.

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
