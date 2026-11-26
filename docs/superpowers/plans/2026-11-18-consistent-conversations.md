> **Historical** (marked 2026-11-25): a design or plan as written at the time; parts no longer match the code (the return check after a pause, for one, is gone). What the backend does today is in `backend/PORT-STATUS.md`.

# The Same Opening Gets the Same Kind of Conversation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Code refuses an offer before the person's 3rd message and on a turn that corrects Mani; the first reply never
declares a core belief; the chat runs at temperature 0.3; the gate checks these moments five times each.

**Architecture:** `decide` gains the two refusals, fed by a count of the person's messages and a `corrected` field on
the reply; `facts` says before the call that no offer is allowed yet; `mani.md` changes its first-reply guidance and
temperature; the eval gains per-case sample counts and three rule cases.

**Tech Stack:** Python 3.14, FastAPI, pydantic, pytest; `backend/.venv`.

**Spec:** `docs/superpowers/specs/2026-11-18-consistent-conversations-design.md`

## Global Constraints

- Branch `feat/one-call-turn`, `/Users/mac/Desktop/mani-ai`; commit per task; never merge, push or open a PR.
- The floor: no offer before the person's 3rd message; the style tap is not one of their messages.
- Temperature 0.3 for the chat, in `mani.md`'s `model_parameters`.
- The gate: the committed prompt (0.7) then the new one (0.3), one after the other; the 0.15 mark over Supportive and
  Reflective; every rule run passes; `check_suite.py` exits 0.

## Review Focus

1. A tap on a framework button counts as one of their messages: the floor counts what they sent, typed or tapped,
   except the style tap. Test in Task 1.
2. A conversation that started before this change with an offer already open: the floor never closes an offer already
   made. Test in Task 1.
3. A refused early offer: no buttons, no offer row, and the next turn may offer normally. Test in Task 1.
4. `corrected` on a turn inside a running set: changes nothing but the offer. Test in Task 1.
5. Temperature 0.3 brings back stock phrases: the gate's phrase count. Task 2.

---

### Task 1: The offer floor and the correction guard

**Files:**
- Modify: `backend/mani/chat/reply.py` (`TurnReply.corrected`), `backend/mani/chat/decide.py` (`OFFER_FROM_MESSAGE`,
  `decide(..., person_messages: int)`), `backend/mani/chat/facts.py` (`facts(..., person_messages: int)`),
  `backend/mani/chat/turn.py` (count and pass it)
- Test: `tests/unit/test_reply.py`, `tests/unit/test_decide.py`, `tests/unit/test_facts.py`,
  `tests/integration/test_turn.py`, `tests/integration/test_record_migration.py` (its `decide` call)

**Interfaces:**
- Produces: `TurnReply.corrected: bool = False` ("True when their latest message corrects something you said or
  understood about them"); `decide.OFFER_FROM_MESSAGE = 3`; `decide.decide(..., person_messages)`, refusing an offer
  (`refused="offer"`, no prompts, no row) when `person_messages < OFFER_FROM_MESSAGE` or `reply.corrected`;
  `facts.facts(..., person_messages)` adding `NO_OFFER` when `person_messages < OFFER_FROM_MESSAGE`.

- [ ] **Step 1: Write the failing tests.** `test_reply.py`: the strict schema includes `corrected`. `test_decide.py`:
  an offer with `person_messages=1` and `2` is refused with no prompts and no technique; with `3` it shows the lead-in
  buttons; an offer with `reply(corrected=True)` at `person_messages=5` is refused; `corrected=True` on a running set's
  stage reply moves the stage as before; an open offer from before (`open_offer=offered("abcde")`) with
  `person_messages=1` still shows the steps (the floor never closes an offer already made). `test_facts.py`:
  `person_messages=2` carries "You cannot offer"; `3` with nothing open does not. `test_turn.py`
  `test_an_offer_on_the_persons_second_message_is_refused_and_the_next_may_offer`: a scripted offer on their 2nd
  message has no buttons and no technique row, a scripted offer on their 3rd shows the lead-in buttons; the count
  counts a tapped framework button and not the style tap.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement.** `turn._turn` counts the person's messages as the user messages in the history after the
  first one (the style tap) plus this one, and passes it to `facts` and `decide`. In `decide._offer`, the refusal joins
  the existing `blocked` conditions.
- [ ] **Step 4: Run the suite.** `pytest -q`. Expected: all pass.
- [ ] **Step 5: Commit.** `git commit -m "Refuse an offer before their 3rd message or right after they correct Mani"`

### Task 2: The first reply, the temperature and the gate

**Files:**
- Modify: `backend/content/prompts/mani.md` (frontmatter `temperature: 0.3`; "How a reply looks" and its first-reply
  example; "What you fill in" gains `corrected`), `backend/evals/run_eval.py` (a case may set `samples`),
  `backend/evals/cases.json` (three rule cases)

- [ ] **Step 1: The prompt.** First reply: reflect what they said in their own terms and ask; any reading is one gentle
  possibility put as a question, never a statement about what they believe or fear, never heavy words. Check the
  first-reply example matches. `corrected`: true when their latest message corrects something you said or understood.
- [ ] **Step 2: The eval.** `run_variant` uses `case.get("samples", samples)`. Rule cases, `"samples": 5`, Directive,
  the opening "I think I'm getting tired of always being the understanding friend...": `rule-first-reply-no-core`
  (judge: reflects and asks; names no core belief, fear or deep reading as a statement; no heavy words; at most one
  gentle possibility as a question), `rule-no-offer-after-correction` (history: the first chat's first reply, then "I
  don't think it's that I'm afraid they won't love me..."; checks `action_not: offer`, and code checks `corrected`
  true via a new `corrected` check), `rule-no-offer-on-second-message` (same history without the correction, a plain
  second message; `action_not: offer`, with the facts carrying `NO_OFFER`).
- [ ] **Step 3: Reseed and test.** `python scripts/seed.py && pytest -q`. Expected: pass.
- [ ] **Step 4: The gate.** The committed prompt saved as the baseline and run first, then the new one; each report's
  stock-phrase count. Expected: Supportive and Reflective no more than 0.15 below; every run of every rule passes in
  the new one. Then `python evals/check_suite.py`. Expected: exit 0.
- [ ] **Step 5: Commit.** `git commit -m "First reply reflects and asks; the chat runs at 0.3; the gate checks consistency"`

### Task 3: Records

- [ ] **Step 1.** `requirements.md`: the R73 conflict row says the first reply no longer names the pattern as a
  statement (muhammad, 2026-11-18). PORT-STATUS Decisions in force: the offer floor and the correction guard (new,
  with the 2026-11-16 removal's reason and why it no longer holds), temperature 0.3, the gate's consistency cases; the
  model entry's parameters. Journal: a note, and the superseded line on `offer-floor-and-coverage-removed-2026-11-16`
  (the floor part).
- [ ] **Step 2.** `pytest -q`. Expected: pass.
- [ ] **Step 3: Commit.** `git commit -m "Record the consistency guards and why the offer floor came back"`
