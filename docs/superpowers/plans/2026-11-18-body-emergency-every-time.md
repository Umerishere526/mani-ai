# A Possible Medical Emergency Always Gets "Call Now" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every reply to a body worry that has not been said to have stopped tells the person to call emergency
services now, guaranteed by code.

**Architecture:** `safety.danger_of` makes such a worry danger now; `judged.judge` reports when code raised the turn to
danger on a body worry the model itself judged lower; `turn._apply` then adds a fixed line after Mani's text. The
prompt's "ask first whether it is happening" line is swapped so the reply and the line agree.

**Tech Stack:** Python 3.14, FastAPI backend, pytest; `backend/.venv`.

**Spec:** `docs/superpowers/specs/2026-11-18-body-emergency-every-time-design.md`

## Global Constraints

- Branch `feat/one-call-turn` in `/Users/mac/Desktop/mani-ai-rebuild`; commit per task; never merge or open a PR.
- The line, word for word: `If this is happening now, please call 911 or get to the nearest emergency room now.`
- Over-triggering is accepted (muhammad, 2026-11-18); the line is added once per rise to danger, never every turn.
- A prompt change is gated side by side on the same day: no drop of more than 0.15 overall, every rule passing.
- CLAUDE.md: ABOUTME headers, no temporal names, decisions edited in place.

## Review Focus

1. Help already coming ("the ambulance is on its way") while the read is body and not stopped: the line still goes
   out; a reasonable person reads "if this is happening now, call" as harmless. Accepted, no test.
2. A turn that pauses (a refusal while the symptom is happening): the pause reply replaces the text and already names
   911; the line must not be added to it. Test in Task 1.
3. A body worry that settled earlier and comes up in the past tense: `reopening` keeps it `none`, so no line. Test in
   Task 1.
4. The dash remover runs after the line is joined: the line has no dashes, so it goes out word for word. Covered by the
   integration test's exact `endswith`.
5. A second turn on the same open worry: no second line. Test in Task 1.

---

### Task 1: The rule and the line

**Files:**
- Modify: `backend/mani/chat/safety.py` (`danger_of`), `backend/mani/chat/judged.py` (`Judged`, `judge`),
  `backend/mani/chat/crisis.py` (`BODY_EMERGENCY`), `backend/mani/chat/turn.py` (`_apply`, its trace)
- Test: `backend/tests/unit/test_safety.py`, `backend/tests/unit/test_judged.py`,
  `backend/tests/integration/test_turn.py`

**Interfaces:**
- Produces: `crisis.BODY_EMERGENCY: str`; `Judged.body_emergency: bool` (code raised this turn to danger on a body
  worry the model judged below danger); trace key `body_emergency: True` when the line was added.

- [ ] **Step 1: Write the failing unit tests.** In `test_safety.py`, replace
  `test_a_symptom_in_the_body_is_danger_only_when_they_said_it_is_happening_now` with
  `test_a_body_worry_that_has_not_stopped_is_danger_now`:
  `danger_of("now","body","yes")=="now"`, `danger_of("now","body","unsaid")=="now"`,
  `danger_of("unsure","body","unsaid")=="now"`, `danger_of("unsure","body",None)=="now"`,
  `danger_of("now","body","no")=="unsure"`, `danger_of("none","body","unsaid")=="none"`,
  `danger_of("now","themselves",None)=="now"`; and in
  `test_a_settled_symptom_reopens_only_when_their_newest_message_says_it_is_happening` change the last assert to
  `danger_of("now","body","unsaid")=="now"` ("a worry that never settled gets the number"). In `test_judged.py`,
  `test_code_raises_a_body_worry_the_model_held_lower_and_says_so`: from CLEAR, `Safety(level="unsure", about="body",
  symptom_now="unsaid")` gives `state_after DANGER` and `body_emergency True`; `Safety(level="danger", about="body",
  symptom_now="yes")` gives `body_emergency False`; from DANGER with the unsure read, `body_emergency False`.
- [ ] **Step 2: Run them.** `cd backend && source .venv/bin/activate && pytest tests/unit/test_safety.py
  tests/unit/test_judged.py -q`. Expected: the new asserts FAIL.
- [ ] **Step 3: Implement.** `danger_of`, when not `reopening`: `about == "body"` and `danger in ("now","unsure")` and
  `symptom_now != "no"` returns `"now"`; `about == "body"`, `danger == "now"`, `symptom_now == "no"` returns `"unsure"`;
  the `reopening` branch is unchanged. Update its docstring (what it does now, with muhammad 2026-11-18 as the reason).
  `judge`: `body_emergency = read.about == "body" and read.level != "danger" and state_after is DANGER and before is
  not DANGER`.
- [ ] **Step 4: Run them.** Same command. Expected: PASS.
- [ ] **Step 5: Write the failing integration tests** in `test_turn.py`:
  `test_a_body_worry_the_model_held_lower_still_gets_call_now`: a scripted reply `said("That needs checking soon.",
  safety=Safety(level="unsure", about="body", symptom_now="unsaid"))` → `turn.content.endswith("\n\n" +
  crisis.BODY_EMERGENCY)`, the thread's safety is `danger`; a second message on the same worry with the same read →
  the reply does not end with the line. `test_a_body_danger_the_model_judged_itself_goes_out_as_written`:
  `level="danger", about="body", symptom_now="yes"` → `turn.content == "Call your emergency number now."`.
  `test_a_pausing_body_turn_sends_only_the_pause_reply`: before DANGER via an earlier turn, then
  `Safety(level="danger", about="body", symptom_now="yes", declined=True)` → content is the pause reply and does not
  contain `BODY_EMERGENCY`.
- [ ] **Step 6: Run them.** `pytest tests/integration/test_turn.py -q`. Expected: the first FAILS.
- [ ] **Step 7: Implement.** `crisis.BODY_EMERGENCY` with the constraint's wording and a comment (ours until the client
  supplies hers). In `_apply`, after the pause/end-check/text choice and before `without_dashes`: when
  `judgment.body_emergency and not judgment.pausing`, the text is `f"{text}\n\n{crisis.BODY_EMERGENCY}"`; the trace
  gets `"body_emergency": True`. Add `("body_emergency", "Call-now line added")` to chat-tester `trace_view._ORDER`.
- [ ] **Step 8: Run the whole suite.** `pytest -q` and the chat-tester suite. Expected: all pass.
- [ ] **Step 9: Commit.** `git commit -m "Tell every body worry that has not stopped to call emergency services now"`

### Task 2: The prompt, the gate and the records

**Files:**
- Modify: `backend/content/prompts/mani.md` (the Safety line beginning "For pain in the body"),
  `backend/PORT-STATUS.md` (the body-symptom part of the safety entry, in place),
  `mani-vault/Journal/audit-of-the-safety-branch-2026-11-11.md` (superseded line),
  `backend/content/prompts/mani.md` is reseeded with `python scripts/seed.py`

- [ ] **Step 1: Swap the prompt line** for: `- For pain or another symptom in the body that could be an emergency and
  has not stopped, tell them plainly, once, to call their local emergency number now, without first asking whether it
  is happening. If they say it has stopped, say once that it is worth getting checked soon.`
- [ ] **Step 2: Run the gate side by side.** Save `git show HEAD:backend/content/prompts/mani.md` to the scratchpad as
  the baseline; run `python evals/run_eval.py --label body-before --prompt <baseline>` and `python evals/run_eval.py
  --label body-after` together. Expected: body-after no more than 0.15 below body-before, every rule passing in
  body-after (rule-chest included). If rule-chest still fails, that is the model's own level; record it, since the code
  line is what reaches the person.
- [ ] **Step 3: Run the conversation suite.** `python evals/check_suite.py`. Expected: exit 0.
- [ ] **Step 4: Records.** PORT-STATUS: the sentence "A symptom in the body is danger only when they said it is
  happening now ..." in the safety entry becomes "A symptom in the body that has not been said to have stopped is
  danger now, and when the model judged it lower code adds the call-now line (muhammad, 2026-11-18)", with the reason
  (MiniMax hedged 7 of 30 chest runs on 2026-11-18) and the pointers (`safety.danger_of`, `crisis.BODY_EMERGENCY`, the
  Task 1 tests). Journal: `> Superseded 2026-11-18 (a body symptom held at unsure until they say it is now) — see
  [[body-emergency-every-time-2026-11-18]]`, and write that note: the drift, the isolation runs A, B, C and the host
  probe, the decision.
- [ ] **Step 5: Reseed and run the suite.** `python scripts/seed.py && pytest -q`. Expected: pass.
- [ ] **Step 6: Commit.** `git commit -m "Send the emergency number for a body worry without asking first, and record why"`
