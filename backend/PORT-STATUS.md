# Port status

What the backend does today and what is still open. Stack notes: `.claude/BACKEND.md`. Database rules:
`.claude/SUPABASE.md`. **Update this file in
the same change as the work.**

## Status, 2026-10-01

- The TypeScript to Python port is complete. FastAPI is the only thing that touches the database.
- Tests: `pytest` runs 451 passed, 4 skipped (the four symmetric-token auth tests, which skip on a
  JWKS-configured project).
- Database: 17 migrations (001 to 010 and 018 to 024), 15 tables (8 `public`, 7 `admin`), 6 frameworks and 5 prompts seeded.
  `admin.exercises` holds the 17 library exercises from `content/exercises/`, with their audio in the
  private `exercises` bucket (`scripts/seed_exercises.py`). A hosted project does not exist yet.
- Models: `openai/gpt-6-luna` for chat and for summaries (`mani/config.py`), routed only to Azure or
  OpenAI, the fastest endpoint first. It is a reasoning model: it takes no `temperature` on any provider and reads
  `reasoning_effort` instead, so `mani/llm/chain.py` sends the sampling parameters an ordinary
  chat model takes only to models that accept them. A prompt row names its own effort in
  `model_parameters.reasoning_effort` and `mani/config.py` holds the default for the calls that have
  no row of their own; `mani_base` is on `medium` (muhammad, 2026-10-22, for comprehension over the 2026-10-12 `low` that cut latency) and so is the exercise pick that
  follows it, while `summarization` and `memory_fold` are on `high`. Effort is billed: measured against Azure,
  `high` spent 26 reasoning tokens where `low` spent 0, about three times the cost of the same call. Every endpoint keeps `data_collection: deny`, so
  training use stays refused, but OpenAI now serves a turn whenever it is faster, not only when Azure is
  down, so a larger share is processed by a second company - a data protection question that is open, not
  settled (muhammad accepted Azure and OpenAI, 2026-10-14).
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
  2. Which framework fits, and whether one fits yet, is the model's call from the Framework Index. Code owns only when an offer may come (on the answer to Mani's check, `context.check_open`, `context.may_check`) and the safety screen.
  3. `composer.py` builds the system prompt with the one style file the thread chose, and `context.py`
     builds the `[ctx]` block: style, offer timing, the stage in progress, what is stored for each stage
     and what this reply's text is for. Nothing in code classifies what the person said: whether a reply is vague, a correction or
     a wish only to be listened to is the model's reading (`response_format.md`, reasoning).
  4. One model call (`mani/llm/`, LangChain on OpenRouter) returns a structured reply: `reasoning`, the answers
     that decide the moment (`check_answer`, `offer_answer`, the stage fields), then `text`, then `understanding_update`,
     `heading_toward`, `style`, `check`, `offer`; on the answer to a check, `heading_toward` and `offer` come before `text`.
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
  7. Crisis, the reply, the framework state, what Mani understands of them and the summary are written together.
- **Frameworks** (`content/frameworks/*.md`, seeded to `admin.frameworks`): ABCDE and Thought Reframe are seeded and
  offered (the client's ABCDE document of 2026-10-09; Thought Reframe moved out of `paused/` by muhammad, 2026-10-21). The other four are kept in `content/frameworks/paused/`; the seed
  sets their rows inactive (never deleted, since threads and exercises refer to them), and moving a file back up
  brings it back. ABCDE ends on E and then the shared body check-in below (muhammad, 2026-10-09: the check-in
  is asked). An offer comes only on a clear yes to Mani's check of its understanding, which may come from
  the person's second message, in every style (spec 0006). The shared body check-in comes from `content/prompts/somatic.md`
  and is the client's document "SOMATIC SECTION OF MANI" (2026-10-16), sent word for word in one voice (muhammad,
  2026-10-22). **The body check-in is the client's six steps, owned by code (`mani/chat/body.py`):** Step 1
  straight after the framework's last stage, with Chest, Stomach, Head, Somewhere Else and No Tension (muhammad,
  2026-10-22 later: the question that asked first was removed, and No Tension is the way out), one of the nine
  exercises sent whole with the check for change (Feel Better / Feel the Same / Feel Worse), the fixed reply, the
  overall question (Yes, It Helped / Somewhat / No, Not Really), and Keep Chatting, Go to Library and Finish for Now.
  The phases are `somatic_check` (only when a place is asked about, see the decision below), `somatic_body`,
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
  `scripts/fold_idle_threads.py` or `GET /internal/cron/fold-summaries` behind `CRON_SECRET`.
- **Exercises**: catalog, completions and signed URLs (`mani/storage.py`). A completing framework picks one
  exercise from the whole active catalog with one bound tool call (`mani/llm/tools.py`): the framework's own
  exercises are listed first, and the pick sees the person's last three messages and the issue Mani
  understands (`threads.understanding`). `GET /v1/exercises` is the whole catalog, and responses never carry the storage path.
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

- **Mani reads their whole message and says back what runs through it, with the name they gave the problem** (muhammad,
  2026-10-22). Because in his Directive chat about a boss who does not lead, Mani mirrored one clause ("your boss doesn't
  seem to understand the work you show him") and dropped the headline the person named, "lack of leadership"; the mirror
  rule ("what matters", "never hand their whole message back") and the problem step's "who, what, how often" both
  select, and nothing says what to keep. Cut and replaced, not added: `mani_base.md` `how_you_talk` and `core issue`,
  `response_format.md` first reasoning step, `context.py` `understanding_next`, `schema.py` `issue` and `core_issue`. Not
  measured live (needs muhammad's yes, replay of that turn); [[direct-questions-have-no-target-2026-10-09]].
- **A turn is one chat call at effort `low`, never a second to fix a draft** (muhammad, 2026-10-12). Because the
  client's R2 asks for no excessive latency, a turn waited on a reasoning model at `high` and up to two more
  full calls whenever a draft broke a rule (a median of 12.6 s and 41 s at worst, 2026-10-07), and the reply
  already carries its own written reasoning. Code shapes the reply instead of asking again: the reply's shape
  is picked from the database each turn (`schema.reply_for`), so while no offer may be made it has no offer
  field, the step through a framework is code's (`walk.py`), and `repairs.apply` strips what remains. The checks that need another call to fix are logged, not
  asked for again, so how often each happens is known. The one scoped extra call is the exercise pick at the end
  of a framework, at the chat row's effort. `test_a_turn_costs_exactly_one_provider_call` and the
  `reply_checks` tests in `tests/integration/test_turn.py` hold it. Not yet measured live (needs muhammad's yes).
- **A chat reply is streamed: a call silent for 15 s is cut and tried once more, and one attempt has a deadline of
  30 s** (`chat_first_token_seconds`, `chat_deadline_seconds`, 2026-10-21; the deadline since 2026-10-14). Because
  `medium` effort makes some turns think 15 to 30 s before the first token (70 percent of output tokens were hidden
  reasoning, p50 9.7 s, 3 of 161 calls timed out), and a flat deadline around a blocking call could only fail them.
  muhammad kept `medium` on purpose. `chain.build` streams through `langchain-openai`'s `astream`, whose
  `stream_chunk_timeout` (set to `chat_first_token_seconds`; background calls keep `llm_timeout_seconds`) ends a
  silence between chunks, keepalives not counting; `client.complete` folds the stream into the one reply it used to
  get, records the cut attempt as its own `timeout` row, and retries once, sharing `MAX_SCHEMA_ATTEMPTS` with a
  malformed reply and a provider blip. Past the deadline or after the second silence the turn fails as `LLM_TIMEOUT`,
  retryable, "Mani took too long to answer. Please try again."; nothing was written, so a resend is safe. It does not
  make a thinking-heavy call faster (the median stays about 9.7 s) and a cut attempt is probably billed; if timeouts stay
  above about 1 percent, `low` effort for plain conversation turns is the next lever. `pytest.ini` ignores one
  third-party warning the stream emits (`field_name='parsed'`). Not measured live (needs muhammad's yes: his
  next chat turns, then read `admin.llm_calls`). `test_a_call_that_sends_nothing_for_too_long_is_cut_and_tried_once_
  more`, `test_a_call_silent_twice_fails_as_too_slow_after_two_tries_only`, `test_a_streamed_reply_records_its_usage_
  and_generation` in `tests/unit/test_client.py`.
- **Chat calls go to the fastest Azure or OpenAI endpoint, never a pinned order and never flex**
  (`openrouter_providers` with `sort: latency`, muhammad, 2026-10-14). Because the pinned `order: ["azure",
  "openai"]` was carried from the previous system, never chosen for speed: an order turns off OpenRouter's load
  balancing and falls back only on an error, and the base slug `azure` covers three regions, two of them with a
  p99 over two minutes on OpenRouter's own figures (`azure/eu` 6.3 s). Base slugs never match the tier endpoints
  (`openai/flex`, `openai/fast`). Every call records OpenRouter's `generation_id` (migration 024), and
  `scripts/llm_call_providers.py` resolves it to the endpoint that served it, so a slow turn is traced, not
  guessed. A timeout has no id (no reply came back); match it by time on OpenRouter's Activity page. If slow
  turns persist, the next step is streaming with a first token deadline, not hedged requests (see
  `mani-vault/Journal/provider-tail-latency-2026-10-14.md`). `test_routing_sends_a_turn_only_to_azure_or_openai_
  fastest_first` in `tests/unit/test_config.py`, `test_each_call_records_the_generation_that_served_it` in
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
- **The body check-in asks about a place only at its start, after a framework's last stage, and only when what Mani
  found before the framework points to one** (muhammad, 2026-10-21). Because a feeling that usually sits in the body
  makes the general question ("Where are you noticing any tension?") personal; it must never interrupt chat or a
  framework, which an earlier build did (a word in a typed message asked about the chest while Mani was still finding
  out how they feel, and was removed the same day). After the last stage, if the feelings they named or the one
  underneath hold a word from `somatic_check.places` in `content/prompts/somatic.md` (anxious, anxiety, nervous to the
  chest; stress, stressed, stressful to the head), Step 1 is the client's introduction and then "Earlier you
  mentioned feeling anxious, and that's often felt in the chest. Is that still the case for you right now?" with Yes
  and No (phase `somatic_check`). Yes is the client's exercise for that place and then the route as before; No is the
  general question with its five buttons; a typed answer is read as at Step 1; a feeling with no place gets Step 1
  as before. The place is found again from the stored understanding on the answer, which a running framework
  freezes. The question, the buttons and the word list are ours, not the client's document. Not measured live
  (needs muhammad's yes). `test_after_the_last_stage_a_feeling_that_has_a_place_gets_the_personal_question`,
  `test_no_to_the_personal_question_carries_on_with_the_general_check_in` and `test_a_feeling_word_in_chat_or_inside_a_
  stage_never_starts_a_body_question` in `tests/integration/test_turn.py`.
- **An offer comes only on a clear yes to Mani's check of its understanding; the check comes only once code has
  seen the problem, its core issue and the feeling underneath found in that order, each in an exchange of its
  own, so at their third message at the earliest, in every style** (muhammad, 2026-10-13, spec 0006; the order
  is code's since muhammad's live run of the same day, where Mani checked at their second message having asked
  about neither the core issue nor the feeling: `understanding.merge` takes a step only once the one before it was
  stored on an earlier turn, `[ctx]` names the next step as `understanding_next`, and a check is stored only when
  their own words give the feeling; a stored check is sent as the model's own sentences in the client's order,
  problem, core issue, feeling, what it comes down to, then the question, `repairs.check_text`). The third step was what is
  in their control until muhammad replaced it with the underlying feeling (2026-10-21): the person may name it, or Mani
  offers it from their words as a possibility inside the check, never as a fact, for them to confirm or correct;
  "I don't know" at that step stores Mani's closest reading as a possibility so the check still opens, and no new gate
  or deadline was added (`test_the_feeling_step_replaced_control_and_the_prompt_did_not_grow`, the prompt is held to its
  size). Because the client's flow
  (meeting of 2026-10-13, R14) is understand the problem, then its core issue and the feeling underneath,
  then check that understanding with them and offer only on a yes, and the message count it replaces needed
  three fixes in a row (scope features 12, 15, 19) without ever recording whether the person agreed. Before
  that: the client rejected an offer on the first message (R1, 2026-10-12); the three steps put the earliest
  check at their third message and the earliest offer at their fourth. Code stores only when the last check was made
  (`threads.check_at_message_count`, migration 023); the next turn is `Moment.CHECK_OPEN`, whose shape alone
  carries `check_answer` and `offer`. A clear yes makes that reply the client's offer; anything else (a no, a
  yes with an addition, another topic) keeps chatting, and the check is used either way. A new check waits
  `COOLDOWN_AFTER_DECLINE` after the last check and `cooldown_for(outcome)` after the last offer, and a set
  just finished may be offered again on a new confirmed check. The check's words are the model's own, never
  fixed text (muhammad, 2026-10-13); its `check` field marks it, so no code reads text to find it. "No check by
  message 5" is only logged. `context.offer_window`, `due` and the one time clarification lines are gone.
  `test_mani_may_check_from_their_second_message_*` and `test_a_check_is_answered_on_the_next_turn_only_*` in
  `tests/unit/test_chat_context.py`, and the spec 0006 tests in `tests/integration/test_turn.py`. Not yet
  measured live (needs muhammad's yes). Every
  reply before an offer asks one question, and what they say back about how it is for them is how the set
  is found. The set is chosen by what hurts, by its Use it when and
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
- **One style file per thread, in the system prompt, written from the client's behavior lists** (muhammad,
  2026-10-12). Because the client separates the styles by what each reply is trying to do, and our own recipe per
  style, under shared rules that contradicted their examples, drifted from it (styles document, 2026-10-12).
  `content/prompts/style_directive.md`, `style_supportive.md` and `style_reflective.md` each hold only the client's
  one-sentence description of that style, which muhammad chose over the longer behavior lists on 2026-10-22. Their example conversations were removed
  (muhammad, 2026-10-13): the client's terse Directive examples pulled against the newer way of communication
  document, and the model copies examples over rules; the one example of the sound is now `mani_base.md`
  `sounds_like`. `composer.compose` sends only the style resolved for the thread, after
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
  realistic way to see it and one clear path, a plan ("raise it with HR") counting as the path, and Thought Reframe's
  last step (`replacement`) only when they have a balanced thought they say they believe, which need not be positive
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
  `test_a_wish_to_stop_leaves_the_framework_and_it_comes_back_only_when_asked_for`). The problem, core issue and feeling found before the offer reach every stage turn as `their_case` in `[ctx]`
  (the stored understanding, relabelled while a framework runs or is about to start), and every stage question and
  possibility is about it, in their words (muhammad, 2026-10-22; `test_the_findings_are_their_case_once_a_framework_is_running_or_about_to_start`). Every feeling they name is kept, none twice. The problem, core issue and underlying feeling
  grow with everything they say, through the whole conversation, in a framework too: each new entry is added after the
  stored ones, none twice, and nothing is replaced or removed (the oldest entry goes only past 600 characters), so the
  model sees the whole picture in `[ctx]` every turn; what does not fit them goes in `also` (a warning, a time limit).
  Because the first read went stale (the boss chat: credit taken, his father not listening and low pay were said after the
  case was frozen, so the D and E questions were built on a first read that missed them), and add-only removes the
  failure the freeze was for, a later detail replacing the problem (muhammad, 2026-10-22; `understanding.merge`,
  `test_after_an_offer_the_case_keeps_growing_and_nothing_in_it_is_lost`; the check no longer writes over them,
  `test_a_stored_check_keeps_what_it_came_down_to`).
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
  muhammad, 2026-10-13, specs 0005 and 0006). Because the feeling they open with was said once and then lost, and
  `thread_summaries.current_issue` lagged a whole fold behind the 20 message window (the frustrated chat,
  2026-10-13, R4, R6); muhammad chose this over OpenAI's conversation API (OpenRouter rejects stored state) and
  over a prompt rewrite alone. Since the whole thread is in view (2026-10-13) the window premise no longer
  holds; the record stays as the steps' gate state, A's feeling slot and the exercise pick's issue. Every reply reports `understanding_update` (`feeling`, `issue`, and since spec
  0006 `core_issue` and `underlying_feeling`, the client's pinpointed problem, its core issue and the feeling
  underneath): only what this message names or changes. On a check turn the check's fields are merged first and
  `understanding_update` after them, so their own words win. `understanding.merge` keeps the stored value on a null or blank one; anything else
  replaces it, on one line, at most 200 characters. Nothing is merged on a concern turn. It is sent back every
  later turn as the `understanding:` line in `[ctx]`, disarmed, and code reads it only to place A's feeling on
  the start turn and to give the exercise pick its issue; no gate reads it. Its own update, only by
  `mani_service`; never logged; sent only in its own thread; deleted with the thread. `current_issue` is gone.
  With `AI_DEBUG_MODE` on, a turn returns `understanding` and the chat tester shows it under "What Mani knows".
  `tests/unit/test_understanding.py`, the spec 0005 tests at the end of `tests/integration/test_turn.py`,
  `tests/sql/test_grants.sql`. Not yet measured live (needs muhammad's yes).
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
- **Each question follows from their last answer and keeps their feeling and issue in view; before an offer
  it asks for what is still missing** (muhammad, 2026-10-09; cut 2026-10-12; spec 0005, 2026-10-13). Because
  Mani re-asked what they had said and walked them into worst cases (2026-10-09), the client's own questions
  ask what made them think it, what feels most pressing, and open on their words (styles document, 2026-10-12),
  and ABCDE's checklist and the bans on using their feeling turned "i am frustrated" into questions about
  ABCDE's needs and an offer about their judgment of the client (the frustrated chat, 2026-10-13, R4). One
  positive rule in `mani_base.md` `rules` says it: "Each question follows from their last answer and keeps the
  feeling and issue they came with in view. Their feeling word may come back inside a question, never as a
  statement about them." No framework checklist steers the questions (`to_find_out` and "Finding the fit" are
  gone). What each question is trying to do comes from the style file. Shared by all three: when the basic what is
  missing (what happened, what they are deciding), it is asked first; a reflection only checks or shows
  understanding; never asking for something they already made clear, in any words; a feeling word only as a question to confirm
  or correct, never told to them as what they feel; one question, never harder than the last (a vague or unsure
  reply gets an easier question about one small part; when they give almost nothing it may name two or three
  concrete possibilities from what they said, as the client's sample does, R13, 2026-10-13), and no advice or
  suggestion hidden in a question. Both sides of one decision in one question, and "what would it
  mean", are allowed: the client asks both (2026-10-12). `heading_toward` only decides what is offered. Mani never joins two things
  they said into a link they did not make. Told it got something wrong, in any words, it says it misunderstood and asks what would be
  more accurate (the client's line), never explaining what it meant.
- **Mani's voice is the shared shape in `mani_base.md` `how_you_talk` plus the chosen style's file; there is no
  shared example conversation** (muhammad, 2026-10-22, replacing "Mani talks like the client's sample conversation",
  2026-10-13). Because all three styles read the same: one sample was copied in every style, one line blended
  Supportive and Reflective for everyone, and each style file was one sentence. The shape stays (a mirror of the whole
  message in their words, one question on its own line, options under it, two to five short sentences, no dashes), and
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
  of how things fit together said for them to confirm or correct. the options for answering the question are the reply's `options` field, which the model must fill (or leave null
  for a yes or no question or a check) and code puts on a line of their own under the question, because the prompt
  rule for them was lost to "one question" lines elsewhere three times (muhammad, 2026-10-22;
  `test_the_options_go_on_the_line_under_the_question_and_only_where_the_reply_is_free_text`); framework stage replies carry it too, under the model's own stage question and never under the
  client's fallback line (`test_the_possibilities_go_under_the_models_own_question_and_never_under_the_clients_line`).
  A reply is a mirror that adds nothing they did not say, an open question that never leads, then possibilities with room
  for something else; the check reads as one flowing summary of the situation, what lies under it and the feeling, then asks
  whether it captures it or something was missed (muhammad, 2026-10-22). Its paragraphs are laid out in code, not left
  to the model, which broke the line before its question in some replies and not others: Mani's own text
  before a framework goes out with each closing question, and the options asked after it, on a line of their
  own (muhammad, 2026-10-21: the model put them on one line despite the prompt), unless a single question has
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
  (`context._MEANING`), so `response_format.md` holds only what the block is. A test fails if a key is sent
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

- R2's 4 s median (2026-10-14): at the fastest regular Azure or OpenAI endpoint a 300 token reply takes about
  6.5 s. Only `openai/fast`, at double the price ($0.2 and $1 per million tokens), reaches 4 s. Decide with the
  client whether the target or the price moves.
- Tell the client (2026-10-13, spec 0004): inside ABCDE, Mani goes one stage per reply, and a stage the person
  already explained is said back and confirmed once ("Is that right?" or a similar short phrase) rather than
  named and passed, as the ABCDE document's Situation 1 shows for A. Only A has a "possible" event; for B to
  E a guess is asked, never said back.
- Tell the client (2026-10-08): "overwhelming" was removed from the Structured Problem Solving description,
  since every offer showed a feeling the person had not named; Supportive and Reflective questions were
  written for the 26 stages whose three styles were identical (the client's wording is kept as Direct, or as
  Reflective for ACT `present`); the offer buttons read Try it / Tell me more / Keep chatting, not the
  specification's "Yes, let's try it" / "I want to keep talking". Have them review the new lines.

- Crisis resources, `PROTOCOLS` and `CLARIFICATION` wording (point 3 above).
- Tell the client what caused the first message offer (R1) and that an offer now comes only on a yes to
  Mani's check of its understanding, at their third message at the earliest, in every style, and have them
  read about five real Supportive and Reflective transcripts.
- Send the client a short written summary of the flow agreed in the meeting of 2026-10-13 (no transcript
  exists) so they can confirm it: pinpoint the problem, then its core issue and the feeling underneath,
  check it with them, and offer only on a yes (R14, spec 0006).
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
