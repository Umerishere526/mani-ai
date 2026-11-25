> **Historical** (marked 2026-11-25): a design or plan as written at the time; parts no longer match the code (the return check after a pause, for one, is gone). What the backend does today is in `backend/PORT-STATUS.md`.

# One-call conversation: the rebuild of Mani's turn

Date: 2026-11-17. Author: Claude, with muhammad. Status: draft for muhammad's approval.

## Intent and why

Mani's backend runs each turn as a state machine around one structured model call. The model fills a 22-field form
with the reply last, and code then rewrites the reply: it stitches a separate closing question on, swaps in
templates, puts letter lines in front and strips dashes. A second "reading" call after the reply writes Mani's
understanding of the person. The mobile app never asks for that reading, so in production it only runs from the
nightly catch-up job. On every turn the model gets about 75,000 characters of rules, with more than a hundred
"never"s in them.

muhammad's complaints follow directly from that design: the model misses context and the core, forgets between
turns, does not listen when corrected, asks too many questions, and code-stitched text breaks grammar.
`orchestrator.py` had 81 commits in 2.5 months, and the patch limit in CLAUDE.md was passed long ago.

A throwaway spike (branch `spike/one-call-turn`, worktree `../mani-ai-spike-a`) showed that the opposite design
works: one call, a short prompt, the model writing every word, and code keeping only guarantees. This document is
the rebuild of the real backend on that design. When it is done, the old path is gone.

## Goals

- The model holds the conversation. It writes every sentence Mani says, keeps its own short notes from turn to
  turn, and decides what happens next. Code never edits its text, except to replace dashes.
- Code keeps only what must be guaranteed: the fixed client pieces, the buttons, the framework's stage order,
  never offering again what was declined or finished, and the safety pause.
- One model call per turn, with nothing running after the response. That suits Vercel, which stops an instance
  once a response is sent.
- Measured quality: the evaluation in `backend/evals/` is the gate for every prompt or model change.
- Cost of about $0.0005 per turn, inside muhammad's budget of $0.002.

## Non-goals

- No change to the mobile or web apps, and no change to the API's request or response shapes.
- No change to the library, exercises, auth, the database tables beyond what is listed under Data, or the admin.
- No streaming in this rebuild. It becomes possible, because code no longer rewrites the text, but it is
  separate work.
- No fine-tuning.

## Anti-goals: it fails even if it works when

- code writes or stitches any sentence of Mani's reply, apart from the client's fixed pieces sent whole;
- the old path survives beside the new one;
- a safety turn can go out with no reply;
- the prompt grows back into a list of rules, instead of a few rules with good examples.

## Constraints

- **Vercel:** nothing runs after the response. No connection is held during the model call; the existing
  read-call-write runner (`chat/runner.py`) stays. The chat deadline is 45 seconds.
- **Budget:** at most $0.002 per turn (muhammad, 2026-11-17).
- **Privacy:** the model runs on zero-data-retention hosts only (OpenRouter `provider.zdr: true`), and never on
  the model makers' own APIs or other China-based hosts.
- **Client:** these fixed pieces stay word for word, sent whole by code with no model call or in place of the
  model's text: the greeting, the style question and the style openers; the Tell me more explanation per style;
  every button label; `crisis.CRISIS_REPLY`, the pause message (`crisis.pause_reply`), `crisis.END_CHECK` and
  the return opener.
  - The stage letter lines ("A is for Activating Event.") are written by the model, as muhammad decided on
    2026-11-17. Code does not check them at runtime, because that would be code editing text. The evaluation has
    a rule case that checks them.
  - The conflicts with client requirements that muhammad has overruled are recorded in
    `docs/client/requirements.md`:
    - R73: the first reply may name the pattern.
    - R83: options may name feelings, each with its reason.
    - R94 and R105: no solutions in the chat, only ideas to explore.
    - The client's offer template and Keep chatting line, replaced by the model's own words (to record with the
      rebuild).
- **CLAUDE.md:** ABOUTME headers, tests with fakes built from real interfaces, no orphans, and "Decisions in
  force" updated in the same change.

## Approaches considered

1. **The model holds the conversation in one call, with a small amount of state (chosen).** One short prompt,
   the whole transcript, and a facts block. A seven-field reply with the text first. Code guards only what must
   be guaranteed. This fixes the causes: there is no stitching, memory has one writer, and the model's thinking
   goes into the reply. The risk is offer timing, which goes back to the model; the evaluation and the spike's
   live tests cover it.
2. **The same, but code keeps running each framework stage by stage (`walk.py`).** This guarantees stage order,
   but it keeps the part muhammad named as feeling like a questionnaire, and about 2,000 lines of code.
   Rejected.
3. **Keep today's structure and shorten the prompts.** This is the smallest change, but every cause stays.
   Rejected.

**Model.** Measured on the real stack against 20 cases, three runs each (`backend/evals/results/`):

| Model | Score against ChatGPT (5 = as good) | Per turn | Median wait |
|---|---|---|---|
| `openai/gpt-chat-latest` | 4.07 | $0.016 | 4.2 s |
| `anthropic/claude-sonnet-5.5` | not scored; clean on the safety and framework suite | about $0.013 | 9.6 s |
| `minimax/minimax-m3.1-flash`, reasoning low (**chosen**) | 3.57 | $0.00045 | 3.8 s |
| `deepseek/deepseek-v4.1-flash-1017` | 3.64 | $0.00022 | 2.3 s |
| `openai/gpt-6-luna` (today's model) | flat; not scored | about $0.0005 | 4 to 9 s |

muhammad chose MiniMax M3.1 Flash on 2026-11-17. The chat model and Sonnet were over budget. DeepSeek scored the
same within noise, but marked chest pain with arm symptoms as `unsure` instead of `danger` in 4 of 9 runs, where
MiniMax got it right in 9 of 9. Three prompt variants did not move the cheap models past about 3.6: the gap to
the chat model is the model's ability, not the prompt. The journal note
`mani-vault/Journal/flat-replies-were-the-model-2026-11-17.md` has the full findings.

## The design, as decided

### A turn

1. As today: the duplicate check, the advisory locks, the pause gate, the rate limits, loading the turn context,
   saving the rewind snapshot, and the history window within `context_budget_chars`.
2. A tap on a style button returns that style's fixed opener, with no model call, as today
   (`_open_in_style`).
3. A tap on **Tell me more** while an offer is open returns the framework's fixed explanation for the person's
   style, with the Try it and Keep chatting buttons, and no model call.
4. Otherwise, exactly one model call, with these messages:
   - **system:** the prompt `mani.md`, then the framework guide generated from the registry (for each active
     framework: when it fits, and for each stage its line, purpose and when it is answered), then the person's
     profile and memory as today, then the summary once messages have left the window;
   - the transcript, with the person's messages disarmed as today;
   - **user:** their message;
   - **system:** the **facts** for this reply (below).
5. Code applies the reply's fields (below), writes the message pair and the thread updates in one transaction,
   and returns the turn. Nothing is left for after the response, except the summary when it is due (see Data).

### The facts block

These are facts, never instructions about style. Each line is present only when it applies:

- their style;
- Mani's notes from the last turn;
- the framework running, the stage the last reply was on, and the next stage's line and the rule that it moves
  at most one stage;
- an offer the last reply made, and that a clear yes in their words starts it;
- what was declined or finished in this conversation;
- a safety worry being open;
- **what code would refuse, said before the reply:** "You cannot offer a set of questions in this reply" while a
  framework runs, an offer is open, one was finished, or a safety worry is open;
- the return check after a pause;
- a recent crisis in another conversation;
- a tap on a button, and what it means ("They tapped Try it: … opens its first stage");
- "Give this conversation a title", when the title is due.

### The reply

```
text       what Mani says, sent as written
action     none | offer | finish | stop | library
framework  the id of the framework offered, with offer
stage      the stage whose question the reply asks, while a framework runs
safety     level none | unsure | danger, about themselves | someone_else | from_someone | body,
           help_in_place, declined (they refused the help offered), symptom_now yes | no | unsaid,
           still_there (their message itself says the danger goes on), why
notes      Mani's own working notes for its next turn, under 150 words
title      only when asked for
```

### Code's guarantees: what code does with the reply

- **Text:** sent as written, with dashes replaced (`repairs.without_dashes`). It must not be empty.
- **Offer:** made only if no framework is running, no offer is open, nothing was finished, the framework was not
  declined, it is in the registry, and no safety worry is open. Then the buttons are Try it, Tell me more and
  Keep chatting, and the technique row records the offer. The facts block already told the model when it may
  not offer, so a refusal here should never happen. If it does, it is logged.
- **Start:** a tap on Try it, or a typed yes when the reply moves to a stage of the offered framework.
- **Stages:** a framework moves at most one stage per turn. The stage stored is the one the reply asks, but
  never more than one past the stored stage. On the starting turn it may reach the second stage, when the chat
  already answered the first.
- **Finish:** only on the last stage. The closing buttons are Keep Chatting, Go to Library and Finish for Now,
  and the framework is recorded as finished.
- **Stop:** the framework is recorded as declined.
- **Library:** the Go to Library button.
- **Keep chatting on an offer:** recorded as declined. Any other reply to an open offer lets it lapse.
- **Safety:** muhammad's pause rules of 2026-11-13, 11-14 and 11-16 stay exactly as they are today
  (`pause.pauses_now`, `safety.after`, `crisis.pause_reply`). Only their input changes: the reply's `safety`
  fields replace `SafetyRead`, and the phrase screen goes.
  - The thread's safety state follows `level`. The first move to `danger` marks the thread in crisis
    (`threads.mark_crisis`).
  - **Never a pause on the first danger message** of a clear conversation: Mani's own reply comes first, and the
    next message decides.
  - Danger to themselves, to someone else, or from someone pauses, with no help in place, when the danger goes
    on: after Mani has answered it (the state was already `danger`), or after Mani asked what they meant and the
    answer says it again.
  - **The body** pauses only when the symptom is happening now (`symptom_now` is yes) and they refuse the help
    for it (`declined`). Pushing back or doubting is never a refusal.
  - **After a pause:** the first message back never pauses. After that, only a message that itself says the
    danger is still there (`still_there`) pauses.
  - **The pausing turn sends the fixed text** for whose danger it is (`crisis.pause_reply`, R89), not the model's
    text. The mobile app shows no blocker, so this text is what puts the emergency numbers in front of them.
  - **After a framework's last stage**, when the conversation reached danger, Mani asks the fixed safety question
    (`crisis.END_CHECK`) before the closing buttons, and the answer is read as a safety turn.
  - An answer to a return check judged `none` marks that pause checked. The turn that asks the return check
    stores it as asked, so it is asked once.
- **Notes**, declined, finished and the return check are stored on the thread (see Data).
- **Title:** stored when one was due.

### Failure

- **The call fails on one host:** OpenRouter falls back to the next zero-data-retention host in the allowed list.
- **Every host fails, on any turn:** a fixed reply goes out, never an error. When a safety worry is open it is
  `crisis.CRISIS_REPLY`, as today. Otherwise it is a short fixed line that Mani is having trouble replying, with
  the emergency numbers, so a first message about danger during an outage still reaches help. The person's
  message is kept, the reply is stored, and the safety state does not move.
- **The reply does not parse:** one retry, as `client.complete` does today.

### Model and configuration

- The model, its reasoning effort and its hosts live in the prompt row's `model_id`, `model_parameters` and
  `routing`, the same way the voice row works today. Not in environment variables: the spike's
  `ONE_CALL_MODEL`, `ONE_CALL_REASONING_EFFORT`, `ONE_CALL_PROVIDERS` and `CONVERSATION_ENGINE` go.
- `minimax/minimax-m3.1-flash`, reasoning `low`, routing
  `only: [inferact-vllm, together, modelrun, fireworks, makora, nebius]` and `zdr: true`. The settings' default
  provider list, which allows only OpenAI, must not override a row's own list.
- The OpenAI priority tier (`service_tier`) applies only to OpenAI models.
- For Anthropic models, `chain.request_body` sends a top-level `cache_control`. It is not needed for MiniMax, but
  it is kept so a later model change is not caught out.

### The prompt

`content/prompts/mani.md` from the spike, as it stands at approval, loaded through the prompt cache like the
others. It replaces `voice.md`, `conversation.md`, `framework.md` and `moments.md`. `summarization.md`,
`memory_fold.md` and `title_generation.md` stay as they are. Changes to `mani.md` go through the evaluation (see
Testing).

### Data

- **`threads.understanding`** keeps its column, with a new shape:
  `{notes, declined: [ids], finished: [ids], return_check, safety_settled, danger_reached, danger_about,
  asked_about, safety_end_check}`. The last five are what the kept pause rules and the check after a framework
  read today.
- **A migration rewrites every existing row to that shape,** so conversations in progress keep what matters:
  - `declined` and `finished` are rebuilt from `thread_technique_state` and the offer history, so nothing
    declined or finished is offered again;
  - the return check and the four safety keys are kept as they are;
  - `notes` starts empty;
  - every other key (picture, reading, known, insights and the rest) is dropped;
  - old rewind snapshots are cleared, so an edit cannot restore the old shape;
  - a thread left at a body check-in phase is retired.
- **`thread_technique_state`** stays: framework, outcome, phase, at_message_count, stages_known (left empty) and
  the two somatic columns (left unused).
- **The follow-up endpoint stays** for the summary only, together with the catch-up job that runs it. The
  reading, `ReadAfter`, `read_understanding` and the pending reading go. Its response keeps its fields, with
  `read` always false.
- **`admin.turn_traces`:** each turn's trace has the action, framework, stage, safety level, whether it paused,
  the buttons and the latency. With AI_DEBUG_MODE, the notes and the raw reply too.

### What is removed

All of these are deleted in the same change, with their tests:

- **Code:** `chat/orchestrator.py` (except the pieces moved into the new turn: the locks, `_open_in_style`,
  `_copied_back`, `find_tapped_prompt`, `chosen_style`, `_within_limits`, `start_thread`, `opening_greeting`,
  `record_trace`, `link_call`, `_record_danger`, `_pause_writes`, `_safety_record`), `chat/walk.py`,
  `chat/converse.py`, `chat/context.py` (keep `disarm`, `resolve_style`, `copies_last_reply` and the safety record
  keys where they move to), `chat/picture.py`, `chat/understanding.py`, `chat/reply_checks.py`, `chat/body.py`,
  and the parts of `chat/repairs.py` other than `without_dashes` and `offer_buttons`. Also `chat/safety.py`'s
  phrase screen (`screen`, its phrase lists and categories; `State`, `after` and `danger_of` stay), the parts of
  `chat/pause.py` and `chat/crisis.py` the kept pause rules do not use, nearly all of `llm/schema.py` (the new
  reply model is about 50 lines), and the moment-specific composers in `prompts/composer.py`.
- **Prompts:** `voice.md`, `conversation.md`, `framework.md`, `moments.md` and `somatic.md`, plus their seeded
  database rows.
- **Scripts:** `scripts/scenario_check.py` and `scenarios*.json`, replaced by `backend/evals/`. `compare_runs.py`
  goes with them.
- **The body check-in is deleted, not kept paused** (my call; see Calls made).

## Testing

- **Unit tests with fakes built from the real interfaces**, for what code decides:
  - which offer is allowed and which is refused;
  - stage moves held to one step;
  - finish only on the last stage;
  - Keep chatting and stop recorded as declined;
  - Tell me more sending the fixed text with no model call;
  - safety moving the state, marking the crisis and pausing exactly when it should;
  - the return check;
  - the facts block's lines for each state;
  - the notes stored.
- **Integration tests** for one turn against the test database, with a fake model that returns a fixed reply.
- **The evaluation** (`backend/evals/run_eval.py` and `cases.json`) is the gate for any change to the prompt or
  the model. It has 14 quality cases and 6 rule cases from muhammad's 2026-11-17 comparisons, three runs each,
  scored by `openai/gpt-6.1-sol`.
  - Add a seventh rule case: on the turn a framework starts, the reply says the first stage's line.
  - **The pass mark:** the change and the current prompt and model run side by side in the same session. The
    change is kept only if its overall score is no more than 0.15 below the current one's, and every rule check
    passes. A score stored from an earlier day is never the comparison.
  - It uses a strict JSON schema, and calls expensive models a few at a time, because the OpenRouter balance
    limits parallel calls.
- **Before merge: the seven-conversation suite** (`backend/evals/suite.json`, run with `evals/drive.py`) through
  the real stack, with a model-played person. Each conversation lists what it must show (its `expect`). The
  checks on the reply's fields are asserted by a script, and the rest is read by muhammad:
  - the overdose is `danger` on the first message;
  - the chest pain is `danger` about the body;
  - passing thoughts with help present never reach `danger`;
  - the dodge never offers a framework;
  - both framework conversations finish with the closing buttons.

## Decisions in force to update (`backend/PORT-STATUS.md`)

- **Add:** one call per turn; the model writes every word; code keeps only the listed guarantees, and states them
  in the facts block before the call.
- **Add:** the model and its hosts (MiniMax M3.1 Flash, zero-data-retention hosts only), and the budget.
- **Add:** the evaluation is the gate for prompt and model changes.
- **Replace:** "every reply ends on a question" (muhammad, 2026-11-10) with "a question only when it helps"
  (2026-11-17).
- **Replace:** the offer decisions (the client's template filled by code; the move pressed by code) with "the
  model writes the offer; code adds the buttons".
- **Replace:** the stage walk owned by code with "the model writes each stage, and code only holds the order".
- **Replace:** the reading after the reply with "Mani's notes, written in the same call".
- **Keep, with a new input:** the safety and pause entries ("Safety is the model's judgment", "After a pause",
  the pause on danger, the pausing message), now fed by the reply's `safety` fields.
- **Retire, as approved by muhammad on 2026-11-17** (each entry rewritten in place, with the reason that the new
  prompt holds it or the code behind it is gone):
  - "A message that asks something never moves a framework stage" (2026-11-05). The prompt says to answer their
    question first; code no longer checks for a question mark.
  - ABCDE's D asked as two questions, with code remembering which is next (2026-10-21).
  - "An offer only after Mani has said the core back", together with `check_at_message_count`. The prompt holds
    it.
  - "Code never sends an offer in a reply that reports frustrated". The prompt holds it.
  - "A chat turn at medium effort". MiniMax runs at low.
  - The framework's ledger, shown on every turn.
- **Supersede:** the journal notes that argued for the replaced or retired decisions get the superseded line, as
  CLAUDE.md asks.

## Calls made, for muhammad to check

1. **The body check-in is deleted rather than kept paused.** It has been paused since 2026-11-05. Keeping its
   code beside a design that no longer has moments would be the half-migrated state CLAUDE.md forbids. If the
   client wants it back, it would be rebuilt as an action in the new turn. The client's script stays in
   `docs/client/`.
2. **`threads.understanding` is reshaped in place,** not replaced by new columns. It holds JSON already, and new
   columns would add a migration with no benefit.
3. **The follow-up endpoint stays,** for the summary only, so the API does not change.
4. **The evaluation's pass mark** is "no drop of more than 0.15 overall against a side-by-side run, and all
   rules pass". 0.15 is about the noise between runs.
5. **Summaries, memory folds and transcription are out of scope.** They keep their models and routing (OpenAI,
   `gpt-6-luna`). Whether zero data retention should cover them too is a separate decision.
6. **The stage letter lines are checked by the evaluation, not by code at runtime.**
7. **Conversations in progress keep their declined and finished lists** (rebuilt by the migration).

## Left to the builder

- Module names and boundaries in `mani/chat/`, within the 150-line component rule's spirit for functions.
- The order of the deletions, as long as `main` never holds both paths.
- The migration's exact SQL.
- How `drive.py` and the evaluation share code.

## Risks

- **Quality is about 88% of the chat model's score** (3.57 against 4.07). muhammad accepted this on 2026-11-17.
- **MiniMax broke two rules in the spike before the facts-block fix:** it offered while a safety worry was open,
  and wrote a template after the person declined. Both passed in the last evaluation runs. The evaluation keeps
  watching them.
- **The kept pause rules depend on the model's new safety fields.** `declined`, `symptom_now` and `still_there`
  have not yet been measured on MiniMax. The suite's overdose, chest and dodge conversations, plus a return-check
  conversation added to `suite.json`, must show them right before merge.
- **MiniMax is an open-weight model from a Chinese lab, served by Western zero-data-retention hosts.** The client
  may have a view on that for a mental-health product. She has not been asked.
- **The OpenRouter balance limits parallel expensive calls.** Production must keep the account topped up and
  watch for 402 errors.
- **Offer timing is the model's judgment.** The journal shows earlier models offering too early when allowed and
  never when not pushed. The live tests showed sensible timing, but there is no code floor. If it goes wrong,
  the fix is a fact (for example, how many exchanges have passed), not a rule in code.
