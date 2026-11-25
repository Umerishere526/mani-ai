> **Historical** (marked 2026-11-25): a design or plan as written at the time; parts no longer match the code (the return check after a pause, for one, is gone). What the backend does today is in `backend/PORT-STATUS.md`.

# Supportive and Reflective build up to the highlight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** In Supportive and Reflective, a reply's depth and length grow with what the person has told Mani, and the
highlight waits until they have laid it out.

**Architecture:** Prompt only, approach A. The lines in `mani.md` that force an early insight and a flat length are
replaced, never stacked on. The eval gains word-count checks and three rule cases, and the gate compares the old and
new prompt in the same session.

**Tech Stack:** Markdown prompt seeded into `admin.prompts`, Python eval (`backend/evals/run_eval.py`), pytest.

**Spec:** `docs/superpowers/specs/2026-11-18-supportive-reflective-build-up-design.md`

## Global Constraints

- **Directive does not change.** Its "In Directive, one or two, never more" line, its "always short: three or four
  short sentences" line, its first-reply text and its examples stay as they are.
- **No code decides when the highlight comes,** and nothing counts messages (approaches B and C are out).
- **Word bands, from the spec:**
  - About 60 to 110 words while Mani is still learning what happened.
  - Up to about 150 when the first message is long and detailed.
  - About 150 to 250 once they have laid it out.
- **When the highlight comes:** once they have said what happened, what it does to them, and something of what it
  means to them. Mani judges that from their words, never from a count.
- **Anti-goal:** early replies stay specific to what they said, never a stock "tell me more".
- **Prompt voice:** no dashes and no semicolons in the prompt's sentences, matching the file. Any example is about
  someone else and is never copied from `evals/cases.json`.
- **Repo rules:** an ABOUTME header on any new code file, no temporal words, and no orphans.
- **Never merge, push or open a PR.** Commit per task on `feat/one-call-turn`.

## Review Focus

1. **A long, detailed first message** must still allow a short reading that links things they said, as the
   client's `colleague-1` reference does. The rewrite must not ban every observation on reply 1. The quality gate's
   `colleague-1` and `cover-1` cases cover this (Task 3, Step 6).
2. **Directive leaking.** A replaced line that loses its "In Supportive and Reflective" scope changes Directive.
   Covered by the existing Directive rule cases in the same eval run (Task 3, Step 6).
3. **Early replies going generic.** This was the reason for the 2026-11-17 overrule. Covered by the judge on
   `rule-sr-first-reply-builds*`, which requires one specific observation, and by the quality gate's `understanding`
   score.
4. **The highlight never arriving** after they have laid it out. Covered by `rule-sr-highlight-when-laid-out`.
5. **Contradicting leftovers.** Any line that still asks for an early reading or the 120 to 220 band. Covered by the
   grep in Task 3, Step 3.

---

### Task 1: Word-count checks in the eval

**Files:**
- Modify: `backend/evals/run_eval.py` (`rule_checks`, beside `max_sentences`)
- Test: `backend/tests/unit/test_eval_checks.py`

**Interfaces:**
- Produces: the case `checks` keys `max_words: int` and `min_words: int`. A word is a whitespace-separated token of
  `got["text"]`. The failure strings are exactly `"{n} words > {max}"` and `"{n} words < {min}"`.

- [ ] **Step 1: Write the failing test** in `tests/unit/test_eval_checks.py`, and update the file's ABOUTME so it
  also names word limits.

```python
def test_a_reply_outside_its_word_limits_fails():
    six = "That sounds hard. What happened next?"  # 6 words
    assert run_eval.rule_checks({"checks": {"max_words": 6}}, {"text": six}) == []
    assert run_eval.rule_checks({"checks": {"max_words": 5}}, {"text": six}) == ["6 words > 5"]
    assert run_eval.rule_checks({"checks": {"min_words": 7}}, {"text": six}) == ["6 words < 7"]
```

- [ ] **Step 2: Run it**

Run: `cd backend && source .venv/bin/activate && pytest tests/unit/test_eval_checks.py -v`
Expected: the new test FAILS (`[] != ['6 words > 5']`), and the two existing tests pass.

- [ ] **Step 3: Add `max_words` and `min_words` to `rule_checks`** in `evals/run_eval.py`, in the same style as the
  `max_sentences` check, using `len((got.get("text") or "").split())`.

- [ ] **Step 4: Run it**

Run: `pytest tests/unit/test_eval_checks.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/evals/run_eval.py backend/tests/unit/test_eval_checks.py
git commit -m "The eval checks a reply's word count"
```

### Task 2: Three rule cases

**Files:**
- Modify: `backend/evals/cases.json` (append to `rules`)

**Interfaces:**
- Consumes: `max_words` and `min_words` from Task 1.
- Produces: the case ids `rule-sr-first-reply-builds`, `rule-sr-first-reply-builds-reflective` and
  `rule-sr-highlight-when-laid-out`.

- [ ] **Step 1: Append the two first-reply cases.**
  - Same shape as `rule-first-reply-no-core`: `reference: null`, `samples: 5`.
  - Styles are `Supportive` (opener `"How can I support you today?"`) and `Reflective` (opener `"What's on your mind
    today?"`).
  - One user turn: `"my co workers keep on blabbering and i can't focus"`.
  - `facts`: the production first-message facts, taken from code and not retyped: `[facts.NO_OFFER, "Give this
    conversation a title."]`.
  - `checks`:

```json
{"max_words": 120, "action_not": "offer",
 "judge": "The reply reflects what they said in their own terms, notices at most one small thing drawn only from their words, and asks one question. It does NOT say what is at stake for them beyond their words, such as a fear of being disliked or seen as a complainer, having to prove their place, or being judged. It is specific to what they said, not a generic invitation to say more."}
```

- [ ] **Step 2: Append `rule-sr-highlight-when-laid-out`.**
  - Style `Supportive`, `samples: 5`, `facts: []` (their fourth message, so no NO_OFFER).
  - The history is invented, about someone else, and not the client's partner chat. It has four user turns and three
    assistant turns that are short, build up and give no highlight.
  - By the fourth user turn the person has said what happened (for example, a friend keeps cancelling plans at the
    last minute), what it does to them (they sit at home feeling foolish, stop suggesting plans), and something of
    what it means to them (they wonder if they matter less to the friend than the friend does to them).
  - `checks`:

```json
{"min_words": 150, "action_not": "offer",
 "judge": "The reply gives one clear highlight: what may really be at stake for them beyond the cancelled plans themselves, held as a possibility they can correct, never stated as a fact. It says this once and does not list several readings."}
```

- [ ] **Step 3: Check the file loads and the cases are well formed**

Run: `cd backend && python3 -c "import json; d=json.load(open('evals/cases.json')); ids=[c['id'] for c in d['rules']]; assert len(ids)==len(set(ids)); print([c['id'] for c in d['rules'] if c['id'].startswith('rule-sr')])"`
Expected: the three new ids are printed, with no assertion error.

- [ ] **Step 4: Commit**

```bash
git add backend/evals/cases.json
git commit -m "Eval cases: Supportive and Reflective build up to the highlight"
```

### Task 3: The prompt builds up

**Files:**
- Modify: `backend/content/prompts/mani.md`
- Reseed: `backend/scripts/seed.py`

**Interfaces:**
- Consumes: the cases from Task 2.

- [ ] **Step 1: Save the baseline prompt** for the gate, before any edit:
  `git show HEAD:backend/content/prompts/mani.md > /private/tmp/claude-501/-Users-mac-Desktop-mani-ai/08ae314c-7029-477c-adfe-bf2d7a355e22/scratchpad/mani-baseline.md`

- [ ] **Step 2: Edit `mani.md`.** Replace these lines, and add nothing that contradicts what is left.
  - **"How you listen".** Replace the bullet starting "Every reply gives them something they did not say
    themselves" with a bullet that keeps its four kinds of help and adds a progression:
    - Say their words back is still never enough.
    - In Supportive and Reflective, early on that something is small and drawn only from their own words.
    - Readings go deeper as they tell more.
    - What is really at stake for them waits until they have said what happened, what it does to them and something
      of what it means to them, judged from their words, never from a count of messages.
  - **"What a good reply gives", the lead-in.** "In Supportive and Reflective, most replies do two or three of these"
    becomes: early on, one, drawn from their words, and more (two or three) once they have told you more. The
    Directive sentence stays.
  - **"Something to highlight".** Add that in Supportive and Reflective it comes only after that build-up. Keep "One
    per reply at most."
  - **"How a reply looks".** Replace "In Supportive and Reflective, usually 120 to 220 words. Longer when something
    heavy has come up, shorter when they just need a moment of acknowledgment." with the growing band from Global
    Constraints, keeping the "shorter when they just need a moment of acknowledgment" sense.
  - **The first-reply paragraph** ("Your first reply reflects what they said…") and the flatmate example.
    - Scope the paragraph to all styles as now, and add that in Supportive and Reflective the first reply makes no
      reading about what is at stake. It reflects, notices one small thing from their words, and asks.
    - Replace the flatmate example with a fresh example of a short opener answered in about 60 to 90 words: reflect,
      one small observation from their words, then one question (options each with a reason is fine). It is about
      someone else and not copied from `evals/cases.json`.
    - Introduce the babysitting example as a later reply, once they have said more. It stays as the example where
      the build-up ends.
  - **"Finding the core".** "Don't hold back once you see it, and don't rush to it before they feel understood" stays.
    Add that in Supportive and Reflective "understood" means the build-up above.

- [ ] **Step 3: Check that no contradiction is left**

Run: `cd backend && grep -n "120 to 220\|Every reply gives\|most replies do two or three\|dishes\|landlord" content/prompts/mani.md`
Expected: no output.

Run: `grep -c "In Directive" content/prompts/mani.md` before and after the edit.
Expected: the same count both times.

- [ ] **Step 4: Run the unit suite**

Run: `cd backend && source .venv/bin/activate && pytest -q 2>&1 | tail -3`
Expected: all pass, with clean output.

- [ ] **Step 5: Reseed**

Run: `cd backend && source .venv/bin/activate && python scripts/seed.py`
Expected: the mani prompt is reported as updated, and no error.

- [ ] **Step 6: The gate.** Run baseline and new in the same session; scores from different days don't compare.

Run: `cd backend && source .venv/bin/activate && python evals/run_eval.py --prompt /private/tmp/claude-501/-Users-mac-Desktop-mani-ai/08ae314c-7029-477c-adfe-bf2d7a355e22/scratchpad/mani-baseline.md --label sr-baseline > /private/tmp/claude-501/-Users-mac-Desktop-mani-ai/08ae314c-7029-477c-adfe-bf2d7a355e22/scratchpad/sr-baseline.txt 2>&1; python evals/run_eval.py --label sr-build-up > /private/tmp/claude-501/-Users-mac-Desktop-mani-ai/08ae314c-7029-477c-adfe-bf2d7a355e22/scratchpad/sr-new.txt 2>&1`

Expected:
- In `sr-new`, the Supportive and Reflective quality means are at least the baseline's minus 0.15.
- Each of the three `rule-sr-*` cases passes at least 4 of 5.
- Every rule case that passed in the baseline still passes in `sr-new`, Directive cases included.

If the gate fails, use superpowers:systematic-debugging. Read the failing replies in
`evals/results/*-sr-build-up/current-replies.md` before changing a line, and change one line at a time.

- [ ] **Step 7: Commit** with the eval numbers (baseline and new, both styles, and the rule pass counts) in the
  message body.

```bash
git add backend/content/prompts/mani.md
git commit -m "Supportive and Reflective build up to the highlight, and replies grow as they tell more"
```

### Task 4: Records

**Files:**
- Create: `docs/client/messages/2026-11-18-supportive-reflective-build-up.md`
- Modify: `docs/client/requirements.md`, `backend/PORT-STATUS.md`
- Create: `mani-vault/Journal/highlight-came-before-the-build-up-2026-11-18.md`

- [ ] **Step 1: The client message file.** Write the client's words as muhammad relayed them on 2026-11-18, word for
  word: "the client like the yappyness and the conversation but they are sayiing its give the highlight too quickly
  it should let the user build up to that before the giving that. The external connection that we models is making
  is very good but we need to build the conversation up to that point. get more yappy as the comversation grows in
  supportive and reflective style." Add muhammad's ruling: "yes, reverse it for supportive and reflective" (the R73
  overrule).

- [ ] **Step 2: `requirements.md`.**
  - Add row R123: "In Supportive and Reflective the highlight comes once the person has built up to it, and replies
    grow longer as the conversation grows." Link the message file, status in-progress, and name the eval cases.
  - Update the R73 row: the overrule is reversed for Supportive and Reflective by muhammad on 2026-11-18, and stays
    in force for Directive.
  - Update its Conflicts row to match.

- [ ] **Step 3: `PORT-STATUS.md`, Decisions in force.**
  - Add the bold line "In Supportive and Reflective a reply builds with what they have told: early replies reflect
    and notice one thing, the highlight waits until they have said what happened, what it does to them and what it
    means, and replies grow longer."
  - Follow it with the line `Because the client found the highlight came too early and asked for replies that grow (2026-11-18).`
  - Then pointers: `rule-sr-first-reply-builds`, `rule-sr-first-reply-builds-reflective`,
    `rule-sr-highlight-when-laid-out`, and `content/prompts/mani.md`.

- [ ] **Step 4: The journal note.** Frontmatter `summary:` and a `failed:` line: "Tried an insight in the first
  reply (the R73 overrule, 2026-11-17); failed because the client found the highlight came before the person built
  up to it". The body covers the cause (the flatmate example and the two rules), the evidence (the three chats and
  the client's reference lengths), and links to [[directive-replies-ran-long-and-definitive-2026-11-18]].
  - Ruling: no journal note argued for the overrule (grep found none). Its reason is in the requirements' Conflicts
    row, so no `> Superseded` line is needed.

- [ ] **Step 5: Check the digest accepts the files**

Run: `python3 .claude/hooks/digest.py --check mani-vault/Journal/highlight-came-before-the-build-up-2026-11-18.md backend/PORT-STATUS.md`
Expected: no output, exit 0.

- [ ] **Step 6: Commit**

```bash
git add docs/client mani-vault/Journal backend/PORT-STATUS.md
git commit -m "Record the client's build-up feedback and the R73 reversal for Supportive and Reflective"
```

### Task 5: Cleanup

- [ ] **Step 1:** Run `/simplify` over the branch diff for this plan's code (`evals/run_eval.py` and the test). Apply
  the fixes it finds, run the test file again, and commit if anything changed.
