# The Framework Runs the Way the Client's Sequence Shows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The offer, the stages and the close follow the client's sequence document; Directive is short; suggestion
buttons appear in the chat.

**Architecture:** Code sends the client's fixed pieces (button rows, the five-step text, the example) and keeps the
offer's step and the feelings check on the framework row; the model writes the lead-in, every stage and the replies
around them. A reply field carries suggested answers that code shows as buttons where allowed.

**Tech Stack:** Python 3.14, FastAPI, asyncpg, pydantic; pytest; `backend/.venv`.

**Spec:** `docs/superpowers/specs/2026-11-18-framework-sequence-design.md`

## Global Constraints

- Branch `feat/one-call-turn` in `/Users/mac/Desktop/mani-ai`; commit per task; never merge or open a PR.
- Labels, word for word: lead-in `Not sure`, `Show me how`, `Give me a tool`; after the steps `Start <framework name>`,
  `I need an example`, `Talk more first`; feelings check `Stronger`, `More focused`, `Still a bit tired`; closing
  `Keep Chatting`, `Go to Library`, `Finish for Now` (unchanged).
- ABCDE's step text per style is the document's, minus the openers that answer "Not sure": Directive "The ABCDE
  technique can really help. It breaks down thoughts into five steps:", Reflective "The ABCDE technique can help reflect
  on these thoughts by breaking them down:", Supportive "The ABCDE technique is a kind way to help break these thoughts
  down:"; then the five list lines exactly as in `docs/client/messages/2026-11-18-framework-sequences.md`; then
  Directive "Ready to dive into a real life situation?", Reflective "Are you ready to dive into a real life
  situation?", Supportive "Would you like to try diving into a real life situation together?".
- Talk more first lets the offer lapse; only a typed clear no (`action: stop` on an open offer) declines it.
- A prompt change passes the gate judged by style, the two prompts run one after the other; `check_suite.py` exits 0.
- CLAUDE.md: ABOUTME headers, tests first, no orphans, decisions edited in place.

## Review Focus

1. A tap on an old Try it / Tell me more / Keep chatting button from before deploy: Try it still starts the open offer
   (it carries the framework id); the other two read as plain text. Test in Task 1.
2. A guarded (safety) turn while the offer is at the lead-in or the steps: nothing moves and no steps are appended.
   Test in Task 1.
3. The feelings check open when a safety worry arises: the turn is held, the check stays open, and the next clear turn
   closes the set. Test in Task 2.
4. Suggestions the model sends when code also shows buttons, or on a safety turn: dropped. Test in Task 3.
5. An edit of the reply that showed the steps or the feelings check: rewind restores the framework row's phase exactly.
   Test in Task 2.

---

### Task 1: The offer in three steps

**Files:**
- Modify: `backend/mani/chat/greeting.py` (labels), `backend/mani/chat/repairs.py` (button rows),
  `backend/mani/chat/techniques.py` (`STEPS` phase, `steps_text`, `example_text`), `backend/mani/chat/taps.py`,
  `backend/mani/chat/decide.py`, `backend/mani/chat/turn.py` (`_explained`, `_example`, the typed lead-in append,
  `open_offer` at either phase), `backend/mani/chat/facts.py` (the open-offer line per phase),
  `backend/content/frameworks/abcde.md`, `backend/content/frameworks/thought_reframe.md`, `backend/scripts/seed.py`
- Test: `tests/unit/test_taps.py`, `tests/unit/test_decide.py`, `tests/unit/test_seed.py`,
  `tests/unit/test_abcde_content.py`, `tests/integration/test_turn.py`, `tests/unit/test_repairs.py`

**Interfaces:**
- Produces: `greeting.LEAD_IN_LABELS: tuple[str, ...]`, `EXAMPLE_LABEL`, `TALK_MORE_FIRST_LABEL`,
  `greeting.start_label(framework_name: str) -> str`; `repairs.lead_in_buttons() -> list[SmartPrompt]`,
  `repairs.start_buttons(framework: Framework, *, with_example: bool) -> list[SmartPrompt]` (Start carries
  `technique=framework.id`); `techniques.STEPS = "steps"`, `techniques.steps_text(framework, style) -> str`,
  `techniques.example_text(framework) -> str`; `TapEvent.example: Framework | None`, `TapEvent.set_aside: bool`
  (replaces `declined`); `Decision.show_steps: Framework | None`.
- Removes: `TRY_IT_LABEL`, `TELL_ME_MORE_LABEL`, `KEEP_CHATTING_LABEL`, `PERMISSION_QUESTION`, `offer_buttons`.

- [ ] **Step 1: Write the failing tests.**
  - `test_taps.py`: each lead-in label on an open offer → `explain` is the framework; `I need an example` → `example`;
    `Talk more first` → `set_aside` True with a fact; `Start ABCDE` (technique `abcde`) on an open offer → `starting`,
    and its fact names only the first stage (no "go on to").
  - `test_decide.py`: an offer → `labels == ["Not sure", "Show me how", "Give me a tool"]`, row `offered`/`offering`;
    an open offer at `offering` with a plain reply → `show_steps` is the framework, prompts are
    `["Start ABCDE", "I need an example", "Talk more first"]`, row phase `steps`; the same with `action="stop"` →
    declined; at `steps` with `set_aside` → `retire_technique`, not declined; at `steps` with a plain reply →
    lapses; a guarded turn at either phase → nothing changes and `show_steps` is None; the starting turn with
    `stage="belief"` stores `activate` (first stage only).
  - `test_seed.py`: a framework whose offering lacks `example` cannot be seeded active.
  - `test_abcde_content.py`: `steps_text(abcde, style)` for each style equals the constraint's text (intro, the five
    lines, the ready question).
  - `test_turn.py` `test_the_offer_runs_lead_in_steps_example_then_start`: offer → tap `Not sure` (no model call,
    content == steps text for the style, three Start buttons) → tap `I need an example` (no model call, content ==
    example text, buttons Start / Talk more first) → tap `Start ABCDE` → a stage reply stores `activate`.
    `test_a_typed_reply_to_the_lead_in_gets_the_reply_then_the_steps`: content ends with `"\n\n" + steps text`, the
    three buttons, row phase `steps`. `test_talk_more_first_lets_the_offer_lapse_and_it_may_come_back`: after the tap
    the row is retired (not declined) and a later offer of ABCDE is allowed. `test_an_old_try_it_button_still_starts`.
  - `test_repairs.py`: the two button rows.
- [ ] **Step 2: Run them.** `cd backend && source .venv/bin/activate && pytest tests/unit tests/integration/test_turn.py -q`.
  Expected: the new tests FAIL.
- [ ] **Step 3: Content.** ABCDE `offering`: `explain` per style becomes the constraint's step text; add `example`
  (one string): "Here's how it can go for someone whose boss moved a deadline up while their child was sick." then
  A to E as lines from the document's answers ("A (what happened): My boss moved the deadline up and my child is
  sick." … "E (the new belief): I have a lot on my plate, but I am capable of doing what I can one step at a time.").
  Thought Reframe: its `explain` per style ends with its style's ready question (the same three as ABCDE); add an
  `example` in the same shape from its own five steps (ours, commented as ours until the client supplies hers).
  `missing_for_activation` also requires `offering.example`.
- [ ] **Step 4: Implement.** `open_offer` in `turn._turn` is a row `offered` at `offering` or `steps`. `decide`:
  at `offering`, unguarded and with no tap that starts, explains or sets aside: `action == "stop"` declines, anything
  else sets `show_steps`, the start buttons and phase `steps`; at `steps`: `set_aside` retires, a reported first stage
  starts, `stop` declines, anything else lapses; `stage_of` on the starting turn allows the first stage only.
  `turn._apply` appends `"\n\n" + steps_text(...)` when `decision.show_steps`. `_explained` sends the step text with
  `start_buttons(with_example=True)` and moves the row to `steps`; `_example` sends the example with
  `start_buttons(with_example=False)`. `facts`: the open-offer line says which step is showing and that a clear yes
  after the steps starts the set. Delete what the Interfaces block removes, and its tests.
- [ ] **Step 5: Run the suite.** `pytest -q` and the chat-tester suite. Expected: all pass.
- [ ] **Step 6: Commit.** `git commit -m "Offer the set in the client's three steps: lead-in, the five steps, then start"`

### Task 2: The feelings check and the end of E

**Files:**
- Modify: `backend/mani/chat/greeting.py` (`FEELINGS_LABELS`), `backend/mani/chat/techniques.py`
  (`FEELINGS = "feelings_check"`), `backend/mani/chat/decide.py` (`_moved`), `backend/mani/chat/turn.py`
  (`_updates`: the end check marked done when the check-in opens), `backend/mani/chat/facts.py` (the last-stage line
  and the check-in line), `backend/content/frameworks/abcde.md` (`effective`), `thought_reframe.md` (`replacement`)
- Test: `tests/unit/test_decide.py`, `tests/unit/test_facts.py`, `tests/integration/test_turn.py`,
  `tests/integration/test_read_think_write.py`

**Interfaces:**
- Consumes: Task 1's labels module and `stage_of`.
- Produces: `repairs.feelings_buttons() -> list[SmartPrompt]`; row phase `FEELINGS` while the check is open.

- [ ] **Step 1: Write the failing tests.** `test_decide.py`: finish on the last stage → row phase `feelings_check`,
  prompts `["Stronger", "More focused", "Still a bit tired"]`, nothing finished; a running row at `feelings_check`
  with any reply → finished, retired, closing buttons; with `end_check_due` → the end check first, and its settled
  answer → `feelings_check`; guarded at `feelings_check` → nothing changes. `test_facts.py`: a row at
  `feelings_check` gives the check-in line ("reply briefly, ask nothing") and no stage line; the last stage's line says
  to acknowledge the new belief, ask how they feel now and set `action` to finish. `test_turn.py`
  `test_after_e_the_feelings_check_then_the_closing_buttons`. `test_read_think_write.py`
  `test_editing_the_reply_that_opened_the_feelings_check_restores_the_last_stage`.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Content.** ABCDE `effective`: `purpose`, `ready_when` and `if_unclear` ask for the new belief in their
  own words only (the "one clear thing" / `path` parts go). Thought Reframe `replacement`: drop "(a) one thing they
  would like to do with the new thought"; keep (b), the practical step when the thought is accurate (it is the
  client's own step for that case).
- [ ] **Step 4: Implement** per the tests: `_moved` sends the last stage's finish (or the settled end check) to
  `FEELINGS`; a row at `FEELINGS` finishes on the next unguarded turn. `_running_line` handles `FEELINGS` before looking
  the phase up in the stages.
- [ ] **Step 5: Run the suite.** Expected: all pass.
- [ ] **Step 6: Commit.** `git commit -m "After E, ask how they feel with the client's three buttons, then close"`

### Task 3: Suggestion buttons

**Files:**
- Modify: `backend/mani/chat/reply.py` (`TurnReply.options`), `backend/mani/chat/repairs.py`
  (`suggestion_buttons`), `backend/mani/chat/turn.py` (`_apply`), chat-tester `trace_view.py` (label)
- Test: `tests/unit/test_reply.py`, `tests/unit/test_repairs.py`, `tests/integration/test_turn.py`

**Interfaces:**
- Produces: `TurnReply.options: list[str]` ("Up to three short answers they might give to your question, in their
  own terms; empty when your question has no few natural answers"); `repairs.suggestion_buttons(options: list[str])
  -> list[SmartPrompt]` (stripped, empty and duplicate dropped, at most 3, each at most 40 characters); trace key
  `suggested`.

- [ ] **Step 1: Write the failing tests.** `test_reply.py`: the strict schema's properties include `options`.
  `test_repairs.py`: `suggestion_buttons([" Work", "Family", "", "Work", "Everything at once", "Fourth"])` →
  labels `["Work", "Family", "Everything at once"]`. `test_turn.py`: options show as buttons on a plain chat reply; not
  when an offer's buttons show, not while a set runs, not on a guarded turn, not when the chat pauses; a tapped
  suggestion reaches the model as their message.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement.** In `_apply`, after the decision: when `decision.prompts` is empty, no set was running or
  offer open before the turn, the turn is not guarded and not pausing, `prompts = suggestion_buttons(reply.options)`.
- [ ] **Step 4: Run the suite.** Expected: all pass.
- [ ] **Step 5: Commit.** `git commit -m "Show the model's suggested answers as buttons in the chat"`

### Task 4: The prompt and the gate

**Files:**
- Modify: `backend/content/prompts/mani.md`, `backend/evals/run_eval.py` (judged by style), `backend/evals/cases.json`
  (rule cases), `backend/evals/check_suite.py` and `suite.json` (labels, turns)
- Test: the gate and the suite (paid)

- [ ] **Step 1: The prompt.** Offering: the lead-in replaces the offer sentence (what they said, a belief can feel true
  without being a fact, a question about how they could test it; never name the set), one example per style adapted
  from the document. Inside the set: one stage per reply always, with its line; a stage the chat touched gets its line,
  what you understood in a sentence and its question; Directive opens each stage with one short acknowledgment; E ends
  on the new belief (line 142 loses "and what they want to do with it"); after E, acknowledge it and ask how they feel
  now with `action: finish`; the reply after the check closes in a sentence or two with no question; line 146 "Help them
  with what they chose" becomes "If they ask what to do, help in practical terms". Your style: Directive replies are
  short (three or four short sentences at most), in the chat and the set. How you sound: no stock phrase twice in a
  conversation. What you fill in: `options`, when to fill it and when to leave it empty; `action: stop` on an open offer
  is a clear no.
- [ ] **Step 2: The gate's code.** `run_eval.py`: a Directive quality case's judge prompt says short replies are the aim
  in that style and length is not a fault; the report gives the overall per style and the 0.15 comparison over
  Supportive and Reflective only. `cases.json`: rule cases for the lead-in (action offer, no set name in the text, ends
  on a question), one stage per reply (`stage_in` the first stage on a start), E answered (`action: finish`), the reply
  after the check (no "?"), suggestions (non-empty on a cause question, empty on a safety message). `check_suite.py`:
  offer checks use `Not sure` and `Start ABCDE`; the two framework conversations get enough turns to reach the close.
- [ ] **Step 3: Reseed and run the suite of tests.** `python scripts/seed.py && pytest -q`. Expected: pass.
- [ ] **Step 4: The gate, one prompt at a time.** `git show HEAD:backend/content/prompts/mani.md` saved as the baseline;
  `python evals/run_eval.py --label seq-before --prompt <baseline>`, then `python evals/run_eval.py --label seq-after`.
  Expected: Supportive and Reflective overall no more than 0.15 below the baseline; every rule passes in seq-after
  (the new rule cases may fail on the baseline, which predates them). Then `python evals/check_suite.py`. Expected:
  exit 0.
- [ ] **Step 5: Commit.** `git commit -m "Prompt: the client's lead-in, one stage per reply, the feelings check, short Directive, suggestions"`

### Task 5: Records

**Files:**
- Modify: `docs/client/requirements.md`, `backend/PORT-STATUS.md`, journal notes, `.claude/BACKEND.md` if it names
  the removed labels

- [ ] **Step 1: requirements.md.** Rows R107 to R113 as the spec lists them, source the 2026-11-18 message, status
  in-progress; conflict rows: the document's offer replaces the client's Try it / Tell me more / Keep chatting
  (2026-10-08) and Tell me more's explanation; the document's closing buttons and greeting not adopted (muhammad,
  2026-11-18).
- [ ] **Step 2: PORT-STATUS Decisions in force,** edited in place: the offer (three steps, labels, Talk more first
  lapses, typed reply to the lead-in), one stage per reply, the feelings check, suggestions, Directive short, the gate
  judged by style; each with `Because ... (2026-11-18)` and the tests. Journal: a note for the change, and the
  superseded line on notes that argued for the replaced offer buttons and E's path.
- [ ] **Step 3: Check.** `grep -rn "Try it\|Tell me more\|Keep chatting" backend/mani backend/PORT-STATUS.md .claude`
  shows only history lines. `pytest -q` passes.
- [ ] **Step 4: Commit.** `git commit -m "Record the client's framework sequence and the decisions it changes"`
