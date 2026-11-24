# Port status

What the backend does today and what is still open. Stack notes: `.claude/BACKEND.md`. Database rules:
`.claude/SUPABASE.md`. **Update this file in
the same change as the work.**

## Status, 2026-11-18

- The TypeScript to Python port is complete. FastAPI is the only thing that touches the database.
- Tests: `pytest` runs 338 tests, 325 passing and 13 skipped (2026-11-18, after the one-call rebuild): the 13 mint a
  symmetric token and skip on a JWKS-configured project.
- Database: 34 migrations (000 to 010 and 018 to 040), 19 tables (10 `public`, 9 `admin`), 2 frameworks and 3 prompts
  seeded (`mani`, `summarization`).
  `admin.exercises` holds the 30 library exercises from `content/exercises/` (as "mani-app" holds them on 2026-11-13;
  the other hosted project was not compared), with their audio in the
  private `exercises` bucket (`scripts/seed_exercises.py`). Two hosted projects held every migration of the time and
  the same data (2026-11-06): `heqenombgkihfeggrxqc` (muhammad's org, ca-central-1, the Hobby deployment's database)
  and `aipgficduzufstilndbw` "mani-app" (the Mani org, us-east-1, for the Vercel Pro deployment). Migration 037 has
  run only on this machine's databases (2026-11-13), and 039 and 040 likewise (2026-11-18).
- Models: the chat turn runs on `deepseek/deepseek-v4.1-flash-1017` at reasoning effort `high`, routed only to
  `sail-research` then `deepinfra`, sorted by price, with `zdr: true` (muhammad, 2026-11-22), as the `mani` prompt row names them (`content/prompts/mani.md` frontmatter, seeded into
  `admin.prompts`; see Decisions in force). Summaries run on `openai/gpt-6-luna` at `high`, routed
  only to OpenAI (`mani/config.py` and their prompt rows), and so does the voice transcription in `mani/stt.py`. Every
  endpoint keeps `data_collection: deny`, so training use stays refused. Effort is billed: measured against Azure,
  `high` spent 26 reasoning tokens where `low` spent 0, about three times the cost of the same call.
- Every call to OpenRouter carries its providers, data policy and reasoning effort from `chain.request_body`; a prompt
  row's own `routing` replaces the settings' default provider list (`Settings.routing`). The voice translation in
  `mani/stt.py` uses the same body. It is still not recorded in `admin.llm_calls`, which has no purpose for it.
- A reasoning model's output budget covers its thinking and its reply together. Every caller sizes
  `max_tokens` for the reply alone, so `chain.sampling` adds `REASONING_ALLOWANCE_TOKENS` (8,192) on top, MiniMax
  included (`chain.ALWAYS_REASONING_PREFIXES`). Without it, at effort high, 4 of 61 chat calls ran out of tokens while
  thinking and the turn failed (2026-10-07). Measured by the rebuild's evaluation on the real stack: MiniMax at `low`
  answered a turn in a median of 3.8 s for about $0.00045 (`evals/results/`, 2026-11-17).
- Every turn's system prompt is `mani.md`, then the framework guide built from the registry, then what is known of the
  person (`facts.system_prompt`). The four chat prompts and the body check-in's script it replaced were deleted on
  2026-11-17; the seed switches their rows off (`seed.RETIRED_PROMPTS`).
- Web and mobile do not call this API yet; they run on placeholder data.

## What the service does

- **Auth** (`mani/auth/`): HS256 or JWKS, audience checked, `alg: none` refused. Admin is
  `app_metadata.admin_role == 'admin'` and `user_metadata` cannot grant it.
- **Database** (`mani/db/`): `as_user()` opens a transaction as `mani_service` with the caller's claims set, so RLS
  applies to real traffic. `as_admin()` is the named exception. A turn's writes share one transaction, and no
  transaction is open while the model thinks (`chat/runner.py`).
- **A chat turn** (`mani/chat/turn.py`, run by `chat/runner.py`; the design:
  `../docs/superpowers/specs/2026-11-17-one-call-conversation-design.md`), in order:
  1. The duplicate check, the advisory locks, the pause gate (423 `chat_paused` while a pause runs, see Decisions in
     force), loading the turn's context, saving the rewind snapshot, and the history window within
     `CONTEXT_BUDGET_CHARS`.
  2. With no model call: a tap on a style button gets that style's fixed opener (`turn._open_in_style`); a tap on a
     lead-in button gets the framework's five steps for their style (`turn._explained`), and I need an example its
     worked example (`turn._fixed_step`); their message equal to Mani's last reply gets `greeting.COPIED_BACK` (`turn._copied_back`).
  3. Otherwise exactly one model call. The system prompt is `content/prompts/mani.md`, the framework guide built from
     the registry (each active framework: when it fits, when never to offer it, and each stage's line, purpose and
     when it is answered), the person's onboarding answers, and the summary once messages have left the
     window (`facts.system_prompt`). Then the transcript, their message, and a system message of facts
     (`facts.facts`): their style, Mani's notes from its last turn, the framework running and its next stage, an open
     offer, what was declined or finished, an open safety worry, what code would refuse (`facts.NO_OFFER`), the
     return check after a pause, a recent crisis elsewhere, a tapped button, and a title when one is due.
  4. The reply is `TurnReply` (`chat/reply.py`): `text`, `action` (none, offer, finish, stop, library), `framework`,
     `stage`, `safety` (`level`, `about`, `help_in_place`, `declined`, `symptom_now`, `still_there`, `why`), `notes`
     and `title`.
  5. Code applies it (`turn._apply`): the safety judgment through the one safety rule (`worry.step`), what the reply
     may change of the framework and which buttons show (`decide.decide`), the fixed text where a pause or the check
     after a framework requires it (`crisis.pause_reply`, `crisis.END_CHECK`), and dashes replaced
     (`repairs.without_dashes`). Every other word goes out as the model wrote it.
  6. The message pair, the thread record (`threads.understanding`, `chat/record.py`), the framework row, the safety
     state, a crisis flag and a pause are written in one transaction. A summary that is due is left for after the
     reply (`turn.follow_up_due`).
  When no host answers, a fixed reply goes out instead (`crisis.TROUBLE_REPLY`, or `crisis.CRISIS_REPLY` while a
  worry is open) and nothing else changes.
- **Frameworks** (`content/frameworks/*.md`, seeded to `admin.frameworks`): ABCDE and Thought Reframe are seeded and
  offered (the client's ABCDE document of 2026-10-09; Thought Reframe moved out of `paused/` by muhammad, 2026-10-21).
  The other four are kept in `content/frameworks/paused/`; the seed sets their rows inactive (never deleted, since
  threads and exercises refer to them), and moving a file back up brings it back once it has what the turn reads
  (`seed.missing_for_activation`). After a framework's last stage come the closing choices Keep Chatting, Go to
  Library and Finish for Now. The body check-in (the client's "SOMATIC SECTION OF MANI", paused since 2026-11-05) was
  deleted on 2026-11-17 with its code, script and phases; migration 039 retired any thread left in it, and the
  client's script stays in `docs/client/`.
- **Memory**: none across chats. Each chat stands alone; only the safety check after a pause crosses chats
  (Decisions in force).
- **Exercises**: catalog, completions and signed URLs (`mani/storage.py`). Nothing picks an exercise for a person:
  the pick by a second model call was deleted with the 2026-10-02 flow. `GET /v1/exercises` is the whole catalog, and responses never carry the storage path.
- **Admin**: prompt CRUD with versioning, exercise CRUD, crisis event review, and every
  person's conversations read-only (each full read logged in `admin.thread_reads`). An admin cannot send a chat
  message (`Participant` in `mani/auth/deps.py`). `scripts/grant_admin.py <email>` grants or `--revoke`s it.
- **Account deletion**: `DELETE /v1/account` removes the user and everything they own.
- **Evaluation** (`evals/`): `run_eval.py` scores the turn's replies against ChatGPT's on 14 quality cases and checks
  7 rule cases (`cases.json`), three runs each, judged by `openai/gpt-6.1-sol`; `check_suite.py` runs the 8
  conversations of `suite.json` through the real stack with a model-played person (`drive.py`) and exits 0 only when
  every check passes. See "The evaluation is the gate" in Decisions in force.

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
| POST | `/v1/threads/{id}/messages/{message_id}/follow-up` | the summary a turn left, asked for once its reply is shown (`follow_up_pending`); `read` is always false; a summary that fails stays waiting (`pending`) |
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
| GET | `/v1/admin/threads` | every person's conversations they have written in, newest activity first; `search` by email or user id |
| GET | `/v1/admin/exercise-feedback` | every person's library ratings, newest first; `search` by email or user id |
| GET | `/v1/admin/threads/{id}` | one conversation in full, oldest first; logs the read |
| GET | `/internal/cron/catch-up` | summaries behind and follow-ups the app never asked for (`mani/catch_up.py`); bearer `CRON_SECRET`, no JWT |

## Decisions in force

- **One model call per turn: the model writes every word Mani says and decides what happens next, and code keeps only
  the guarantees below, stated to the model in the facts before the call** (muhammad, 2026-11-17; the first turn back
  after a pause is the one reply code writes too, `crisis.RETURN_CHECK_REPLY`, 2026-11-19). Because the state
  machine around one structured call (a 22-field form with the reply last, code stitching a closing question,
  templates and letter lines into the reply, a second call reading the person after it, about 75,000 characters of
  rules) gave replies that missed the core, forgot between turns, ignored corrections and broke grammar where code
  joined text, and the turn's module took 81 commits in 2.5 months (2026-11-17). Design:
  `../docs/superpowers/specs/2026-11-17-one-call-conversation-design.md`; journal:
  `mani-vault/Journal/flat-replies-were-the-model-2026-11-17.md`. Code guarantees only:
  - the client's fixed pieces, sent whole: the greeting, the style question and openers, the return opener, the five
    steps per style and the worked example, every button label, `crisis.CRISIS_REPLY`,
    `crisis.pause_reply`, `crisis.END_CHECK`, `crisis.RETURN_CHECK_REPLY` and `greeting.COPIED_BACK`;
  - an offer only when it is allowed, as the client's three steps with their buttons (`decide._offer`,
    `decide._answered_offer`);
  - one stage step per turn, and finish only on the last stage (`decide.stage_of`, `decide._moved`);
  - the safety question after a framework when the conversation reached danger (`crisis.END_CHECK`);
  - the declined and finished lists on the thread record (`chat/record.py`);
  - the safety rule, fed by the reply's `safety` fields (`worry.step`);
  - dashes replaced (`repairs.without_dashes`).
  A refused offer is traced (`refused`), never repaired. Tests: `test_a_turn_costs_exactly_one_provider_call_and_
  sends_the_text_as_written`, `test_dashes_are_replaced_and_nothing_else_in_the_text_changes` and
  `test_notes_written_by_one_turn_reach_the_next_turns_facts` in `tests/integration/test_turn.py`;
  `tests/unit/test_decide.py`, `test_facts.py`, `test_worry.py`, `test_taps.py`, `test_record.py`.
- **A turn held for safety changes no framework state and makes no offer, and its facts invite neither: it stays on
  its stage, a tap on Start does not start the set, and no offer is allowed** (2026-11-18). Because the facts told a
  held turn it might move to the next stage, start an open offer or start a tapped set, which code then refused, so
  the reply could say a line code did not follow (2026-11-18). Held: a worry is open or a return check is owed
  (`holding` in `turn._turn`); a worry found in this message guards the turn too (`guarded` in `turn._apply`). The one
  exception is the answer to the safety question after a framework, which may close the set. Someone who taps Start
  during a safety turn taps again once safe (accepted 2026-11-17). `facts.HELD_START`;
  `test_a_held_turn_never_invites_a_move_a_start_or_an_offer_that_code_would_refuse` in `tests/unit/test_facts.py`,
  `test_a_guarded_turn_changes_no_framework_state` in `tests/unit/test_decide.py`.
- **The chat turn runs on DeepSeek V4.1 Flash (1017) at reasoning effort `high`, on the cheapest zero-data-retention
  host (Sail Research) with the most reliable (DeepInfra) as its fallback, within $0.002 a turn, and an empty reply
  gets the one retry any reply that does not parse gets** (muhammad, 2026-11-22; back on this model 2026-11-24 for
  `fixing-directive-in-chat`; effort high, 2026-11-18). Because the acceptance run of 2026-11-22 passed none of its 36
  chats on MiniMax M3.1 Flash, and the gate run of that day had DeepSeek ahead on Supportive and Reflective (4.19
  against 3.82) and Directive (3.78 against 3.22) at $0.00011 a reply against $0.00053, with 2 of 158 calls coming back
  empty (all reasoning), which the client now retries once (`client.NO_CONTENT`;
  `test_an_empty_reply_is_retried_like_any_reply_that_does_not_parse`). Not re-measured on this branch's prompt.
  Earlier, on MiniMax M3.1 Flash at reasoning effort `high`, only on zero-data-retention hosts that run
  its reasoning, within $0.002 a turn** (muhammad, 2026-11-17; effort high and the reasoning hosts, 2026-11-18). Because on the real stack, 20 cases with three runs each, it scored 3.57
  against ChatGPT as 5 for about $0.00045 a turn and a median of 3.8 s, where `openai/gpt-chat-latest` scored 4.07 at
  $0.016 (over budget) and DeepSeek V4.1 Flash scored 3.64 but judged chest pain with arm symptoms `unsure` in 4 of 9
  runs (MiniMax `danger` in 9 of 9); three prompt variants did not move the cheap models past about 3.6, so the gap is
  the model's (2026-11-17). The model, effort and hosts live in the `mani` row (`model_id`,
  `model_parameters.reasoning_effort`, `routing: {only: [modelrun, fireworks, makora], zdr: true}`), from `content/prompts/mani.md`'s frontmatter through `scripts/seed.py`, never in environment
  variables; never the model makers' own APIs or other China-based hosts. A failing host falls back to the next in
  the list. The row's `only` replaces the settings' OpenAI-only default (`Settings.routing`). Accepted: about 88% of
  the chat model's score. Inferact vLLM, Together and Nebius answer this model with no reasoning at all, so they
  were dropped (2026-11-18): since 16:00 UTC that day 87 of 91 live chat calls had landed on Inferact, and at the same
  moment of a replayed chat Makora offered the set 4 of 6 times where Inferact offered 0 of 6 and copied its own last
  reply. When a host is added, check a probe call shows reasoning tokens. `test_the_model_effort_and_hosts_come_from_the_prompt_row` in `tests/unit/test_composer.py`,
  `test_a_prompt_file_carries_its_routing` in `test_seed.py`,
  `test_a_prompt_can_override_routing_without_losing_the_data_policy` in `test_config.py`.
- **A model that always reasons is sent its row's effort, and its output budget includes the reasoning allowance**
  (2026-11-18). Because MiniMax M3.1 Flash reasons on every call with a default effort of max (OpenRouter), and
  `chain` sent it no effort, so every live turn on the rebuild thought at max while the evaluation measured `low`
  (2026-11-18). `chain.ALWAYS_REASONING_PREFIXES` (`minimax/`): such a model keeps its temperature and gets
  `reasoning.effort` and `max_tokens` plus `REASONING_ALLOWANCE_TOKENS`. One live call confirmed the request is
  accepted (4.6 s). `test_a_model_that_always_reasons_is_told_the_rows_effort_and_given_room_to_think` in
  `tests/unit/test_chain.py`.
- **The evaluation is the gate for every change to the prompt or the model** (muhammad, 2026-11-17). Because the
  scenario script counted words, offers and phrases rather than whether a reply was good, and the rebuild needed a
  scored comparison with ChatGPT; 0.15 is about the noise between runs (2026-11-17). `evals/run_eval.py`: 14 quality
  cases from muhammad's 2026-11-17 comparisons and 11 rule cases (`evals/cases.json`), three runs each, scored by
  `openai/gpt-6.1-sol` with a strict JSON schema, four calls at a time, waiting when OpenRouter's in-flight budget
  refuses one (402). The change and the current prompt and model run one after the other in the same session; the
  change is kept only if its Supportive and Reflective overall is no more than 0.15 below and every rule passes.
  Directive is judged with length set aside and reported apart, since its replies are short by design (muhammad,
  2026-11-18). A score from an earlier day is never the comparison. It sends production's request
  (`chain.request_body`, `chain.sampling`; since 2026-11-18, so earlier scores measured a different request), and it
  runs only from the command line. Before a merge, `evals/check_suite.py` runs the 8 conversations of
  `evals/suite.json` through the real stack with a model-played person (`evals/drive.py`, which calls OpenRouter
  directly, never billed as chat) and exits 0 only when every check passes; muhammad reads the rest. Last gate,
  2026-11-18, the client's framework sequence: Supportive and Reflective 3.30 against the baseline's 3.36, rules 32 of
  33 (one Directive close a sentence long, accepted by muhammad); then the prompt's own examples stopped teaching the
  stock phrases: 3.42, none of the phrases in 75 replies, rules 30 of 33 (the model suggested answers on the passive
  wish-not-to-wake case in 2 of 3 runs, judged unsure, so code drops them; one Directive close a sentence long); the
  suite passed 8 of 8 both times.
- **The conversation regression suite (`evals/regress.py`, TC-01 to TC-15) runs by hand only, against a local or
  dedicated test database; its deterministic checks fail it, its judged scores and requirement gaps never do, and each
  run's summary is committed** (muhammad, 2026-11-24). Because manual testing repeated the same conversations, every
  live run spends the client's credit, and comparing runs needs the earlier results. Paused frameworks, the deleted
  body check-in and the retired "offer by the fifth message" are reported as gaps, never asserted. The scenarios are a
  draft from the client's documents awaiting muhammad's approval, and the suite has not yet made a live run.
  `evals/regression/`, `tests/unit/test_regression_checks.py`, `.github/workflows/regression.yml` (manual dispatch)
  and `backend-unit.yml` (every push), `.gitignore` (`evals/results/summaries/`).
- **Directive replies are short and human: two or three short sentences, at most one point and not every reply, a
  few of their own words to show it heard them, then it stays or asks the one question that moves them on (never a
  pick-from-several), never going back over what was said, never saying sorry (it says what they are trying to say
  instead, muhammad, 2026-11-24), and A asks for one specific recent event** (muhammad,
  2026-11-18; two or three sentences and the human voice, muhammad, 2026-11-24, because replies still read long and
  scripted). Because the
  client's sequence document shows Directive's short acknowledgments, and her review of the promotion chat
  (2026-11-18) found Directive stacking four or five points, a three-option question, and an A that bundled the whole
  pattern. The first rule, sentences only, was ignored in every reply: the prompt's other lines (two or three moves a
  reply, 120 to 220 words, 60 to 120 inside a set) said the opposite, so those now name Supportive and Reflective,
  which keep their own length (see the build-up entry below), their possibilities questions and their A. If the eval still finds long Directive replies,
  the next step is code counting sentences and asking once more, not another line. `mani.md`; eval
  `rule-directive-short`, `rule-directive-open-question`, `max_sentences`.
- **Every reading is a possibility, each point is made once, and no causal claim the person hasn't made** (muhammad,
  2026-11-18). Because the client's promotion-chat review found readings stated as fact ("That is the core of it"),
  the same reassurance four times, and "That silence probably reinforced the feeling", which blamed the person. All
  styles. `mani.md` ("What a good reply gives").
- **Inside a set the belief is never argued with before D, and the set opens with one bridge sentence before "A is for
  Activating Event."** (muhammad, 2026-11-18). Because the client's review found Mani disputing at B, leaving D
  nothing new, and the jump into A abrupt. The chat before a set may still offer a fair perspective. `mani.md`
  ("Inside the set of questions"); eval `rule-no-dispute-at-b`, `rule-start-bridge`.
- **In Supportive and Reflective a reply builds with what they have told: early replies reflect and notice one thing,
  the highlight waits until they have said what happened, what it does to them and what it means, and replies grow
  longer** (muhammad, 2026-11-18). Because the client found the highlight came too early and asked for replies that
  grow (2026-11-18). This reverses the 2026-11-17 R73 overrule for these two styles. Directive is unchanged. `mani.md`
  ("How you listen", "How a reply looks"); eval `rule-sr-first-reply-builds`, `rule-sr-first-reply-builds-reflective`,
  `rule-sr-highlight-when-laid-out`.
- **Retired 2026-11-18: suggested answers as buttons** (muhammad, 2026-11-18, the same day). Because muhammad asked
  for them to be removed after testing; the reply no longer carries `options`.
- **When no host answers, or the reply's text is empty, a send or a first message gets a fixed reply, never an
  error; an edit fails instead and changes nothing** (muhammad, 2026-11-17; the edit and the empty text, 2026-11-18).
  An empty text keeps its safety judgment and moves nothing else (`test_an_empty_reply_gets_a_fixed_one_and_keeps_the_
  safety_judgment`). Because a safety turn must never go out with no
  reply, and a first message about danger during an outage must still reach the numbers (2026-11-17); and a failed
  model call on an edit stored the outage reply in place of the original exchange (2026-11-18). The reply is
  `crisis.CRISIS_REPLY` while a worry is open or a return check is owed, otherwise `crisis.TROUBLE_REPLY` (a short
  line with 911 and 988, our wording until the client's). Their message is kept and the reply stored; the safety
  state, the notes and the framework do not move (`turn._unanswered`). A first message no host answers returns 201
  with that reply and keeps its conversation. `runner.run(answer_failure=...)`: true for send and start, false for
  edit. A reply that does not parse is tried once more (`client.MAX_SCHEMA_ATTEMPTS`).
  `test_every_host_failing_on_a_first_danger_message_still_answers`,
  `test_a_fallback_reply_keeps_the_notes_and_moves_no_state` in `test_turn.py`,
  `test_a_first_turn_no_host_answers_still_gets_the_fixed_reply` in `test_threads_api.py`,
  `test_a_failed_edit_leaves_the_original_exchange_in_place` in `test_read_think_write.py`.
- **Columns nothing reads are dropped: a framework's confirm phrases and the thread's message count at Mani's last
  check** (muhammad, 2026-11-18). Because the model writes its own words and no check is made any more, so both were
  dead data (2026-11-18). `supabase/migrations/040_drop_unread_columns.sql`; `scripts/test_db.sh` passes. Still kept
  though nothing writes them: `thread_techniques_offered` and `thread_technique_state.physical_response`,
  `conversation_effect` and `stages_known` (Open decisions).
- **A reply asks a question only when it helps, and never more than one; every open-chat question has a job
  (situation, feeling, belief, wants or a step toward the core and the set, never advice), chosen before the words
  and kept with the question, and in the open chat code cuts every question but the last, and every question after
  a message frustrated with Mani** (muhammad, 2026-11-17; the job, the ledger and the cut, muhammad, 2026-11-24, in
  all three styles). Because Mani re-asked what it had asked and ran interviews with no memory of why it asked, and
  a wording rule alone has not held. The cut deletes Mani's own sentences and adds none; a stage's question, a
  lead-in and a safety question are never cut. `chat/questions.py` (`held_to_one`, `INTENTS`), `TurnReply.question`,
  `facts.question_lines`; `test_an_open_chat_reply_keeps_one_question_and_the_next_turn_hears_what_it_was_for`.
  Earlier: because code that
  held every reply to a closing question in a field of its own joined text the model did not write and broke grammar,
  and muhammad's 2026-11-17 comparisons wanted replies that give something before they ask; this replaces "every chat
  reply ends on one question" (muhammad, 2026-11-10), knowingly. `mani.md` ("when a question helps, ask one question
  that goes deeper", "Never more than one question"); the evaluation scores it. The client has not been told.
- **Retired 2026-11-17: what is explored stays explored, and a message's length decides nothing** (muhammad,
  2026-11-10). Because the code that kept the explored areas and pressed toward the framework is gone; the model
  reads the whole conversation and keeps its own notes (2026-11-17).
- **Retired 2026-11-17: a reading that never lands is visible** (2026-11-10). Because there is no reading after
  the reply any more (2026-11-17).
- **Retired 2026-11-17: the ledger of a framework, shown on every turn** (muhammad, 2026-11-10). Because the stage
  store it was built from is no longer written, and the ledger left the turn's response (approved by muhammad,
  2026-11-17).
- **A scheduled catch-up finishes what the app never asked for** (muhammad, 2026-11-06). Because on Vercel the app
  triggers the work after a reply and a new chat, so a closed tab lost a reading and someone who never taps New chat
  was never remembered. `mani/catch_up.py`, every 5 minutes from `backend/vercel.json` (Vercel Pro): summaries behind,
  follow-ups waiting on a reply quiet for `QUIET_AFTER` (5 min) and given up after `GIVE_UP_AFTER` (1 h), each as its
  person (`Claims.acting_as`). Each job starts at most `catch_up.LIMIT` (10) items a run and stops at `RUN_SECONDS`
  (240), inside the function's 300 s. Nothing failing is retried forever: a follow-up for `GIVE_UP_AFTER` (1 h), a
  summary while its thread had a message in `summarize.CATCH_UP_FOR` (1 day); past that a summary waits for the
  thread's next turn. Work a request has claimed is passed over. Tests: `test_follow_up.py`, `test_queries.py`
  (`due_for_summary`), `test_catch_up.py`, `test_cron.py`.
- **The hosted chat-tester runs as it does locally, Forgot password included, for testing only** (muhammad,
  2026-11-06). Because testers need it now and the safe flow can wait. It is a public Streamlit Community Cloud app
  from the public repo, holding mani-app's Supabase secret key, so anyone with the link can reset any non-admin
  account's password and read that person's conversations, and create accounts that spend model calls. Accepted for
  test accounts only; before any real person signs up, remove the Forgot password tab and the secret key from the
  hosted copy (sign-up works with the publishable key alone, since mani-app auto-confirms) and make the app private.
- **When the chat-tester cannot read `GET /v1/crisis/resources`, the pause pop-up names the backend's US reference
  lines (988, 911) instead of no number** (muhammad, 2026-11-24). Because a crisis pop-up with no number to call is
  worse than a fallback list, and the backend's US lines are long-standing public services. Every network failure
  reaches callers as `ApiError` (`BackendUnreachable`), so the pop-up and the pause check never crash the page.
  `chat-tester/crisis_pause.py` `FALLBACK_RESOURCES` (kept in step with `backend/mani/chat/crisis.py` `RESOURCES`),
  `test_the_pop_up_names_the_us_lines_when_the_help_numbers_cannot_be_loaded`.
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
  definer functions to `mani_service`, hides `threads.understanding`, `rewind_snapshot`, `pending_follow_up`,
  `vague_streak`, a column migration 040 dropped since, and `memory_folded_at`, which 041 dropped, from
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

- **Retired 2026-11-17: one home per rule, and no reply shape is a formula** (muhammad, 2026-11-06). Because the
  four chat prompts it ordered were replaced by one, `mani.md`, which holds the rules it kept (2026-11-17).

- **Retired 2026-11-17: every question earns its place, with Mani's reasoning before each reply and its progress
  fields** (muhammad, 2026-11-06). Because the progress and exploration fields and the code that held the move to
  the set are gone; `mani.md` holds how Mani listens and when it offers (2026-11-17).
- **Retired 2026-11-17: Plan Next Step after the questions** (muhammad, 2026-11-06). Because the script that
  carried its button and the picture that kept what they asked for are deleted; `mani.md` says to help with what
  they chose after a finished set (2026-11-17).

- **Safety is the model's judgment of whether anyone is in danger now, held by the conversation; no phrase locks
  anything, and danger that continues with nothing in place pauses the chat (a symptom in the body only on a refusal
  of the help).** Because a concern must outlive the reply that raised it and must not give way on a refusal (manasa's
  safety test, 2026-11-06), and because sign lists with a rule per kind of danger held concerns open against what the
  model understood: "I mean my workplace", "my friend is with me and stops me", a symptom that has passed (muhammad's
  and Lolly's chats, 2026-11-10). Spec: `docs/specs/0007-safety-follows-what-they-said/`. Since 2026-11-17 the
  judgment is the turn's own reply (`TurnReply.safety`), the rules below are unchanged, and the phrase screen is
  deleted (the one-call design, approved by muhammad).
  - The reply's `safety` judges their message against the whole conversation: `level` none, unsure or danger; `about`
    themselves, someone_else, from_someone or body; `help_in_place` (help called or on its way, someone with them or
    coming, the means away from them, or moved away from the danger); `declined` when they refuse the help offered,
    never for pushing back or doubting; `symptom_now` yes, no or unsaid for the body; `still_there` when their message
    itself says the danger goes on; and a line of `why`, never traced and stored only as the reason of a pause it
    starts (`chat_pauses.reason`). What each means is `mani.md`'s Safety section, watched by the evaluation's rule
    cases. `worry._DANGER` names `danger` as the rules' `now`.
  - `threads.safety` is clear, unsure or danger (migration 036). Code applies the judgment with rules of its own
    (`safety.after`): a refusal never lowers a concern; only the model raises a concern about a person to danger, so
    an answer it judged unsure stays unsure however often Mani asked, and from danger the model judged about a person
    (`safety.HELD`) only a judgment of none of that same worry lowers it, so an unsure read of another kind is not held
    by it (`worry_about`; chest pain, then "I wish I weren't here") (muhammad, 2026-11-20, after production paused a
    person who was lonely and crying after "unsafe with my family" with no danger ever judged; this ends the hold of
    2026-11-16 that turned a second unsure into danger; `test_worry.py`, "a worry the model only ever judged unsure
    never pauses"). A symptom in the body
    that they have not said stopped is danger now, and when the model judged it lower code adds the call-now line after
    Mani's text, once per body worry, also on a thread already in danger of another kind (`safety.danger_of`, `crisis.BODY_EMERGENCY`; muhammad, 2026-11-18: a possible medical
    emergency gets "call emergency services now" every time, over-triggering accepted, after MiniMax held chest pain
    with a strange left arm at unsure in 7 of 30 runs; `test_a_body_worry_that_has_not_stopped_is_danger_now`,
    `test_a_body_worry_the_model_held_lower_still_gets_call_now`). Once a concern settled, only their newest message
    reopens a body worry (the stroke chat, replayed 2026-11-11).
    Mani's question counts as asked only for the kind of danger it was about (`worry.step`, the kind kept as
    `worry_about` while a worry is open and forgotten when it settles; the held-back run, 2026-11-16). A worry that
    settles is kept on the record as `safety_settled` (`worry.record_after`).
  - While a worry is open the facts say so, no offer is allowed and the turn changes no framework state (see "A turn
    held for safety"); a running framework waits on its stage. The message limits do not apply while it is open.
    How Mani answers danger (asking plainly what they mean, not asking the same question again, saying how to reach
    help, asking once whether pain in the body is happening now) is `mani.md`'s Safety section.
  - The first turn judged danger is recorded in `admin.crisis_events` with whose danger it is, never their words
    (`turn._record_danger`, `threads.mark_crisis`). `threads.crisis_at` (migration 037) keeps when it was last flagged,
    and `recent_crisis` counts its 30 days from it. An edit restores the state (`rewind`).
  - **When danger continues with nothing in place, the chat pauses for `CRISIS_PAUSE_SECONDS` (default 30); a refusal
    is required only for a symptom in the body; nobody is signed out, no conversation takes a message, the Library
    and every conversation stay readable, and the backend is the whole lock** (muhammad, 2026-11-13, and 2026-11-14 for
    the refusal; 2026-11-23 for the 30 seconds and for reading the conversation after closing the pop-up; this replaces
    "nothing locks" of 2026-11-06 and "help refused is the only block" of 2026-11-11). Because once a crisis is certain
    Mani must stop rather than go round a loop of "please get help", and the production chat of 2026-11-14 never
    paused in 11 turns: "i want to kill myself", about to act right now, nobody with them, nobody called, every
    question answered honestly and so never `declined` (2026-11-14).
    The rule is `worry.step`: the state after is danger, nothing is in place, and the danger went on after Mani
    had answered it (the state before was danger) or, once Mani had asked about this kind of worry, the answer says
    it again (muhammad, 2026-11-16: asked, they say "I just want to die", and the help screen comes, "every time").
    Never a pause on the first danger message of a clear conversation: Mani's own reply comes first. A danger about
    the body pauses only when this turn's read has the symptom happening now and they refuse the help (`declined`;
    the controller's ruling, 2026-11-13, because a doubt paused 5 of 6 body chats live), at the level code holds it,
    so a symptom the model judged unsure counts as danger (muhammad, 2026-11-23: refusing an ambulance for chest pain
    that was still happening never paused when the model said unsure); a danger of no known kind
    needs `declined` too. Accepted: a `help_in_place` misread can pause someone who has help (2026-11-14).
    On the pausing turn a `chat_pauses` row (migration 037: thread, `started_at`, `ends_at`, `reason`, `checked_at`) is
    written in the turn's transaction, the reply is `crisis.pause_reply(about)` in place of the model's text (whom
    Mani worries for and the help that fits: 911 and 988 for themselves or an unknown kind, 911 for someone else, from
    someone and the body; Crisis Text Line stays in `RESOURCES` for the API), the response carries `paused_from` and
    `paused_until`, and no summary is left for after it. One gate, `auth/deps.require_chat_open` (`ChatOpen`), answers
    423 `chat_paused` with `error.details.paused_from` and `paused_until` on `POST /v1/threads`, send, edit and
    follow-up, and the turn checks again under the message lock before its duplicate lookup (`turn._arrival`), so a
    retry or another tab cannot slip past. The profile and the opening carry `chat_paused_from` and
    `chat_paused_until`; reading conversations, the crisis resources and the Library stay open. A pause's reason is
    loaded by the turns of any of the person's conversations (`threads.load_turn_context`), never by the profile, and the person's own role has no SELECT on it. An edit never undoes a pause.
    **Every conversation asks after a pause, until they say they are all right** (muhammad, 2026-11-13; the
    conversation the pause began in too, 2026-11-19: it stops asking once they have said it in another). Because a
    person who comes back and chats in another conversation, new or older, must not bypass the check (2026-11-13).
    **A pause owes the check only while it ended within `RECENT_CRISIS_DAYS` (30)** (the controller's ruling,
    2026-11-13). Because without a bound every old unchecked pause would make every conversation ask, however long ago
    (2026-11-13).
    **Wherever they come back, Mani asks about what they faced, with what the pause rested on** (muhammad,
    2026-11-16). Because someone who came back in a new conversation was met by the style's opener and a question with
    no details, and the client's blocker test had Mani agree to keep talking before safety was established
    (2026-11-16). The return check is for the person's latest pause that has run out (`pause.return_check`); the facts
    give its reason and tell Mani to ask how things are with it before anything else (`facts._pause_lines`). In a new
    conversation the question is the opening: `GET /v1/threads/opening` gives `greeting.RETURN_OPENER` for every style
    while a pause is owed (`pauses.owed`), the style tap is answered with it at no model call (`turn._open_in_style`),
    and their first message is its answer. Each conversation asks once per pause (`return_check` on the record). An
    answer judged none clears that conversation and marks the pause checked (`pauses.mark_checked`), after which the
    other conversations stop asking; see "After a pause" for when an answer pauses again. The chat-tester shows the
    client's blocker as she drew it on 2026-11-16, word for word ("Blocker.", "Chat is temporary unavailable", "For
    your safety, chat is paused for <the pause's own length>.", the Library line, the 988 line, Get help now and Go to
    library; muhammad: exactly as drawn, with the length the pause has (30 seconds as of 2026-11-23), and the 911 line and the live timer at the bottom
    stay though she did not draw them; the timer says "Chat resumes in", without "while you reach out", her safety
    test, point 43); the numbers come from the resources by `kind`, Get help now calls the support line (our choice),
    the page runs again at 0:00, and its cross leaves the person's conversation to read, with the composer, the edit icon
    and the suggested replies off and a banner with the same timer until the pause ends; Go to library opens the
    Library (`chat-tester/crisis_pause.py`, `test_closing_the_pop_up_leaves_the_conversation_to_read_with_no_way_to_write`,
    `test_a_paused_chat_shows_only_the_clients_pop_up_and_the_library_still_opens`). The pop-up was not looked at in a
    browser.
    `config.crisis_pause_seconds`; `chat/pause.py`, `chat/worry.py`, `db/pauses.py`, `routers/threads.py`,
    `auth/deps.py`; `tests/unit/test_pause.py`, `test_safety.py`, `test_worry.py`, `test_crisis_resources.py`; in
    `test_turn.py` `test_overdose_on_the_first_message_gets_manis_reply_and_the_next_message_pauses`,
    `test_a_paused_person_is_refused_before_anything_is_paid`,
    `test_a_return_check_answer_that_is_fine_marks_the_pause_checked`; in `test_threads_api.py`
    `test_every_chat_route_refuses_while_paused`, `test_the_library_and_profile_stay_open_while_paused`,
    `test_the_opening_asks_about_a_pause_that_ran_out_until_they_have_answered`.
  - After a framework's last stage, a conversation that reached danger asks about safety once, as a reply of its own
    (`crisis.END_CHECK`), before the closing choices; their answer is a safety turn, and the reply that settles it
    carries the close and the choices, whatever action the model chose (muhammad, 2026-11-11; the final review,
    2026-11-18, `test_a_settled_answer_to_the_safety_question_closes_the_framework_whatever_the_action`). It keys on `danger_reached` on the record, set when a
    turn ends in danger, not on the crisis flag (the audit, 2026-11-13); the record keeps `safety_end_check` as asked
    or done (`decide._moved`, `turn._updates`). Conversations that reached danger before 2026-11-13 hold no
    `danger_reached` and get no end check (no backfill). `test_finish_after_danger_asks_the_safety_question_first`,
    `test_after_the_safety_question_a_settled_answer_closes_the_framework` in `test_decide.py`,
    `test_a_finish_after_danger_sends_the_end_check_then_the_close` in `test_turn.py`.
  - Still the client's: the approved safety wording and resources (`crisis.RESOURCES` holds three US reference
    numbers and the Find A Helpline directory until then, and `pause_reply` names only numbers from it), and whether
    anything alerts a person.
  - `declined`, `symptom_now` and `still_there` on MiniMax are held by the suite's overdose, chest, dodge and
    return-check conversations (`evals/suite.json`); the return check needed one sentence in `mani.md`, that a safe
    answer to the question about a pause judges none (2026-11-17).

- **Retired 2026-11-17: the body check-in, paused since 2026-11-05** (muhammad, 2026-11-05: "chat -> framework
  (not somatic)"). Because it was deleted with its code, script and phases rather than kept paused beside a turn
  with no moments; migration 039 retired threads left in it (2026-11-17; muhammad to confirm, Open decisions).

- **A turn reads, thinks, then writes: no database connection is held while the model thinks** (muhammad,
  2026-11-05). Because a turn held its transaction across the model call (6 to 30 s) and `client._record` took a
  second connection inside it, so ten turns in flight on one instance emptied its pool of 10, and with no acquire
  timeout the instance hung. `chat/runner.py` runs `turn.send` twice: the read, in a transaction that rolls
  back, ends where the turn asks the model (`runner.Model` records the request and the thread's version, its message
  count and newest message id); the model is called holding nothing; the write runs the same steps in a fresh
  transaction under `threads.lock` and answers them with that reply. A turn that never asks the model (a style
  button, a lead-in button or I need an example, a duplicate, their own message sent back) commits in the read, and one refused by a pause writes nothing.
  At the write, a message id
  already stored returns that turn; a thread whose version moved, or a reply asked for in another shape, is refused as
  `CONFLICT` 409, retryable, "Mani is still answering your last message. Please try again." The write rebuilds from the
  thread as it is then. The edit route takes the turn back in both passes (`runner.edit`), so a failed edit, the
  model's failure included (2026-11-18), leaves the original. A retry with the same
  `client_message_id` waits in process for the first (`one_at_a_time`, `mani/one_at_a_time.py`) and pays nothing; one that reaches
  another instance pays once more and still stores one turn. The pre-model reads run twice (a few queries, about
  150 ms cross-region). `tests/integration/test_read_think_write.py` (`test_no_connection_is_held_while_the_model_thinks_on_a_send_or_an_
  edit`, `test_the_same_message_on_two_instances_at_once_stores_one_turn`); [[read-think-write-2026-11-05]].
  The rule holds everywhere and is enforced (muhammad, after the 500-person load test, 2026-11-05): a task holding a
  pool connection may not take a second one (`pool._acquire`), call the model (`client.complete`) or read the prompt
  cache (`cache.load`, which reloads on its own connection); each raises `RuntimeError`, so a test finds it. Because the
  turn's read still called `cache.load()`, which on a stale cache took a second connection under a process-wide lock:
  at 500 people every connection was held by a read waiting on it, and 3,694 of 3,708 sends failed `busy`. The runner
  reads the prompts first and passes them in (`turn.send(config=...)`). Summaries (`summarize.update`) read, call the
  model, then write only onto what they read. In one process a second summary waits for the first
  (`mani/one_at_a_time.py`).
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
  `MINUTE_MESSAGE_LIMIT` 10 is counted from the messages they sent, beside `DAILY_MESSAGE_LIMIT`
  (`turn.within_limits`); neither applies while a safety worry is open or a return check is owed. Since 2026-11-17 no
  phrase screen reads a message before the limit, so a crisis in a message past it is not recognised, and the refusal
  itself says where to get help (`crisis.IN_DANGER`; muhammad to confirm, Open decisions).
  `test_a_call_that_finds_every_slot_taken_is_refused_quickly_as_busy`,
  `test_past_the_minute_limit_a_turn_is_refused_with_where_to_get_help`.
- **Every wait on a turn adds up under 90 s** (muhammad, 2026-11-05). Because the chat-tester gives up at 90 s and a
  person sooner; Vercel Hobby allows 300 s. Worst case, each wait at its limit: JWKS fetch on a key-cache miss 5
  (`JWKS_TIMEOUT_SECONDS`; PyJWT's default was 30), pool acquire for the read 5, the read's statements about 0.5, a
  model slot 2, the model 65 (`CHAT_BUDGET_SECONDS`, the first attempt's cost row inside it), the last cost row's
  acquire 5, the write's acquire 5 and statements about 0.5: about 88 s. A statement is capped at 10 s, so a database
  slow on every statement could still pass 90. The JWKS fetch is blocking, and stays off the event loop because
  `auth/deps.current_user` is a plain `def` dependency, which FastAPI runs in its threadpool.
- **Only the backend creates a thread or records an offered framework** (migration 031, 2026-11-05). Because with
  INSERT on `threads` a user's own token, through PostgREST, could create a row with any `understanding`,
  `rewind_snapshot`, `memory_folded_at` or `message_count`, which the backend reads back as
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
  conversation; a first turn that fails with an error soft-deletes the one it created, and one no host answers keeps
  it with the fixed reply (2026-11-17). `GET /v1/threads/current` returns the
  conversation last written in, or none. The lists, `most_recent` and the admin list show only conversations with a
  message the person wrote (`threads.WRITTEN_IN`; a style tap does not count), so greeting-only threads already stored
  are hidden, not deleted. `threads.create` always inserts a new conversation. The greeting says "good to see you again" only
  when an earlier conversation was written in (`turn.has_written_in_earlier_thread`).
  `tests/integration/test_threads_api.py`: `test_opening_writes_nothing`,
  `test_the_first_message_creates_the_thread_with_its_opening`, `test_a_retried_first_message_returns_the_same_thread`,
  `test_a_first_turn_no_host_answers_still_gets_the_fixed_reply`.

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
- **Retired 2026-11-17: a body check-in turn and the reading after a reply think at `low`, every other chat turn
  at `medium`** (muhammad, 2026-11-05). Because both are gone and the chat turn runs on MiniMax at `low` (see
  "The chat turn runs on MiniMax M3.1 Flash") (2026-11-17).
- **Mani's text is not streamed to the person; the call is.** Because 75% of a chat call's wait is thinking before
  the first token, and only about 1.6 s p50 comes after it, so streaming the text would show the reply about 1.6 s
  sooner for the cost of a streaming API in the backend and both frontends (muhammad, 2026-11-05;
  `docs/latency-report-2026-11-05.md`, section 7). Revisit if the time after the first token grows.
- **Retired 2026-11-17: a reply follows Lolly's cadence, and the check is her barometer** (2026-10-29). Because the
  check and the prompts that held the cadence are gone; `mani.md` holds what it kept (2026-11-17).
- **The person can edit their last message: it and Mani's reply are replaced, and the thread state returns to what it
  was before that turn.** Because muhammad wants ChatGPT's edit for the chat-tester (2026-11-03): replace, last message
  only, also inside a framework, chat-tester only for now. Every turn saves the state it will overwrite (title,
  the thread record, the safety state, the framework row) in `threads.rewind_snapshot` (migration 029; migration 039
  cleared the snapshots taken before the one-call turn);
  `POST /v1/threads/{id}/messages/{message_id}/edit` deletes the pair through `delete_last_message_pair`, restores the
  snapshot and runs the new text in one transaction (`chat/rewind.py`). Refused: a message sent by
  tapping an option, the style tap, a message already inside the thread summary. A crisis thread is edited wherever a
  message can still be sent: the edit has no crisis rule of its own; while a pause runs the edit route's gate and the
  send that runs the new text both refuse as `chat_paused`, and the whole edit rolls back (muhammad, 2026-11-10: a
  thread flagged once refused every edit as "paused" while it still took messages). The crisis record in `admin.crisis_events` outlives an edited message. Tests:
  `test_editing_after_a_finishing_turn_restores_the_framework_state` in `test_turn.py`,
  `test_a_failed_edit_leaves_the_original_exchange_in_place` in `test_read_think_write.py`.
- **A message is cleaned to its visible text before anything reads it, and an empty one is refused with what to do.**
  Because a zero-width character inside "kill myself" turned into a space in the safety screen and the phrase was no
  longer matched, and the same hid a typed `[ctx]` block from its guard (muhammad, 2026-11-04). `text.clean_message`
  folds full-width and compatibility letters, drops zero-width, control and unassigned characters, makes every space a
  plain one and collapses runs; `SendMessageIn` and `EditMessageIn` apply it. The phrase screen it first protected is gone (2026-11-17); the model
  still reads only the visible text.
  Nothing visible left gives 422 "Write a message first. It can't be empty or only spaces."; over 4000 characters gives
  "That message is too long..." (`main.py` `_what_to_fix`). Not covered: look-alike letters from other alphabets.
  Tests: `tests/unit/test_text.py`, `test_an_empty_or_too_long_message_is_told_what_to_do`.
- **Retired 2026-11-17: Mani runs the chat like a therapist runs a session, with Lolly's role-played session as
  its example** (2026-10-29). Because the prompts and reply fields it described are gone; `mani.md` says Mani
  thinks like an experienced therapist (2026-11-17).

- **Retired 2026-11-17: Mani looks for the core, and the check is about the core alone** (2026-10-28). Because the
  picture's core and the check are gone; `mani.md` defines the core and offers once it was said back and not
  corrected (2026-11-17).

- **Retired 2026-11-17: every turn speaks from one voice prompt beside a prompt per moment** (2026-10-27). Because
  every turn reads one prompt, `mani.md`; the seed still switches the retired rows off (`seed.RETIRED_PROMPTS`)
  (2026-11-17).

- **Retired 2026-11-17: Mani asks before the body check-in** (2026-10-27). Because the body check-in is deleted
  (2026-11-17).

- **Retired 2026-11-17: a framework that stops helping offers to step out, named by code and the reply together**
  (2026-10-27). Because the stall count and fit fields are gone; `mani.md` says to offer to step out, and
  `action: stop` records the set declined (`decide._moved`) (2026-11-17).

- **Retired 2026-11-17: the chat's note carries the core, what they want, the insights given and what recent
  replies added** (muhammad, 2026-11-16). Because code writes no note any more: Mani's own notes come back each
  turn (see "Mani's notes") (2026-11-17).
- **Retired 2026-11-17: an observation is the ordinary chat reply, and a bare acknowledgement never comes twice in
  a row** (muhammad, 2026-11-16). Because the reply kinds and the check that counted them are gone; `mani.md`
  asks every reply to give something they did not say themselves (2026-11-17).
- **Retired 2026-11-17: something new and painful holds the move to the set for one reply** (2026-11-16). Because
  the form that held the move is gone; `mani.md` holds an offer while their message brings something new and
  painful (2026-11-17).
- **After a pause, only a message that itself says the danger is still there, or that the model reads as danger,
  pauses again, and the answer to how things are is read literally** (muhammad, 2026-11-16; 2026-11-23 for a danger
  read: "I took more pills" in answer used to wait one more message when the read did not also mark `still_there`).
  Because in his local chat a new conversation opened with the
  question about the pause, he answered "fine", the read held the pause's reason against it ("saying you're fine
  doesn't clarify whether you're away from them") and the chat paused again (2026-11-16). The facts give the reason as
  what the pause rested on earlier (`facts._pause_lines`). The first message back never pauses and gets Mani's reply
  (`Phase.ASKING` in `worry.step`); the answer to it pauses only when the reply's `safety.still_there` says
  the danger is still there or its level is danger, with nothing in place, and an unclear answer gets Mani's reply and the message after it decides. `mani.md`
  judges a safe answer to the question about a pause as none (2026-11-17, after the suite's return-check conversation
  held "i'm ok now, my sister is here and i'm safe" as unsure). The sequences "the first message back after a pause
  never pauses, whatever the read reports" and "their answer to how things are pauses only when it says the danger
  is still there" and "an answer read as danger pauses even when the read does not say it is still there" in
  `test_worry.py`,
  `test_a_return_check_answer_that_is_fine_marks_the_pause_checked` in `test_turn.py`.
- **A conversation's safety moves by one rule, a worry's kind lasts only while the worry is open, and their word that
  they are all right, in any conversation, settles every worry held from before it** (muhammad, 2026-11-19, the
  redesign of the crisis pause). Because the kind of a worry and the question asked about it sat in two record keys
  that nothing cleared, so after a settled body worry a later danger with no stated kind was held to the body rule and
  never paused, and the conversation a pause began in kept its danger, asked again and could pause with no word from
  Mani after they had said elsewhere that they were all right (2026-11-19). The rule is `worry.step` over `Standing`
  (the state, the worry's kind in `worry_about`, and the phase: ordinary, asking the return check, answering it);
  `worry.standing` settles a held worry whose conversation's last message came before the latest pause's
  `checked_at`; `pause.return_check` is the one rule for who is owed the question. A settled worry's kind is forgotten, so a later
  danger with no stated kind needs a refusal like any other (muhammad kept this, 2026-11-19). muhammad, 2026-11-20,
  after an edge-case pass: an unsure worry they never answer closes on the second message in a row read as no
  concern (`worry.CALM_TO_CLEAR`, record key `worry_calm`; an answer to a question Mani asked directly, the return
  check or the one after a set, still settles at once), because one calm message can be a changed subject and a
  worry nobody closes held every later turn; a first message back read as danger gets `crisis.RETURN_DANGER_REPLY`
  in place of the question; the pausing turn sends Mani's own reply and then the pause line; a retry of a message
  answered with the fixed words of a failed call runs the turn again from the state before it
  (`crisis.UNREAD_REPLIES`, `turn._arrival`); a copy of Mani's reply with words of theirs added is read like any
  message (`text.COPY_ADDED_WORDS`). The prompt lines that go with these have not been through the evaluation.
  Changes that follow
  from the redesign and wait for him to keep or overrule them: a conversation asks with the latest pause's reason, whichever conversation the pause began in; the
  answer to the question a new conversation opens with is a held turn, so no limit refuses it. `test_worry.py` (each
  sequence was first run through the rules as they stood), `test_pause.py`; in `test_turn.py`
  `test_the_conversation_paused_in_stops_asking_once_they_said_elsewhere_they_are_all_right` and
  `test_the_answer_to_the_question_a_new_conversation_opens_with_is_never_refused_for_a_limit`;
  `test_worry_migration.py`.
- **Retired 2026-11-16 (superseded) and 2026-11-17: every conversation turns from understanding to helping, and
  code names the turn and the help move** (muhammad, 2026-10-27). Because the state and note lines that carried
  it are gone; `mani.md` says what Mani does when they ask what to do (2026-11-17).

- **Retired 2026-11-17: a framework's stages speak in the chat's voice from a stage prompt of their own**
  (muhammad, 2026-10-27). Because the stage prompt is gone; `mani.md`'s "Inside the set of questions" holds it:
  the set gives the direction, never a script (2026-11-17).

- **Retired 2026-11-17: one picture of the person, shared by the chat and every framework** (muhammad,
  2026-10-27). Because the picture is gone; the model reads the whole conversation and keeps its own notes
  (2026-11-17).

- **Retired 2026-11-17: only a declined offer holds the next check back** (muhammad, 2026-10-27). Because no check
  is made; a set declined or finished is never offered again (see "When to offer a set") (2026-11-17).

- **An admin reads every person's conversations in full and takes part in none; each full read is logged.**
  Because the client and we review beta users' chats for their cadence, which a crisis-only browser could not show
  (muhammad, 2026-10-26; replaces the note "scope the conversation browser to unresolved crisis threads"). The list
  carries no content; `GET /v1/admin/threads/{id}` writes `admin.thread_reads` in the read's transaction. The send
  endpoint refuses an admin token (`test_an_admin_can_read_conversations_but_not_send_a_message`), the chat-tester
  shows an admin only the read-only viewer, and its on-page password reset refuses an admin account, since
  anyone who reaches the page can use it. `tests/integration/test_admin_threads.py`, migration 026.
- **Retired 2026-11-17: before a framework, Mani is its own conversation in the cadence of Lolly's two ChatGPT
  chats** (muhammad, 2026-10-26). Because there is one conversation in one call, with no separate chat route
  (2026-11-17).

- **Retired 2026-11-17: Mani reads their whole message against what it already understands and says what is new**
  (muhammad, 2026-10-22). Because the prompt rules and fields it named are gone; `mani.md` holds it ("Every reply
  gives them something they did not say themselves") (2026-11-17).
- **Mani's notes are written in the same call as the reply and handed back on the next turn; nothing runs after a
  reply but the summary, which the app asks for** (muhammad, 2026-11-17). Because the reading of the person by a
  second call after the reply landed a median 18.8 s after it (p90 29.8 s, 2026-11-10 to 16), ran in production only
  from the catch-up job since the mobile app never asked for it, and made the record a second writer the turn could
  not see (2026-11-17). `TurnReply.notes` (under 150 words) is stored on the thread record and given back in the next
  turn's facts; a fixed reply keeps the notes it had. Since 2026-11-05 nothing runs after a response (Vercel stops the
  instance once it is sent; muhammad chose the app's own request, 2026-11-05; it works the same on AWS). A turn whose
  summary is due stores it in `threads.pending_follow_up` (migration 032; `{message_id, summary}`, keyed by Mani's
  reply, set or cleared by every turn, `turn.follow_up_due`), says `follow_up_pending`, and the app posts
  `/v1/threads/{id}/messages/{reply id}/follow-up`, which runs the summary (`turn.follow_up`); the response keeps its
  fields, with `read` always false. The request claims the work for `FOLLOW_UP_CLAIM_SECONDS` (120), so a second
  request meanwhile does nothing; a summary that fails stays waiting (`pending`), and a request that died frees its
  work when the claim runs out. It stops at `FOLLOW_UP_DEADLINE_SECONDS` (90), inside the claim. Interim (muhammad,
  2026-11-06): this is the app asking, for as long as the backend runs on Vercel; on a stateful host (Render, AWS)
  delete the endpoint, `follow_up_pending` and `pending_follow_up`, and run the summary in the process after the
  response. Only the chat tester calls it today; `web/` and `mobile/` are not wired to the API. The call link and the
  trace are database writes only, awaited side by side before the turn's response (`turn.link_call`,
  `turn.record_trace`). Work the app never asks for is done by the catch-up. `test_notes_written_by_one_turn_reach_the_next_turns_facts` in `test_turn.py`,
  `test_the_notes_from_the_last_turn_are_handed_back` in `test_facts.py`, `tests/integration/test_follow_up.py`,
  `tests/unit/test_follow_up_endpoint.py`, chat-tester `test_follow_up.py`.
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
  make a thinking-heavy call faster (the median stays about 9.7 s) and a cut attempt is probably billed. Since 2026-11-17 the
  chat turn runs at the `mani` row's `low`. `pytest.ini` ignores one
  third-party warning the stream emits (`field_name='parsed'`). Not measured live (needs muhammad's yes: his
  next chat turns, then read `admin.llm_calls`). `test_a_call_that_sends_nothing_for_too_long_is_cut_and_tried_once_
  more`, `test_a_call_silent_twice_fails_as_too_slow_after_two_tries_only`, `test_a_streamed_reply_records_its_usage_
  and_generation` in `tests/unit/test_client.py`.
- **Every call but the chat turn goes only to OpenAI, its fastest endpoint first, never a pinned order and never
  flex; a chat reply on an OpenAI model asks for OpenAI's priority tier** (`openrouter_providers: ["openai"]` with
  `sort: latency`, muhammad, 2026-10-26; the tier, muhammad, 2026-11-05; the chat turn left OpenAI on 2026-11-17,
  see "The chat turn runs on MiniMax M3.1 Flash"). Because the priority endpoint (`openai/fast`) ran at 109 tokens a second against the standard
  endpoint's 65, and thinking before the first token is 75% of a chat call's wait, for about $0.06 a day more at the
  traffic of 2026-11-03 to 05 (chat cost $0.18 in that window at the standard price, which priority doubles;
  `docs/latency-report-2026-11-05.md`, sections 7 and 8). A purpose `chat` call on an OpenAI model (`chain.request_body`) sends `service_tier: "priority"` and
  `provider.only: ["openai", "openai/priority"]` (`Settings.routing(priority=True)`; OpenRouter's docs name
  `openai/priority` and `openai/fast` as one endpoint). OpenRouter tries the priority endpoints first and falls back to
  the default ones in the list, so a turn is never failed for want of priority capacity and is billed at the endpoint
  that served it; the explicit slug is there because a base slug never matches a tier endpoint, and nothing else is
  allowed, so never Azure, Bedrock or flex; `data_collection: deny` stays; no `provider.order`, which turns off sticky
  routing. `summarize` stays on the default tier. `OPENROUTER_CHAT_SERVICE_TIER=default`
  turns it off with no change to code. Evidence after deploy: `service_tier` is `priority` on `GET /api/v1/generation`
  for chat generation ids (`scripts/llm_call_providers.py` prints the endpoint; see the report's section 7 for the
  call). `test_only_the_chat_reply_asks_for_the_priority_tier_and_each_purpose_keeps_its_own_key`,
  `test_the_priority_tier_is_switched_off_by_configuration` in `tests/unit/test_client.py`,
  `test_the_priority_tier_is_asked_for_only_on_openai_models` in `tests/unit/test_chain.py`. Because Azure's content filter,
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
- **Retired 2026-11-17: ABCDE's D asked as two questions, with code remembering which is next** (muhammad,
  2026-10-21). Because the stage store and its gaps are gone; the model writes each stage from its purpose and
  `ready_when` in the framework guide (approved by muhammad, 2026-11-17).
- **Retired 2026-11-17: a message that asks something never moves a framework stage** (muhammad, 2026-11-05).
  Because `mani.md` says to answer what they just said first, and code no longer reads a question mark (approved
  by muhammad, 2026-11-17).
- **Retired 2026-11-17: "ready" is a confirmation, never a deepening** (the client meeting, 2026-11-05). Because the
  heart value and the move it gated are gone; `mani.md` says when to offer (2026-11-17).
- **Retired 2026-11-17: a yes to the body check-in always gets the client's Step 1** (muhammad, 2026-11-04).
  Because the body check-in is deleted (2026-11-17).
- **When to offer a set is the model's judgment; a set declined or finished is never offered again in the
  conversation, and code refuses an offer while a set runs or is open, after one was finished, for a set they
  declined, for an id not in the registry, and while a safety worry is open** (muhammad, 2026-11-17; never again,
  2026-11-16). Because counts of messages, a check before the offer and pushes from code made offers come too early,
  too late or never (on 2026-11-16 muhammad's Directive chat had to type "framework?" at its 23rd message), while the
  spike's live tests showed sensible timing with the rule in the prompt (2026-11-17); and because manasa's tests of
  2026-11-16 had ABCDE offered again two replies after she turned it down and again after she finished it (R91, R92).
  `mani.md` "Offering the set of questions": offer once the core was said back in an earlier reply and not corrected,
  and their latest message does not correct, ask, show frustration or bring something new and painful; never as a way
  out of frustration. Retired with it (approved by muhammad, 2026-11-17; the prompt holds both): "an offer only after
  Mani has said the core back", with the stored count of the last check (dropped by migration 040), and "code never
  sends an offer in a reply that reports frustrated". The facts say before the reply when an offer would be refused
  (`facts.NO_OFFER`), so a refusal should not happen; one that does is traced as `refused`, and the reply's text goes
  out with no buttons (`decide._offer`). R91's "unless the user requests it" is not kept: code refuses a declined set
  even when they ask for it (Open decisions). There is no code floor on timing; if it goes wrong, the fix is a fact
  (such as how many exchanges have passed), not a rule in code.
  `test_an_offer_while_a_framework_runs_is_refused_and_shows_no_buttons`,
  `test_an_offer_of_a_declined_framework_is_refused`, `test_an_offer_of_an_unknown_framework_is_refused`,
  `test_an_offer_while_a_safety_worry_is_open_is_refused` in `test_decide.py`,
  `test_no_offer_is_allowed_while_one_is_open_or_after_a_framework_was_finished` in `test_facts.py`,
  `test_a_declined_framework_is_never_offered_again` in `test_turn.py`.
- **Which framework fits comes from the client's Framework Selection Cheat Sheet line (`central_indication`) and each
  framework's contraindications, both in the framework guide; the model chooses** (muhammad, 2026-10-13, R15; the
  contraindications, 2026-11-18). Because the client's cheat sheet (2026-10-13) says to select only once the
  underlying concern is understood, never from the opening feeling, and gives one line per framework; and because the
  rebuild's guide had left out "Never offer it when:", so the model was no longer told, for example, never to reframe
  an established fact or feed an OCD checking loop (2026-11-18). No framework id is in code: the reply names
  `framework`, and code checks only that it is in the registry and allowed (`decide._offer`). The paused files carry
  their cheat sheet line too, and the seed refuses to activate a framework missing what the turn reads
  (`seed.missing_for_activation`: each style's five steps, the worked example, each stage's line, `purpose` and
  `ready_when`), so
  bringing one back is a content change. `facts.framework_guide`;
  `test_the_guide_says_when_never_to_offer_each_framework` in `test_facts.py`,
  `test_a_framework_stage_without_its_purpose_cannot_be_seeded_active` in `test_seed.py`.
- **Every chat stands alone: nothing from an earlier chat reaches a new one except the safety check after a pause**
  (muhammad, 2026-11-18). Because a tester's memory held every scenario tested and pulled old themes and loops into
  new chats, and muhammad wants each chat separate even when the person returns with the same issue (2026-11-18). The
  safety check is the return question after a pause and the "go gently" line for a recent worry
  (`chat/pause.return_check`, `TurnContext.recent_crisis`); the onboarding profile is not a chat. No chat call opts into
  OpenRouter's response cache, and its prompt-cache key is that chat's own. Migration `041`;
  `test_a_new_chat_carries_nothing_from_an_earlier_one_but_the_safety_check` in `tests/integration/test_queries.py`,
  `test_a_chat_call_never_opts_into_openrouters_response_cache` in `tests/unit/test_client.py`.
- **The offer is the client's three steps: a lead-in the model writes, then her five steps, then the choice to
  start** (muhammad, 2026-11-18). Because the client's sequence document (2026-11-18,
  `docs/client/messages/2026-11-18-framework-sequences.md`) shows how a framework is meant to run, and the newest client
  document wins (2026-11-18). The reply sets `action: offer` and `framework`; its text is the lead-in: the belief said
  back, that a belief can feel true without being a fact, and a question about how they could test it, never naming the
  set (`mani.md`, an example per style). Code adds Not sure / Show me how / Give me a tool (`repairs.lead_in_buttons`).
  Any of them sends the client's five steps for their style word for word, with the ready question, and Start ABCDE /
  I need an example / Talk more first, with no model call (`turn._explained`); I need an example sends the worked
  example (`stages.offering.example`; ABCDE's from her document, Thought Reframe's ours). A typed answer to the lead-in
  gets Mani's reply, then the five steps and their buttons (`Decision.show_steps`). Talk more first sets the offer
  aside for now, so it may come back; only a clear no (`action: stop` on an open offer) declines it. The earlier
  offer (Mani's own sentence with Try it / Tell me more / Keep chatting) is overruled, recorded in
  `docs/client/requirements.md`. `test_the_offer_runs_lead_in_steps_example_then_start`,
  `test_a_typed_reply_to_the_lead_in_gets_the_reply_then_the_steps`,
  `test_talk_more_first_lets_the_offer_lapse_and_it_may_come_back` in `test_turn.py`.
- **Retired 2026-10-27 (superseded) and 2026-11-17: one style file per thread in the system prompt** (muhammad,
  2026-10-12). Because one prompt, `mani.md`, carries all three styles, and the facts name the conversation's
  style (2026-11-17).
- **Every button of a framework is the client's, set by code**: Not sure / Show me how / Give me a tool under the
  lead-in, Start <name> / I need an example / Talk more first under the steps, Stronger / More focused / Still a bit
  tired after the last stage, Keep Chatting / Go to Library / Finish for Now at the close (`greeting.py`,
  `repairs.py`); the model never writes them. Because the client's sequence document (2026-11-18) names them, and
  muhammad kept the closing three (2026-11-18). A tap is matched by its label; Start carries the framework's id, so it
  starts only the offer still open. `test_the_offer_carries_the_clients_buttons_at_each_step` in `test_repairs.py`.
- **Retired 2026-11-17: an offer the window allows is never dropped for a question beside it** (muhammad,
  2026-10-12). Because code no longer reads the offer's text; the buttons follow `action: offer` (2026-11-17).
- **The model writes each stage, and code only holds the order: one stage step per turn, finish only on the last
  stage** (muhammad, 2026-11-17). Because the stage walk owned by code (a store of each stage's status, fallbacks to
  the client's lines, a reply split into its answer, the letter line and the stage's opening) felt like a
  questionnaire, held about 2,000 lines of code, and still asked again what they had said (2026-11-17). The reply's
  `stage` is the stage whose question it asks; code stores it but never more than one past the stored stage, and the
  starting turn opens the first stage only, even when the chat touched it, as the client's sequence asks every letter
  on its own reply (`decide.stage_of`; 2026-11-18). A stage of another framework changes nothing. `action: finish` on
  the last stage opens the feelings check: Mani acknowledges the new belief and asks how they feel now, with Feel stronger /
  Feel more focused / I'm not sure yet (the words changed 2026-11-24, muhammad: "Still a bit tired" put a feeling in their
  mouth), and the next answer closes the set with Keep Chatting, Go to Library and Finish for
  Now and records it finished (phase `feelings_check`, `decide._moved`; 2026-11-18). The closing reply answers warmly
  and asks whether they want to think about a practical next step, since feeling better is not the situation solved
  (the client's promotion-chat review; muhammad, 2026-11-18; `facts._running_line`). E ends on the new belief, with no
  "one thing they'll do" (muhammad, 2026-11-18). `action: stop` records the set declined. A set starts on a tap on
  Start for the offer still open (`taps.tap_event`), or on a typed yes after its five steps when the reply moves to
  its first stage. The facts name the stage in force, the next stage's line and the one-step
  rule (`facts._running_line`). Each stage opens with its letter line ("A is for Activating Event."), written by the
  model (muhammad, 2026-11-17); code does not check it at runtime, because that would be code editing text, and the
  evaluation's rule case `rule-stage-line` checks it. How a stage goes (answer what they said first, never ask again
  what they told, never narrate, the new belief in their own words) is `mani.md`'s "Inside the set of questions".
  Their own last reply sent back still gets `greeting.COPIED_BACK` with no model call (R67).
  `test_a_stage_two_ahead_is_held_to_the_next_one`, `test_the_starting_turn_opens_the_first_stage_only`,
  `test_finish_before_the_last_stage_is_ignored`, `test_stop_records_the_framework_declined` in `test_decide.py`;
  `test_after_e_the_feelings_check_then_the_closing_buttons` in `test_turn.py`.
- **Retired 2026-11-17: a framework walk never skips and helps when they don't know** (muhammad, 2026-10-21).
  Because the walk is gone; `mani.md` holds both (every stage in order, a gentle reading when they don't know),
  and only `action: stop` ends a set (2026-11-17).
- **ABCDE is offered from the client's ABCDE document** (muhammad, 2026-10-09; Thought Reframe joined it 2026-10-21).
  Because the client's ABCDE document of 2026-10-09 is what we build to, and ABCDE's stages give the questions a
  target (2026-10-09); why the other four are paused: reason unknown, muhammad to confirm. Each stage opens with its
  letter and name ("A is for Activating Event."), as the document shows (muhammad agreed 2026-10-13, R12), and
  nothing but a short acknowledgment in Directive comes before it. The five steps are the client's sequence
  document's list in the person's style with its ready question, word for word (`stages.offering.explain`). Of each stage the turn reads its line (`intro`), `purpose` and `ready_when`; the
  other stage fields are unread (Open decisions). `tests/unit/test_abcde_content.py`.
- **Retired 2026-11-17: the stage store** (`thread_technique_state.stages_known`, 2026-10-13). Because the walk
  that wrote it is gone; the column stays, left empty, until muhammad approves dropping it (2026-11-17).
- **The transcript is the memory within a thread** (muhammad, 2026-10-13, after the architecture reviewer's
  comparison of seven designs). The model sees the whole thread up to `CONTEXT_BUDGET_CHARS` (40,000 characters
  of message content, `messages.for_context`); past it the oldest messages leave in blocks of
  `CONTEXT_DROP_BLOCK` (20), so what is shown, and its cached prefix, stays the same between drops, and only then
  is the thread summary sent and refreshed (`needs_summary` when more messages have left than any summary
  covers; the cron backstop uses the same rule). Because the 20 message window was inherited, a thread reaches
  ABCDE's E at about message 23 to 30, and every store built to outlive the window had to guess ahead and went
  stale or thin (the seed, the understanding record). The budget is the rollback lever. The app's thread view
  has its own tail (`routers/threads.OPENING_TAIL`). The chat model's host receives the whole thread,
  the same open data protection question as before. `test_the_model_sees_the_whole_thread_until_the_budget_then_
  loses_whole_blocks` in `tests/integration/test_queries.py`.
- **`threads.understanding` is the thread record: Mani's notes, the sets declined and finished, and the safety keys
  the pause rules read** (muhammad, 2026-11-17). Because the record had grown into a picture, readings and stores that
  code wrote and the model was asked to fill, and it already holds JSON, so reshaping it in place needs no new column
  (2026-11-17). Shape: `{notes, questions, declined, finished, return_check, safety_settled, danger_reached, worry_about,
  safety_end_check}` (`chat/record.py`; migration 042, 2026-11-19, folded `danger_about` and `asked_about` into
  `worry_about`). Migration 039 rewrote every row: declined and finished rebuilt
  from `thread_technique_state`, the safety keys kept, notes empty, every other key dropped, rewind snapshots cleared,
  and a thread left at the body check-in retired and counted finished. A set declined before a later offer replaced
  that row is not recoverable, so such a thread could be offered it once more (accepted 2026-11-17). Written only by
  `mani_service` and hidden from `authenticated` (migration 034); never logged; sent only in its own thread; deleted
  with the thread. With `AI_DEBUG_MODE` on, a turn returns it as `understanding`, and the chat tester shows the notes,
  declined and finished under "What Mani knows". `tests/unit/test_record.py`,
  `tests/integration/test_record_migration.py`, `tests/sql/test_grants.sql`.
- **No phrase lists judge the conversation** (muhammad, 2026-10-09). Because literal phrase matching cannot
  read a paraphrase, so its judgments were silently wrong whenever people worded things differently
  (2026-10-09). Code holds no list of what people say, of feeling words, of self-judgments or of pain words; since
  2026-11-17 the safety phrase screen is gone too, and safety is the reply's own judgment. The rules live in
  `mani.md`, and the reply reports its judgments in typed fields (`action`, `stage`, `safety`). What code still
  matches is not about meaning: a tap against the labels of the buttons it showed (`taps.find_tapped_prompt`), their
  message against Mani's last reply (`text.copies_last_reply`), and dashes. A paused framework moved back brings no
  phrase list with it (2026-10-12).
- **Retired 2026-11-17: each reply says what is new and how it changes Mani's reading, as a guess they confirm or
  correct, with one question that tests it** (muhammad, 2026-10-26). Because the prompts and scenario flags that
  held it are gone; `mani.md` holds what it kept (2026-11-17).
- **Retired 2026-11-17: Mani's voice as a shared shape plus the style file, with the check's layout and the stage
  options laid out by code** (muhammad, 2026-10-22). Because code no longer lays out or adds to the reply; the
  model writes every word and `mani.md` holds the voice (2026-11-17).
- **Retired 2026-11-17: the context block explains itself** (2026-10-09). Because the block is gone; the facts are
  plain sentences sent after their message (`facts.facts`) (2026-11-17).
- **An open offer is read from the database, not from the buttons on screen.** Because an offer can stay open
  with no buttons showing, and a typed yes to it then started nothing (2026-10-09). The offer row stands at the lead-in
  (`offering`) or the five steps (`steps`); a tap on Start starts it only while it is open (`taps.tap_event`), and a
  typed yes starts it after the steps when the reply moves to its first stage (`decide.decide`). A lapsed offer (its
  row retired, phase null) is no longer open: an old button starts nothing and a new offer may come (the final review,
  2026-11-18, `test_an_offer_they_moved_past_is_no_longer_open_and_its_old_button_starts_nothing`).
  `test_start_starts_only_the_framework_on_the_offer_that_is_still_open` in `test_taps.py`,
  `test_a_typed_reply_to_the_lead_in_gets_the_five_steps_and_the_start_buttons` in `test_decide.py`.
- **Retired 2026-11-17: "It hit me so hard" is not violence** (2026-10-08). Because the phrase screen it corrected
  is gone (2026-11-17).
- **chat-tester resets a password on the page**: email and new password, set through the Auth Admin API with
  no email. Because the test tool should need no mail setup, accepting that the page stays non-public
  (2026-10-07); the seven day session: reason unknown, muhammad to confirm. Anyone who can reach the page can reset any ordinary account, so it stays non-public; an admin account is refused, because it reads every conversation (2026-10-26). A browser session
  is remembered for seven days.
- **Also settled: OpenRouter only, asyncpg not PostgREST, the `public` and `admin` split, the `mani_service` role,
  three security definer write functions, no streaming.** Settled with them: the deterministic safety screen as the
  only thing that locks a thread (superseded 2026-11-06, when nothing locked, and 2026-11-13: no phrase locks, and
  danger that continues with nothing in place pauses the chat, see the safety entry; the screen itself was deleted
  2026-11-17), and in process routing.
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
2. **The one-call turn needs its migrations and seed in the same release.** `supabase db push` for 039 (reshapes every
   thread's record and clears rewind snapshots) and 040 (drops two columns), then `scripts/seed.py`, which seeds the
   `mani` row with its model and hosts and switches the retired prompt rows off; the turn refuses to load without the
   `mani` row (`cache.REQUIRED_PROMPTS`). 040 and 041 (drops the stored per-person memory for good) run only after
   the code that no longer reads them is deployed: code from before 2026-11-18 reads `threads.check_at_message_count`
   and selects from `admin.user_memory` on every turn, so either one ahead of the deploy fails every chat. Done on
   hosted project `aipgficduzufstilndbw` after the PR #58 deploy: 039–041 pushed and seeded (2026-11-18). 042 (folds
   two record keys into `worry_about`, clears rewind snapshots) runs only after the code that reads `worry_about`
   is deployed; until then the code from before it reads `danger_about` and `asked_about`. 042 is on hosted
   (muhammad confirmed 2026-11-24). The library branch's
   `042_exercise_audio_optional.sql` (`feat/library-descriptions`, stashed) becomes 043 when that branch comes back;
   muhammad's local dev database already records version 042 for it.
3. **Rate limit and cost ceiling.** `DAILY_MESSAGE_LIMIT` exists and defaults to 0 (off); muhammad sets it in the
   environment. `MINUTE_MESSAGE_LIMIT` is 10, and neither applies while a safety worry is open. There is no per user
   cost ceiling; `llm_calls.spend_since()` is what one would read. A retried send with the same `client_message_id`
   returns the first reply for free.
4. **Crisis resources are reference numbers, US only.** `crisis.RESOURCES` holds 911, the 988 Suicide & Crisis
   Lifeline and Crisis Text Line (muhammad, 2026-11-13); `crisis.pause_reply` names 911, and 988 for themselves or an
   unknown kind; `crisis.TROUBLE_REPLY` and the limit refusals name 911 and 988; the pop-up shows 988 (call and text)
   and 911; none names Crisis Text Line;
   the pop-up also links Find A Helpline (findahelpline.com), listed for every country. The specifications refer to an
   approved protocol and helpline list and contain neither. Needs the client's list, by country; until then the pause
   text gives US numbers to everyone, wherever they are.
5. **The OpenRouter balance and the chat's hosts.** The chat runs only on six zero-data-retention hosts; when none
   answers, every turn gets the fixed reply. A low balance limits parallel calls and returns 402: keep the account
   topped up and watch for 402 errors (the design's risks, 2026-11-17).
6. **Migrations are not run by anything.** `supabase db push` is manual.
7. **The catch-up cron needs Vercel Pro.** `backend/vercel.json` calls `/internal/cron/catch-up` every 5 minutes,
   with `CRON_SECRET` set on the project. Vercel Hobby refuses to deploy a cron that runs more than once a day, so the
   file must not reach a branch a Hobby project deploys from.
8. **`CORS_ORIGINS` must name the deployed web origin**, or `web/` gets no browser response. Mobile is
   unaffected.
9. **Pool and load.** Set the hosted `DATABASE_URL` to the transaction pooler: host
   `aws-0-ca-central-1.pooler.supabase.com`, port **6543** (today 5432, the session pooler), same user and database.
   Then `supabase db push` for migration 031. Load-tested offline only (Latest measurements): one instance served
   100 people with no errors; at 500 the database held and 30% of sends were refused by the 100 model-call slots.
10. **The backend's database role.** `001_initial_schema.sql` grants `mani_service` to `postgres`. If the
    deployed `DATABASE_URL` connects as anything else, `set local role mani_service` fails. Grant it to that role,
    never to `authenticator`.
11. **Email confirmation is not enforced** and **app attestation is absent.** Confirmation needs
    `enable_confirmations` in Supabase and SMTP; do not read `email_verified` from the token, because the user can
    write it. Attestation layers on after the rate limit, in front of the chat endpoint only.

## Open decisions for muhammad

From the one-call rebuild (the design's "Calls made" and the build's flags, 2026-11-17 and 18), each with the answer
I recommend:

- The body check-in is deleted rather than kept paused. Recommended: confirm; if the client wants it back, rebuild it
  as an action of the turn.
- `threads.understanding` is reshaped in place rather than replaced by new columns. Recommended: confirm.
- The follow-up endpoint stays for the summary only, with `read` always false. Recommended: confirm until the backend
  moves to a stateful host.
- The evaluation's pass mark: no drop of more than 0.15 overall against a side-by-side run, and every rule passes.
  Recommended: confirm.
- Summaries and transcription stay on `openai/gpt-6-luna` through OpenAI: should zero data retention
  cover them too? Recommended: yes, as a change of its own.
- The stage letter lines are checked by the evaluation, not by code at runtime. Recommended: confirm.
- Conversations in progress keep their declined and finished lists, rebuilt by migration 039; a set declined before a
  later offer replaced the row can be offered once more. Recommended: accept.
- A message past the day's or the minute's limit is refused with "If you're in danger or thinking about hurting
  yourself, call 911 now, or call or text 988." (`crisis.IN_DANGER`), since nothing reads it for danger first.
  Recommended: confirm.
- The framework files' stage fields no turn reads (`explore`, `reach`, `listen_for`, `question_bank`, `if_unclear`,
  `picture`, `new_view`, `first_gap`, `title`, `carries_case`, `confirm`, `missing`). Recommended: delete them from the
  files; the client's documents in `docs/client/` stay the source.
- `thread_techniques_offered` and `thread_technique_state.physical_response`, `conversation_effect` and
  `stages_known` are no longer written. Recommended: a migration dropping them, with the chat-tester's read of the two
  outcome columns removed in the same change.
- R91 lets a declined set come back "if the user requests it"; code now refuses a declined set even when they ask.
  Recommended: keep the stricter rule and tell the client.
- In 1 of 3 suite runs MiniMax offered ABCDE to an anxious person who had asked three times for "one simple thing to
  try" and was pointed to the library each time ("library only" for exercises). Recommended: keep library only, and
  add this conversation to `evals/suite.json` so any change is measured.
- MiniMax is an open-weight model from a Chinese lab, served by Western zero-data-retention hosts; the client has not
  been asked. Recommended: tell her before real traffic.

Earlier:

- R2's 4 s median (2026-10-14): the rebuild's evaluation measured a median of 3.8 s a turn on MiniMax at `low`
  (2026-11-17); measure it live and tell the client.
- Tell the client (2026-11-17): inside a set, Mani goes one stage per reply; a stage the chat already answered is said
  back in one sentence and the next stage's question follows, never "Is that right?".
- Tell the client (2026-10-08): "overwhelming" was removed from the Structured Problem Solving description,
  since every offer showed a feeling the person had not named; Supportive and Reflective questions were
  written for the 26 stages whose three styles were identical (the client's wording is kept as Direct, or as
  Reflective for ACT `present`). Have them review the new lines. (The offer buttons are now the client's own, from
  her sequence document of 2026-11-18.)

- The client's crisis resources and safety wording (point 4 above).
- Tell the client (2026-11-17) how an offer comes now: once Mani has said the core back and it was not corrected,
  with no check before it and no count of messages; the offer is where they confirm or correct (R1, R14, R30, R33),
  in every style, and have them read about five real Supportive and Reflective transcripts.
- Tell the client (2026-10-13): by their own cheat sheet, their sample conversation is Structured Problem
  Solving, which is paused, so it gets ABCDE or Thought Reframe for now (R15).
- Tell the client: when a person asks Mani to pick, it offers one small draft step to accept
  or change, which the Behavioral Activation specification's "must not choose the activity" does not allow
  as written.
- Tell the client: a person who cannot say what to do is offered up to three options at the first
  "I don't know". Both depart from the literal Structured Problem Solving example.
- Panic with no action in sight: the overview sends it to DBT STOP, the STOP specification is written around an
  action about to be taken. The client's call.
- Whether a crisis turn should hand off to an exercise. Left out on purpose; do not add it as a missing branch.
- The three styles still differ little in length and question rate. Schema field order was the lever that worked
  for openers; more prose rules did not.
- Revisit the grief veto (Behavioral Activation after loss words) with real transcripts.

## Open engineering

- **Re-gate the evaluation after the 2026-11-18 changes:** the guide's contraindications (a longer prompt), MiniMax's
  effort now sent, and `run_eval` building production's request. The last gate (3.62, all 21 rules, 2026-11-17)
  measured a different request, so a shift may come from the request, not the code.
- **Production is Vercel Hobby functions in iad1, with the database in ca-central-1.** Work started after a response
  was lost there: it suspends or ends the function (Vercel's `waitUntil` is Node and Edge only). Nothing runs after a
  response any more (2026-11-05); the app asks for the summary (see "Mani's notes" in Decisions in force). The rest of
  this entry is the evidence from before that: 15 of 49 `understanding` calls of
  2026-11-01 to 05 timed out at 61 to 335 s against a 60 s wait, background calls spent p50 6.3 s between OpenRouter
  finishing and our row being written (chat: 0.33 s), and both memory-fold retries never wrote a row, so the person's
  picture and memory are being lost (`docs/latency-report-2026-11-05.md`, sections 5 and 9). Every database round trip
  also crosses from iad1 to ca-central-1. Kept on Vercel for now by muhammad, 2026-11-05. The fix is a container host
  near ca-central-1 (the `Dockerfile` is ready) or a queue for the background work.

- **Hosted and local schemas match** as of 2026-10-07, checked read-only: the same migrations, columns,
  enums, functions and RLS policies, and the same prompts, frameworks and exercises (only seed timestamps
  differ). The production deployment is `45543ed`, the head of `main`. What prod's environment variables
  hold is not readable, so those are unchecked. Migrations 037, 039 and 040 have run only locally since.
- **Migration numbers were reused across the reverted branches.** `011` was both
  `technique_state_holds` and `technique_outcome_stopped`; `013` was both `llm_call_decision` and
  `llm_call_facts`. Reviving any of those branches collides again.

- **Redesigns the rebuild deferred, for muhammad** (its /simplify pass, 2026-11-18): one object for the turn's
  situation instead of 17 keyword arguments through `_turn`, `_apply`, `facts` and `decide`; `Decision` carrying what
  this turn declined or finished instead of the full lists; the end check as its own pending safety question instead
  of setting `threads.safety` to unsure; the safety rules taking the reply's `Safety` directly instead of translating
  danger to now; buttons recognised by a structured kind instead of lowercased labels; one settings override instead
  of setting `MINUTE_MESSAGE_LIMIT` before import (the pytest conftest, `check_suite.py`); one threads UPDATE per
  turn; the successful `llm_calls` row written off the critical path; the context window cut in SQL; the thread's
  version read from the loaded context; the limits checked only in the read pass; the summary refreshed one block
  early; one helper to dump and load prompts.
- **LangChain's `include_raw` prints a Pydantic serializer warning on every structured call.**
- **Generated TypeScript types** for `web/` and `mobile/` from the OpenAPI schema, with a CI gate. No CI exists.
- **Admin audio upload.** The 30 seeded exercises come from `content/exercises/` through
  `scripts/seed_exercises.py`; there is no upload route, and the admin exercise CRUD takes an existing
  `audio_path`.
- **A worker process** for summaries, for when there is more than one instance.
- **Model-call capacity at 500 people.** One instance's 100 slots run out (Latest measurements, measured when each
  turn also held a slot for a reading after it, which is gone). Either more instances (Vercel adds them on its own;
  each has its own 100), or a higher `MODEL_CALLS_IN_FLIGHT` once OpenRouter's rate limit for the key is known.
  Unmeasured on Vercel and on the one-call turn.
- **A `busy` 503 or a slot 429 logs at ERROR or WARNING per request**, and 5xx goes to Sentry with a traceback. Under
  load that is one report per refused request; consider logging them without `exc_info`.
- **`GET /v1/admin/models`**, which the prompt editor's model dropdown needs.
- **`threads.vague_streak`** is granted to the backend and written by nothing; the pacing it belongs to is
  designed, not built.
- **`appropriate_when` and `not_when`** in the framework files are read by nothing (each file says so).

## Latest measurements

**Since 2026-11-17 the gate for every prompt or model change is `evals/`** (`run_eval.py` side by side,
`check_suite.py` before a merge; see "The evaluation is the gate" in Decisions in force). The measurements below are
history from the turn it replaced.

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

Taken 2026-10-01 with the earlier eval harness, since removed. The scenario script (deleted 2026-11-17) replaced it;
its first run was to be the next baseline. Re-measure after any change to prompts, framework content or the offer rules.

- Reached an offer: 36 of 36 conversations (grief had been 1 of 9). First offers at message 2 to 4.
- Redrafts (the loop is gone since 2026-10-12): 7% of replies across scenarios, 17 to 19% on the hardest
  chat (a colleague, an embarrassing meeting). Those are the turns that now go out as first written, and
  `Turn.checks` counts the three kinds that matter; read it in the next scenario run.
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
