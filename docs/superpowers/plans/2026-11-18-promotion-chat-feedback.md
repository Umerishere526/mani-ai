> **Historical** (marked 2026-11-25): a design or plan as written at the time; parts no longer match the code (the return check after a pause, for one, is gone). What the backend does today is in `backend/PORT-STATUS.md`.

# The Client's Feedback on the Directive Promotion Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Directive replies are short, open and specific; no reply states a reading as fact, repeats a point or makes
a causal claim the person hasn't made; the set never argues before D, opens with a bridge, and closes by offering a
practical next step.

**Architecture:** `mani.md` carries every behaviour change; `facts.py`'s feelings-check line asks about a next step;
the eval gains a sentence-count check and rule cases from the client's chat. Records follow.

**Tech Stack:** Python 3.14, pytest, `backend/.venv`; prompt Markdown.

**Spec:** `docs/superpowers/specs/2026-11-18-promotion-chat-feedback-design.md`

## Global Constraints

- Branch `feat/one-call-turn`, `/Users/mac/Desktop/mani-ai`; commit per task; never merge, push or open a PR.
- Directive only: one or two points (1), no pick-from-three question (5), step A one specific recent event (7).
  Supportive and Reflective keep their length, their possibilities questions and their activating event.
- All styles: readings as possibilities (2), no arguing with the belief before D inside the set (3; the chat may still
  offer a fair perspective), each point once (4), a bridge sentence before the first stage's line (6), a next-step
  question after the feelings answer with the closing buttons kept (8), no causal claim the person hasn't made.
- Directive length is fixed by removing the contradicting lines (option 1); no code length check.
- No eval or live call can run (credits exhausted); the gate runs when credits are back.
- Every `mani.md` wording is the builder's; examples never reuse this chat's details (the prompt's own rule).

## Review Focus

1. The bridge versus "Never narrate the set": a bridge before the first line only; between stages narration stays
   banned. Test: `rule-start-bridge` (Task 2) checks `max_sentences` and that B is not reached.
2. A feelings check held for safety must not ask about a next step. Test in Task 1.
3. The Start reply in Directive (bridge, line, question) stays within four sentences. Test: `rule-start-bridge`.
4. The sentence count on text with a question inside quotes or an ellipsis: counted once per sentence. Test in Task 2.
5. Supportive and Reflective unchanged: the 0.15 gate over those styles when credits return (Task 2, Step 6).

---

### Task 1: The prompt and the feelings-check line

**Files:**
- Modify: `backend/content/prompts/mani.md`, `backend/mani/chat/facts.py` (`_running_line`, the `FEELINGS` branch)
- Test: `backend/tests/unit/test_facts.py`

**Interfaces:**
- Produces: the unheld feelings-check fact names "a practical next step" and no longer says "ask nothing"; it still
  says code closes the set and shows the closing buttons. Task 2 copies its exact text into `rule-after-check`.

- [ ] **Step 1: Write the failing tests.** In `test_facts.py`, rename
  `test_the_last_stage_asks_how_they_feel_and_the_check_in_asks_nothing` to
  `test_the_last_stage_asks_how_they_feel_and_the_check_in_offers_a_next_step`; `check_in` asserts
  `"how they feel" in check_in and "practical next step" in check_in and "ask nothing" not in check_in and "is for" not in check_in`.
  In `test_a_held_feelings_check_is_about_their_safety_and_promises_no_close`, add `"next step" not in held`.
- [ ] **Step 2: Run them.** `cd backend && source .venv/bin/activate && pytest -q tests/unit/test_facts.py`.
  Expected: the renamed test FAILS on "practical next step"; the held test passes.
- [ ] **Step 3: The facts line.** The `FEELINGS` unheld text: answer how they feel warmly in a sentence or two (in
  Directive, one), carrying the new way of seeing it forward, then ask whether they'd like to think about a practical
  next step for what they are facing; recap nothing; code closes the set and shows the closing buttons.
- [ ] **Step 4: `mani.md`**, each edit by its point:
  - (2) Delete the "How you listen" bullet "Your first reply shows you understood…" (it contradicts the first-reply
    paragraph in "How a reply looks"). In that paragraph's flatmate example, the "isn't really about the dishes" reading
    becomes a possibility, not a statement. "What a good reply gives" says every reading is a possibility they can
    correct, never stated as fact ("That is the core of it", "This is really about…").
  - (4) and causal claims: "What a good reply gives" also says never make a point already made in this conversation
    again, in other words either, and never say what caused something or that it made things worse unless they said
    it, least of all in a way that makes it their fault.
  - (1) "Most replies do two or three of these" becomes Supportive and Reflective; Directive does one or two.
  - (5) The possibilities question is for Supportive and Reflective; Directive asks one plain open question.
  - (1) "How a reply looks": "Usually 120 to 220 words…" is for Supportive and Reflective; Directive keeps "three or
    four short sentences at most". Add one Directive example of three or four sentences (someone else's situation).
  - (1) "Inside the set": "usually 60 to 120 words" is for Supportive and Reflective.
  - (3) "Inside the set" gains: before D, never argue with the belief, reassure them it is untrue, or say what doesn't
    fit it; at A, B and C you understand it, and examining it is D's work.
  - (6) The reply that starts the set says one short sentence that takes them from the chat to one moment, then the
    first line and its question. "Never narrate the set" stays for every later reply.
  - (7) In Directive, A asks for one specific, recent moment, not a summary of the whole pattern.
  - (8) The closing bullets: after a warm sentence, ask whether they want to think about a practical next step; if
    they do, help in practical terms. "How you listen"'s "Practical help comes after the set of questions, when they
    ask for it" says the set's close offers it.
- [ ] **Step 5: Run the suite.** `python scripts/seed.py && pytest -q`. Expected: all pass. Then
  `grep -n "120 to 220\|60 to 120\|two or three of these\|Your first reply shows" content/prompts/mani.md`.
  Expected: each remaining hit names Supportive and Reflective; no "Your first reply shows".
- [ ] **Step 6: Commit.** `git commit -m "Directive says less and asks openly; no arguing before D; the set closes on a next step"`

### Task 2: The eval

**Files:**
- Modify: `backend/evals/run_eval.py` (`sentences`, `rule_checks`), `backend/evals/cases.json`
- Create: `backend/tests/unit/test_eval_checks.py`

**Interfaces:**
- Consumes: Task 1's exact feelings-check fact (from `facts._running_line(<abcde>, "feelings_check", held=False)`).
- Produces: `run_eval.sentences(text: str) -> int`; the rule check `max_sentences: int`, failing with
  `"<n> sentences > <max>"`.

- [ ] **Step 1: Write the failing tests** in `test_eval_checks.py`:
  `test_a_directive_reply_over_four_sentences_fails`: `rule_checks({"checks": {"max_sentences": 4}}, {"text": t})`
  is `[]` for "That makes sense. A is for Activating Event. What happened?" and names "5 sentences > 4" for a
  five-sentence text. `test_a_quoted_question_and_an_ellipsis_count_once`: `sentences('He said "why me?" and left...
  Then what?') == 2`.
- [ ] **Step 2: Run them.** `pytest -q tests/unit/test_eval_checks.py`. Expected: FAIL (no `sentences`).
- [ ] **Step 3: Implement** `sentences`: a sentence ends at a run of `.`, `?` or `!` (closing quotes included) that is
  followed by whitespace or the end; count non-empty pieces. `rule_checks` adds `max_sentences`.
- [ ] **Step 4: Run them.** Expected: PASS.
- [ ] **Step 5: The cases.** First record the chat: `docs/client/messages/2026-11-18-promotion-chat-feedback.md`, the
  whole Directive chat and the client's review reply by reply, with muhammad's answers (styles per point). Then the
  cases, all Directive, `"samples": 5`, turns taken from that chat, facts as the code gives them for that moment:
  - `rule-directive-short`: history to "I think they're more confident…"; `max_sentences: 4`; judge: one or two
    points, then one open question; no reading stated as fact; no point the history already made.
  - `rule-directive-open-question`: history to "Honestly, I don't even know anymore…"; `max_sentences: 4`; judge: one
    open question, never a choice between listed options.
  - `rule-start-bridge`: history through the lead-in, "Not sure", the five steps, "Start ABCDE"; `stage_in: [activate]`,
    `text_excludes: ["B is for Belief"]`, `max_sentences: 4`; judge: a short bridging sentence, "A is for Activating
    Event.", and a question for one specific recent moment, not a summary of the pattern.
  - `rule-no-dispute-at-b`: history through the B question and "I think I told myself that I'm just not good
    enough…", ABCDE running at `belief`; `stage_in: [belief, consequence]`, `max_sentences: 4`; judge: no arguing
    with the belief, no reassurance that it is untrue, nothing said about what doesn't fit it.
  - `rule-after-check` (existing): its facts line becomes Task 1's text; `no_question` goes; judge: a warm one-sentence
    close, then a question about a practical next step; no recap.
- [ ] **Step 6: Run.** `pytest -q` and `python evals/run_eval.py --help`. Expected: pass; the eval loads its cases.
  The gate (`run_eval.py` over every case; Supportive and Reflective within 0.15 of the committed prompt; every run of
  every rule passes) waits for credits: say so in the ledger, never as passed.
- [ ] **Step 7: Commit.** `git commit -m "The eval counts Directive sentences and checks the client's promotion chat"`

### Task 3: Records

- [ ] **Step 1.** `docs/client/requirements.md`, citing the message Task 2 recorded: new rows for points 2, 3, 4, 6, 7, 8 and
  the causal-claim rule; R83 upheld for Directive and still overruled for Supportive and Reflective; R94 and R105
  upheld after a set; the Conflicts row for R83 and R94/R105 updated. `backend/PORT-STATUS.md` Decisions in force,
  edited in place: the Directive entry (one or two points, open question, A one event; why the length rule failed),
  the feelings-check entry (the next-step question); new entries for no arguing before D and the bridge. A journal
  note on why the replies ran long and definitive (the menu, the contradicting lengths, the eval rewarding "adds
  something"), with `summary:` and `failed:`.
- [ ] **Step 2.** `pytest -q` and `python3 ../.claude/hooks/digest.py --check ../backend/PORT-STATUS.md
  ../mani-vault/Journal/*.md`. Expected: pass; nothing printed.
- [ ] **Step 3: Commit.** `git commit -m "Record the client's promotion-chat review and muhammad's answers"`
