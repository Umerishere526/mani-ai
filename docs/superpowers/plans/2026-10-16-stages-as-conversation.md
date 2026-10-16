# Stages as Conversation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Inside ABCDE the walk moves only when a stage's purpose is met in substance, never by a counter; the person can be helped when stuck and can stop; the core issue keeps moving; the check comes the turn after control.

**Architecture:** The walk (`backend/mani/chat/walk.py`) stays code-owned and one stage per reply; what changes is the move rule (no automatic let-go, a stall limit that offers a choice, a `stopped` answer the orchestrator records as a decline) and the content that defines when C, D and E are met (`backend/content/frameworks/abcde.md`, with a `when_stuck` key sent in `[ctx]`). The understanding record gains `event` and a `core_issue` the model revises on any turn. `context.may_check` waits until all three steps are stored.

**Tech Stack:** FastAPI on Python 3.14 in `backend/.venv`, Pydantic 2 reply schema, pytest (unit; integration needs local Supabase), content seeded by `scripts/seed.py`.

**Spec:** `docs/specs/0007-stages-as-conversation/index.md` (the four decisions there are muhammad's; this plan assumes the recommended answers).

## Global Constraints

- Always `cd backend && source .venv/bin/activate` before any Python. Unit: `pytest tests/unit -q`. Integration: `pytest tests/integration/test_turn.py -q` (skips without the database).
- After any edit under `backend/content/`, `python scripts/seed.py` before a live run. The unit tests read the files directly.
- Commit messages carry no `Co-Authored-By` or assistant trailer (muhammad's rule). Run `git` from the repo root. Branch: `feat/reading-check-and-body-context` (current), or a new one off it if muhammad asks.
- Never log or store the person's words beyond the existing `said`/understanding fields; notes and logs name stage ids and statuses only.
- No scenario used to judge the prompt may appear in the prompt (journal, 2026-10-16). Lolly's two chats go in `scenarios.json` only.
- Names and comments say what a thing is for, never its history. Every code file keeps its two `ABOUTME:` lines.
- Max 150 lines per component is a frontend rule; here keep functions readable and `walk.py` under its current shape (no new module).

## Review Focus

1. A "yes" to a C confirmation that carries only what they did: the stage must come back as partial with gap `feeling`, never move to D. Pinned by `test_c_reached_with_only_what_they_did_asks_how_believing_it_left_them_feeling` (Task 3) for the content, and judged live (Task 6).
2. Four "I don't know" in a row on one stage: the fourth reply offers the choice; the fifth still does not move without an answer. Pinned by `test_a_plain_no_never_moves_the_stage_and_after_four_the_choice_is_offered` (Task 1).
3. `stopped` reported on the start turn (the OFFER_OPEN shape carries `stage_answer`): ignored, the walk opens on A. Pinned by `test_stopped_on_the_start_turn_is_ignored` (Task 1).
4. `stopped` beside a body answer at the closing: the body answer wins, nothing is declined. Pinned by `test_a_body_answer_at_the_closing_wins_over_stopped` (Task 1).
5. A control answer that carries something new (Lolly's "I choose nothing"): the reply to it must be an ordinary forward reply with no `check` field; the check field appears on the next message. Pinned by the rewritten `test_the_problem_its_core_issue_and_control_each_take_an_exchange_then_the_check_and_offer` (Task 5).

---

### Task 1: The walk never lets a stage go; a stall offers a choice; `stopped` is an answer

**Files:**
- Modify: `backend/mani/chat/walk.py` (`MOVES`, `HELD_FOR_QUESTIONS` area; `Walked`; `advance`; `next_line`)
- Modify: `backend/mani/llm/schema.py:238` (`StageAnswer`), `:331-343` (`stage_answer` description)
- Modify: `backend/mani/chat/context.py` (`_TWO_TRIES` and its `two_tries:` line in `_running_lines`)
- Test: `backend/tests/unit/test_walk.py`, `backend/tests/unit/test_chat_context.py`

**Interfaces:**
- Produces: `walk.STALL_LIMIT: int = 4`; `walk.STOPPED = "stopped"`; `Walked.stopped: bool = False`; `walk.advance(...)` returns `Walked(stopped=True)` on answer `"stopped"` with entries unchanged and note `f"{in_force} stopped by them"`; `walk.next_line(framework, entries, phase) -> str` whose stalled form starts `"They have stayed on {phase} for {tries} replies. Your text offers the choice: keep going with it, skip it (answer let_go), or stop the questions here (answer stopped). "`.
- `StageAnswer = Literal["agreed", "answered", "corrected", "let_go", "not_yet", "asked", "stopped"]`.

- [ ] **Step 1: Write the failing tests in `tests/unit/test_walk.py`**

Delete `test_a_plain_no_stays_once_and_the_second_lets_the_stage_go`. Rename and rewrite `test_on_a_second_try_the_stage_reached_is_said_back_from_the_judgement` to use `let_go` on the second call (same assertions, name `test_a_stage_let_go_reaches_the_next_said_back_from_the_judgement`). In `test_questions_hold_a_stage_only_so_long_then_count_as_tries`, replace the last assertion with:

```python
    again = walk.advance(abcde, tried.entries, None, "asked", in_force="effective")
    assert (again.phase, again.entries["effective"]["tries"]) == ("effective", 2)
```

Add:

```python
def test_a_plain_no_never_moves_the_stage_and_after_four_the_choice_is_offered(abcde):
    """Spec 0007, AC-1, AC-2: no counter moves a stage; at STALL_LIMIT the reply offers the choice."""
    entries: dict = {}
    for n in range(1, walk.STALL_LIMIT + 2):
        walked = walk.advance(abcde, entries, None, "not_yet", in_force="belief")
        entries = walked.entries
        assert (walked.phase, walked.reached, entries["belief"]["tries"]) == ("belief", None, n)
    assert not walk.next_line(abcde, {"belief": {"tries": walk.STALL_LIMIT - 1}}, "belief").startswith("They have stayed")
    stalled = walk.next_line(abcde, entries, "belief")
    assert stalled.startswith(
        f"They have stayed on belief for {walk.STALL_LIMIT + 1} replies. Your text offers the choice: "
        "keep going with it, skip it (answer let_go), or stop the questions here (answer stopped). "
    )
    assert "If not_yet, write the follow up for this stage, helped by stage_when_stuck when they don't know." in stalled


def test_stopping_the_questions_is_reported_and_moves_nothing(abcde):
    """Spec 0007, AC-3: the walk reports the stop and leaves the store as it was; the orchestrator records it."""
    stored = {"belief": {"said": "I am useless", "status": "known", "tries": 2}}
    walked = walk.advance(abcde, stored, None, "stopped", in_force="belief")
    assert (walked.phase, walked.reached, walked.stopped) == ("belief", None, True)
    assert walked.entries == stored
    assert walked.notes == ["belief stopped by them"]


def test_stopped_on_the_start_turn_is_ignored(abcde):
    started = walk.start(abcde, None, judged("missing"))
    assert (started.phase, started.reached, started.stopped) == ("activate", "activate", False)


def test_a_body_answer_at_the_closing_wins_over_stopped(abcde):
    walked = walk.advance(abcde, {}, None, "stopped", in_force="effective", body_answered=True)
    assert (walked.phase, walked.stopped) == ("somatic_checkin", False)
    assert "stage answer stopped ignored for a body answer" in walked.notes
```

- [ ] **Step 2: Run them to see them fail**

Run: `pytest tests/unit/test_walk.py -q`
Expected: the four new tests fail (`stopped` is read as an invalid answer / `Walked` has no `stopped`); the rewritten `asked` test fails on phase `somatic_checkin`.

- [ ] **Step 3: Implement in `walk.py`**

- Add `STALL_LIMIT = 4` and `STOPPED = "stopped"` next to `MOVES`, with one comment line each in the file's voice.
- `Walked`: add `stopped: bool = False`.
- `advance`: delete the `if not moved and tries >= 1:` block. Inside the non-body branch, after the `asked` hold, add: if `answer == STOPPED`, return `Walked(merged.entries, in_force, None, notes + [f"{in_force} stopped by them"], stopped=True)` without touching `tries`. `_counts` already returns True for it.
- `next_line`: drop the `tries >= 1` branch. Build `prefix = f"They have stayed on {phase} for {tries} replies. Your text offers the choice: keep going with it, skip it (answer let_go), or stop the questions here (answer stopped). " if tries >= STALL_LIMIT else ""`, and return `prefix + f"If you answer agreed, answered, corrected or let_go, {moved} If not_yet, write the follow up for this stage, helped by stage_when_stuck when they don't know. If stopped, say in one sentence that they can stop here; the two choices follow.{asked}"`.
- Update the `advance` docstring: a stage is never let go by code; a stall offers the choice.

- [ ] **Step 4: `schema.py`**

`StageAnswer` gains `"stopped"`. Rewrite the `stage_answer` description so `let_go` reads "they want to skip this stage, or a question made them uneasy", `stopped` reads "they want to stop the questions altogether, never a plain no or I don't know", and the words "because it was asked twice already" are gone.

- [ ] **Step 5: `context.py`**

Delete `_TWO_TRIES` and the `lines.append(f"two_tries: {_TWO_TRIES}")` line. In `tests/unit/test_chat_context.py`: remove `"two_tries"` from `_SELF_EXPLAINED`; in `test_what_they_said_per_stage_is_shown_from_the_store_on_every_stage_turn` replace the `If not_yet, write the follow up for this stage.` assertion with the new sentence from Step 3.

- [ ] **Step 6: Run the unit suite**

Run: `pytest tests/unit -q`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add backend/mani/chat/walk.py backend/mani/llm/schema.py backend/mani/chat/context.py backend/tests/unit/test_walk.py backend/tests/unit/test_chat_context.py
git commit -m "walk: no stage is let go by code; a stall offers the choice; stopped is an answer"
```

---

### Task 2: `stopped` records the run as declined and offers the two choices

**Files:**
- Modify: `backend/mani/chat/orchestrator.py:718-730` (right after `_walked` returns)
- Test: `backend/tests/integration/test_turn.py` (after `_land_on`, line ~1340)

**Interfaces:**
- Consumes: `Walked.stopped` (Task 1), `_handoff()`, `_decided_framework`, `TechniqueOutcome.DECLINED`.
- Produces: a `thread_technique_state` row with `outcome = declined`, `phase = null`, `at_message_count = count_after`, `stages_known` kept; reply prompts Chat More / Go to Library.

- [ ] **Step 1: Write the failing test**

```python
async def test_stopping_the_questions_keeps_what_was_said_and_offers_the_two_choices(alice, model):
    """Spec 0007, AC-3: the person ends the questions; the run is recorded as declined so the next check
    waits the short cooldown, and what they said stays stored."""
    model(Reply(text="We can stop the questions here.", stage_answer="stopped"))
    from mani.db import pool

    thread = await start(alice)
    known = {"abcde": {"activate": {"said": "the list", "status": "done", "tries": 0},
                       "belief": {"said": "I won't get it all done", "status": "known", "tries": 4}}}
    await _land_on(alice, thread.id, "belief", known)

    turn = await send(alice, thread.id, "I don't want to keep doing this")

    assert turn.content == "We can stop the questions here."
    assert [p.label for p in turn.prompts] == ["Chat More", "Go to Library"]
    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)
    assert (ctx.technique.outcome, ctx.technique.phase) == (TechniqueOutcome.DECLINED, None)
    assert ctx.technique.stages_known == known
    assert context.live(ctx.technique) is None
```

- [ ] **Step 2: Run it to see it fail**

Run: `pytest tests/integration/test_turn.py -q -k stopping_the_questions`
Expected: FAIL (prompts empty, outcome still accepted).

- [ ] **Step 3: Implement**

After `fixed, walked = _walked(...)` and the `stages_known` update, add:

```python
        if walked.stopped:
            # They ended the questions: recorded as a decline, so the next check waits the short
            # cooldown, and the two choices follow their own words (spec 0007, AC-3).
            outcome = TechniqueOutcome.DECLINED
            fixed = dataclasses.replace(
                fixed, framework_id=None, phase=None, prompts=_handoff(),
                notes=fixed.notes + ["questions stopped by them"],
            )
```

`_decided_framework(None, DECLINED, technique, None)` then names the live row, and the existing write stores `phase=None, at_message_count=count_after`. The `stages_known` statement runs after the upsert, so the store survives.

- [ ] **Step 4: Run the integration file**

Run: `pytest tests/integration/test_turn.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/mani/chat/orchestrator.py backend/tests/integration/test_turn.py
git commit -m "orchestrator: a stopped framework is recorded as declined with the two choices"
```

---

### Task 3: Content defines when C, D and E are met; `when_stuck` reaches `[ctx]`; the prompt says there is no count

**Files:**
- Modify: `backend/content/frameworks/abcde.md` (stages `belief`, `consequence`, `dispute`, `effective`)
- Modify: `backend/mani/chat/context.py:475-505` (`_stage_lines`)
- Modify: `backend/content/prompts/mani_base.md` (`in_a_framework`, `any_stage`), `backend/content/prompts/response_format.md` (reasoning step "The stage")
- Test: `backend/tests/unit/test_walk.py`, `backend/tests/unit/test_chat_context.py`

**Interfaces:**
- Produces: stage key `when_stuck: str` (optional), sent as `{prefix}_when_stuck`; `consequence.if_unclear` ids `feeling` and `doing` with `slot: belief`; `effective.if_unclear` id `fits` with `slot: effective`.

- [ ] **Step 1: Write the failing tests**

In `tests/unit/test_walk.py`:

```python
def test_c_reached_with_only_what_they_did_asks_how_believing_it_left_them_feeling(abcde):
    """Lolly, 2026-10-16: C is both how it left them feeling and what they did; one of the two is a gap."""
    entries = {"belief": {"said": "I won't get it all done", "status": "done", "tries": 0},
               "consequence": {"said": "so you don't start", "status": "partial", "gap": "feeling"}}
    assert walk._gap_line(abcde, entries, "consequence", "feeling") == (
        "And when you believe I won't get it all done, how does that leave you feeling?")
    assert walk._gap_line(abcde, entries, "consequence", "doing") == (
        "What do you do, or stop doing, once you believe I won't get it all done?")


def test_e_offered_a_new_belief_is_asked_whether_it_fits_before_it_is_done(abcde):
    """Lolly, 2026-10-16, point 7: a new belief is verified with them before the body check-in."""
    entries = {"effective": {"said": "I can still make progress on something", "status": "partial", "gap": "fits"}}
    assert walk._gap_line(abcde, entries, "effective", "fits") == (
        "So the thought would now be: I can still make progress on something. Does that fit for you?")
    effective, dispute = abcde.stages["effective"], abcde.stages["dispute"]
    assert "no different one" not in effective["ready_when"]
    assert effective["when_stuck"] and dispute["when_stuck"]
    assert "enough information" not in dispute["ready_when"]
```

In `tests/unit/test_chat_context.py` (its `framework()` is synthetic: add `"when_stuck": "Offer one distinction from their words."` to its `belief` stage):

```python
def test_a_stages_when_stuck_line_is_sent_for_the_stage_and_the_next():
    """Spec 0007, AC-4."""
    block = context.build(_running_at("activate"), framework=framework()).splitlines()
    assert "next_stage_when_stuck: Offer one distinction from their words." in block
    block = context.build(_running_at("belief"), framework=framework()).splitlines()
    assert "stage_when_stuck: Offer one distinction from their words." in block
```

- [ ] **Step 2: Run them to see them fail**

Run: `pytest tests/unit/test_walk.py tests/unit/test_chat_context.py -q`
Expected: the three new tests fail.

- [ ] **Step 3: `context._stage_lines`**

Change the field loop to `for field in ("purpose", "listen_for", "ready_when", "when_stuck"):`. Update the docstring's list of clinical fields.

- [ ] **Step 4: `abcde.md` stage edits (YAML, exact)**

`belief.reach`, append one sentence: `What they did because of it is not the belief; keep it for consequence.`

`consequence`:
```yaml
    purpose: "Identify how believing that affected what they felt and what they did or avoided."
    reach: "Report consequence as known only where they tied both a feeling and an action or avoidance to that belief. Where only one is there, report it as partial with that one in their words and the other as the gap: feeling when how it left them feeling is missing, doing when what they did or avoided is missing. A yes to your confirmation adds nothing."
    ready_when: "A feeling and a behaviour, each tied by them to the belief. Do not introduce either."
    if_unclear:
      - when: "consequence unclear - \"It affected everything.\""
        reply: "It affected everything. What changed first?"
      - id: feeling
        slot: belief
        when: "what they did is there and how believing it left them feeling is not"
        reply: "And when you believe <their belief>, how does that leave you feeling?"
      - id: doing
        slot: belief
        when: "how it left them feeling is there and what they did or avoided is not"
        reply: "What do you do, or stop doing, once you believe <their belief>?"
```

`dispute`:
```yaml
    ready_when: "What supports the belief and what might challenge it have both been looked at, and where the belief is joined to a conclusion they draw from it (\"I can't get it all done\" and \"so there is no point starting\"), the two have been pulled apart in their words. Not knowing for sure is not enough on its own."
    when_stuck: "When nothing comes to mind, help them look, from their own words. Offer one distinction: between the belief and the conclusion they draw from it, or between what they know and what they assume. Ask which is closer to what they tell themselves."
```
and the first `if_unclear` branch's reply becomes `"Nothing comes to mind yet, and that's fine. <one distinction from when_stuck, in their words, as a question>"`.

`effective`:
```yaml
    reach: "A plan or an action, such as raising it with someone, is not a new belief, so report effective as missing. When they answer effective with a plan, acknowledge the plan and ask for the new way of seeing it. When they offer a new way of seeing it, report effective as partial with it in their words and gap fits: your text says it back and asks whether it fits for them. Known only once they said it does."
    ready_when: "A more realistic and helpful understanding in their own words, which they have said fits them. One they rejected, or not sure, is not reached: stay and help."
    when_stuck: "Put side by side, in their words, the belief and what they found when they looked at it in dispute, and ask what they would say to themselves now. Never supply the belief, never force a positive one."
    if_unclear:
      - id: fits
        slot: effective
        when: "they offered a new way of seeing it and have not said whether it fits"
        reply: "So the thought would now be: <their new belief>. Does that fit for you?"
```
Keep every existing boundary.

- [ ] **Step 5: `mani_base.md` edits (exact)**

In `in_a_framework`, replace the bullet beginning `A stage is answered as soon as stage_ready_when is met` with:
`- A stage is answered when stage_ready_when is met by what they said, never by a yes, an I don't know or a plan. Each stage is a conversation of its own and takes as many exchanges as it needs; there is no count.`

Replace the bullet beginning `Staying is not repeating.` with:
`- Staying is not repeating. Say what you now have in their words, then ask for the one thing missing in fresh words. When they don't know, stage_when_stuck says how to help them look. Not knowing is never a reason to move on.`

Add after it:
`- Each letter builds on the one before. The belief from B is the one looked at in D and reconsidered in E; name it in their words when you ask.`

In `any_stage`:
- `they say they don't know:` → `help them look as stage_when_stuck says, from words they already gave; for example "It is difficult to identify. What was going through your mind at that point?" Never a reason to move on.`
- `they want to stop:` → `answer stopped. Say in one sentence that they can stop here; the two choices follow your text.`
- `a question makes them uneasy, or they want to skip it:` → `answer let_go and move to the next stage without pushing. Never ask whether to continue.`

In `response_format.md`, the reasoning step `The stage, while the questions run.` becomes: `The stage, while the questions run. Does what they said meet stage_ready_when in substance? A yes, an I don't know or a plan does not. Set stage_answer, put in stage_updates only their words for it that are new or changed, judge next_stage from the whole conversation, and write what next in [ctx] says my text is for.`

- [ ] **Step 6: Run the unit suite, then reseed**

Run: `pytest tests/unit -q` → all pass. Then `python scripts/seed.py` (local Supabase running) → exits 0 and names `abcde` as seeded.

- [ ] **Step 7: Commit**

```bash
git add backend/content backend/mani/chat/context.py backend/tests/unit/test_walk.py backend/tests/unit/test_chat_context.py
git commit -m "abcde: C needs feeling and doing, D looks at the belief, E is verified; when_stuck reaches ctx"
```

---

### Task 4: The understanding records the event and a core issue that keeps moving

**Files:**
- Modify: `backend/mani/chat/understanding.py:9` (`KEYS`)
- Modify: `backend/mani/llm/schema.py:150-200` (`UnderstandingUpdate`: new `event`, `core_issue` description)
- Modify: `backend/content/prompts/mani_base.md` (`understanding_them`, the core issue bullet)
- Test: `backend/tests/unit/test_understanding.py`, `backend/tests/integration/test_turn.py`

**Interfaces:**
- Produces: `understanding.KEYS = ("feeling", "body", "event", "issue", "core_issue", "in_their_control", "comes_down_to")`; `UnderstandingUpdate.event: str | None`.

- [ ] **Step 1: Write the failing tests**

`tests/unit/test_understanding.py`:
```python
def test_the_event_they_describe_is_kept_and_shown_but_is_never_a_step():
    """Spec 0007, AC-9: the event that started it is recorded from the first message that names it."""
    stored = understanding.merge({}, UnderstandingUpdate(event="your boss criticized your report in front of the team"))
    assert stored == {"event": "your boss criticized your report in front of the team"}
    assert understanding.next_step(stored) == "problem"
    assert understanding.render(stored) == (
        "event: your boss criticized your report in front of the team; issue: missing; "
        "core_issue: missing; in_their_control: missing"
    )
```

`tests/integration/test_turn.py` (after `_land_on`):
```python
async def test_the_core_issue_is_revised_inside_a_framework(alice, model):
    """Spec 0007, AC-9: the core issue is Mani's reading and moves when a later answer changes it."""
    revised = "not finishing everything has become a reason not to start"
    model(Reply(text="What stops you starting, in that moment?", stage_answer="not_yet",
                understanding_update=UnderstandingUpdate(core_issue=revised)))
    from mani.db import pool

    thread = await start(alice)
    async with pool.as_user(alice) as conn:
        await conn.execute(
            "update public.threads set understanding = $1::jsonb where id = $2",
            {"issue": "a long list undone", "core_issue": "choosing leaves you doing nothing",
             "in_their_control": "you're not sure yet"},
            thread.id,
        )
    await _land_on(alice, thread.id, "belief")

    await send(alice, thread.id, "I won't get it all done so I don't start")

    assert (await _thread_row(alice, thread.id)).understanding["core_issue"] == revised
```

- [ ] **Step 2: Run them to see them fail**

Run: `pytest tests/unit/test_understanding.py -q -k event` → FAIL (`event` not a field). Run the integration test; if it already passes, the code path is proven and the test stays as the pin.

- [ ] **Step 3: Implement**

- `understanding.KEYS` as in Interfaces.
- `UnderstandingUpdate.event: str | None = Field(default=None, description="The specific event or moment they describe that seems to have started this, such as \"your boss criticized your report in front of the team\", in their words and said to them as you, only when this message names it or changes it. A dozen words at most. Null otherwise.")`, placed between `body` and `issue`.
- `core_issue` description becomes: `"The core issue: your reading of what the problem comes down to for them underneath, formed from what is happening and how they feel about it, such as what usually happens next, what falls on them, or what keeps it going. Report it as soon as their answers show it, and again whenever a later answer changes it, before or after your check and inside the framework. Never the feeling they opened with or the problem reworded. A dozen words at most. Null when nothing changed."`
- `mani_base.understanding_them`, the core issue bullet, append: `It is your reading, and it moves: when a later answer changes what it comes down to, say the new reading in one sentence and go on from it, inside the framework too.`
- Update the module docstring of `understanding.py` (ABOUTME) to name the event.

- [ ] **Step 4: Run both suites**

Run: `pytest tests/unit -q && pytest tests/integration/test_turn.py -q` → all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/mani/chat/understanding.py backend/mani/llm/schema.py backend/content/prompts/mani_base.md backend/tests/unit/test_understanding.py backend/tests/integration/test_turn.py
git commit -m "understanding: record the event from the first message; the core issue is a reading that moves"
```

---

### Task 5: The check comes the turn after control is stored

**Files:**
- Modify: `backend/mani/chat/context.py:120-135` (`may_check`), `:206-215` (`_MEANING["check"]`), `:378-381` (the `check` line)
- Modify: `backend/content/prompts/mani_base.md` (`understanding_them` first bullet)
- Modify: `docs/specs/0006-pinpoint-confirm-then-offer/index.md` (AC-2, AC-18, in place)
- Test: `backend/tests/unit/test_chat_context.py:438-466`, `backend/tests/integration/test_turn.py:311-372`

**Interfaces:**
- `context.may_check(ctx) -> bool` is false whenever `understanding.next_step(ctx.thread.understanding)` is not `None`. The `[ctx]` `check` line has two values only: `open`, `may_check`.

- [ ] **Step 1: Rewrite the tests**

`test_no_check_until_the_problem_its_core_issue_and_their_control_are_all_found`: expect `[False, False, False, True]` for `may_check` and `[None, None, None, "check: may_check"]` for the `check` line; update its docstring (the check comes the turn after control; Lolly, 2026-10-16, point 2).

`test_the_problem_its_core_issue_and_control_each_take_an_exchange_then_the_check_and_offer`: script five replies, inserting `Reply(text="When you want to start and nothing happens, what gets in the way?", understanding_update=everything)` as the third; send a fourth person message `"I just freeze, I think"` before the yes; assert `scripted.calls == 5`, `["check" in ...] == [False, False, False, True, False]`, `["offer" in ...] == [False, False, False, False, True]`; `check_at_message_count` is set after the fourth send, not the third. Update the docstring: the reply to the control answer is an ordinary reply; the check answers their 4th message.

`test_a_check_whose_control_did_not_come_from_them_opens_nothing`: its premise (a check field on the control turn) no longer exists. Rewrite as `test_the_turn_that_asks_about_control_has_no_check_field`: with issue and core issue stored, the reply shape on their third message has no `check` field, and `check_at_message_count` stays null after it.

- [ ] **Step 2: Run them to see them fail**

Run: `pytest tests/unit/test_chat_context.py -q -k check` and `pytest tests/integration/test_turn.py -q -k "exchange or control"`.
Expected: FAIL on the third-message expectations.

- [ ] **Step 3: Implement**

- `may_check`: first line becomes `if understanding.next_step(ctx.thread.understanding) is not None: return False`; docstring: "once the problem, its core issue and what is in their control are all stored, which takes at least four of their messages, so the reply that receives the control answer is an ordinary one".
- `_MEANING["check"]`: delete the `once_control_is_answered` entry. The `check` line in `build` becomes `lines += _line("check", "may_check")` with the `waiting` variable removed.
- `mani_base.understanding_them` first bullet, append: `The reply to their answer about control is an ordinary reply, built on what is new in it; the check comes the turn after.`
- Spec 0006: AC-2 "or is what this message answers" → "stored, on earlier turns"; earliest check "their 4th message (2026-10-16, spec 0007)". AC-18: drop the `once_control_is_answered` sentence; a check field exists only once all three are stored.

- [ ] **Step 4: Run both suites**

Run: `pytest tests/unit -q && pytest tests/integration/test_turn.py -q` → all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/mani/chat/context.py backend/content/prompts/mani_base.md backend/tests docs/specs/0006-pinpoint-confirm-then-offer/index.md
git commit -m "check: the reply to the control answer is an ordinary reply; the check comes the turn after"
```

---

### Task 6: Lolly's two conversations as scenarios, reseed, live run through review-chat-change

**Files:**
- Modify: `backend/scripts/scenarios.json` (new group)
- Run: `backend/scripts/seed.py`, `backend/scripts/scenario_check.py`, skill `review-chat-change`

- [ ] **Step 1: Add the group**

Group `two_styles_2026_10_16`, `about`: "Lolly's Reflective and Directive runs of 2026-10-16, the same answers in both. Read by eye: each stage should take as many exchanges as it needs, I don't know gets help, E is verified before the body check-in.", `expect: {}`, one conversation `anxious_long_day` with `source` "Lolly, 2026-10-16, her lines word for word", `lines` = her ten person messages from the Reflective chat in order (from "I had a really long day and i am feeling anxious." to "To be honest, I dont know, thats kinda why im here"), `check_answer`: "Yea I think u got it all", `after_offer.answer`: "yes", `after_offer.lines` = her nine framework answers in order ("Try it" excluded; from "A long list of things that I need to get done and haven't" to "my eyes are burning"). No `stages` expectations: scripted lines land a stage early or late once stages take several exchanges.

- [ ] **Step 2: Unit check of the file**

Run: `pytest tests/unit/test_scenario_check.py -q` → passes (the loader reads the new group).

- [ ] **Step 3: Reseed and run live (needs muhammad's yes: this spends real model calls)**

Run: `python scripts/seed.py && python scripts/scenario_check.py --scenario anxious_long_day --style directive`, then `--style reflective`, then `--style supportive`. Save each log under the session scratchpad as `stages_<style>.txt`.

- [ ] **Step 4: Invoke `review-chat-change`** on the branch diff. Fix what it finds, re-run the touched tests, commit each fix on its own.

- [ ] **Step 5: Commit**

```bash
git add backend/scripts/scenarios.json
git commit -m "scenarios: Lolly's two-styles conversation of 2026-10-16"
```

---

### Task 7: Records

**Files:**
- Modify: `backend/PORT-STATUS.md` ("Decisions in force": the entry at line 226 edited in place; new entries; the turn description)
- Modify: `docs/client/requirements.md` (R17 status and notes; Conflicts rows)
- Create: `mani-vault/Journal/stages-as-conversation-2026-10-16.md`
- Modify: `mani-vault/Journal/abcde-walk-owned-by-code-2026-10-13.md` (Superseded line for the two-tries paragraph), `mani-vault/Journal/client-sample-voice-and-confirmed-check-2026-10-13.md` if it argues for the check on the control turn
- Modify: `docs/specs/0007-stages-as-conversation/index.md` status → In Progress, with the live-run numbers

- [ ] **Step 1: PORT-STATUS**

Edit in place the decision "Inside a framework, a stage their words already answer is said back and confirmed once, never asked; one stage per reply, stepped by code": remove every mention of a second try moving the walk; add `Because Lolly's review of 2026-10-16 found the two-try move turning ABCDE into a questionnaire (2026-10-16).` Add two entries in the same form: **No stage is let go by code; after `walk.STALL_LIMIT` replies Mani offers to keep going, skip or stop, and `stopped` records the run as declined** (because ..., 2026-10-16; tests named in Task 1 and 2). **The check comes the turn after control is stored, never on the reply that receives it** (because Lolly's point 2, 2026-10-16; tests in Task 5). Update the "A chat turn" description where it names the two tries.

- [ ] **Step 2: requirements.md**

R17 status → in-progress; notes: what was built (one line per AC group), the live-run reading from Task 6, what stays open. Conflicts rows: (a) ABCDE document `effective.ready_when` "or have looked at the belief and have no different one" vs Lolly's point 7.4, resolved 2026-10-16 in `abcde.md`; (b) spec 0006 AC-2/AC-18 (check on the control turn) vs her point 2, resolved in Task 5; (c) `_TWO_TRIES` (2026-10-08, "a stage is a step, not an exam") vs her point 5, deleted.

- [ ] **Step 3: Journal**

New note, dated, tags `[journal, walk, abcde, prompts, lessons]`: the root cause (a counter in code), why the earlier fixes missed it, what moved live, lessons (an auto-move rule written against one failure, five asks in a row, became the opposite failure; keep both cases in view). Superseded line on the 2026-10-13 note's two-tries paragraph: `> Superseded 2026-10-16 (the second not_yet moving on) — see [[stages-as-conversation-2026-10-16]]`.

- [ ] **Step 4: Commit**

```bash
git add backend/PORT-STATUS.md docs/client/requirements.md docs/specs mani-vault/Journal
git commit -m "records: stages as conversation, the check turn, and the two-tries decision superseded"
```

---

## Amendments (2026-10-16, after muhammad's decisions 5 to 10 in the spec)

The tasks above stand. These deltas are applied inside them, in order; each keeps its task's test-first steps and commit.

### Task 1 delta: `answered` stays, `agreed` needs a known stage, a corrected earlier stage holds (AC-14, AC-16)

Tests added to `tests/unit/test_walk.py`:

```python
def test_answered_stores_the_words_and_waits_for_their_yes_to_the_say_back(abcde):
    """Spec 0007 decision 6: substance first, then their agreement; answered never moves by itself."""
    walked = walk.advance(abcde, {"belief": {"status": "partial", "said": "too much"}},
                          [said("belief", "I won't get it all done", "known")], "answered", in_force="belief")
    assert (walked.phase, walked.reached) == ("belief", None)
    assert walked.entries["belief"] == {"said": "I won't get it all done", "status": "known"}
    assert "belief answered: said back for their yes" in walked.notes
    agreed = walk.advance(abcde, walked.entries, None, "agreed", in_force="belief", report=judged("missing"))
    assert (agreed.phase, agreed.reached) == ("consequence", "consequence")


def test_a_yes_to_the_say_back_of_a_partial_stage_stays_and_the_gap_is_asked(abcde):
    """Lolly's 6C: "yea" to a C that held only what they did moved on; now it stays on the gap."""
    stored = {"consequence": {"said": "so you don't start", "status": "partial", "gap": "feeling"}}
    walked = walk.advance(abcde, stored, None, "agreed", in_force="consequence")
    assert (walked.phase, walked.reached) == ("consequence", None)
    assert walked.entries["consequence"]["gap"] == "feeling"
    assert "stage answer invalid: agreed" in walked.notes


def test_a_correction_to_an_earlier_stage_keeps_its_old_words_and_holds_this_stage(abcde):
    """Spec 0007 decision 9: corrected in place with its history; nothing moves until Mani has asked about it."""
    stored = {"belief": {"said": "I won't get it all done", "status": "done", "tries": 0},
              "dispute": {"said": "nothing supports it", "status": "known"}}
    walked = walk.advance(abcde, stored, [said("belief", "I'm lazy", "known", corrected=True)], "agreed",
                          in_force="dispute")
    assert (walked.phase, walked.reached) == ("dispute", None)
    assert walked.entries["belief"] == {"said": "I'm lazy", "status": "done", "tries": 0,
                                        "was": ["I won't get it all done"]}
    assert "earlier stage corrected: clarified before moving" in walked.notes
```

`walk.py`: in `merge`, the `elif update.corrected:` branch keeps `"was": (stored.get("was") or [])[-2:] + [stored["said"]]`. In `advance`, after the `asked` hold: `corrected_earlier = any(u.stage != in_force for u in now)`; if so, note and stay with `tries` unchanged; elif `answer in ("answered", "corrected")`, note `f"{in_force} answered: said back for their yes"` and stay with `tries` unchanged; elif `answer == "agreed"`, move only if `stored.get(in_force, {}).get("status") in CONFIRMED and not stored[in_force].get("gap")`; `let_go` moves; anything else stays with `tries + 1`. `MOVES` becomes `frozenset({"agreed", "let_go"})` and its comment says why. `next_line` reads, after the stall prefix: "If they give what this stage needs (answered or corrected), report it in stage_updates and your text says back what you now have for it in their words, as what you understand, and asks whether that is right; nothing moves until their yes. If agreed to your say-back of a known stage, {moved} If agreed while the stage is still partial, ask only the gap. If not_yet, write the follow up for this stage, helped by stage_when_stuck when they don't know. If they correct an earlier stage, report it corrected: your text names the change in one sentence from their words and asks one question to be sure of it, and this stage waits. If let_go, {moved} If stopped, say in one sentence that they can stop here; the two choices follow.{asked}". Update the tests in `test_walk.py` and `test_chat_context.py` that assert the old `next` wording or an `answered` move (`test_a_stage_let_go_reaches_the_next_said_back_from_the_judgement` keeps `let_go`; any test moving on `answered` now expects a stay then an `agreed`).

`schema.py` `stage_answer` description: "agreed: yes to your say-back of what you have for this stage, with more or not. answered: they gave what the stage needs, with an update for it; your text says it back and asks whether that is right. corrected: a no with new words for this stage, or new words for an earlier stage, with an update for it. let_go: they want to skip this stage, or a question made them uneasy. not_yet: a plain no, unclear, or I don't know while you still help. asked: they asked you something or pushed back instead of answering; answer them and ask again. stopped: they want to stop the questions altogether, never a plain no or I don't know."

### Task 3 delta: the prompt says substance then agreement, readings from their words only (AC-14, decision 7)

`mani_base.in_a_framework`, in place of the "A stage is answered..." bullet (Task 3 step 5): "- A stage is answered when stage_ready_when is met by what they said, never by a yes, an I don't know or a plan. When they give it, say it back as what you now understand and ask whether that is right; the stage moves on their yes. Each stage is a conversation of its own and takes as many exchanges as it needs; there is no count." After the "Each letter builds..." bullet add: "- What you say back, and any distinction you offer when they are stuck, is built only from words they gave. Never a new fact, person, motive or feeling, and never what to do." `any_stage` "they correct you:" becomes "they correct an earlier stage: report it corrected, name the change in one sentence from their words, ask one question to be sure of it, and stay on this stage." `response_format` reasoning step "The stage" ends: "...judge next_stage from the whole conversation, and write what next in [ctx] says my text is for: a say-back for their yes, the gap, the help, or the change they made."

### Task 8 (new, after Task 3): Mani's own words at every stage; the client's lines only as fallback (AC-13)

**Files:** `backend/mani/chat/walk.py` (`CONFIRM_ASK`, `reply_text`, `reach_line`), `backend/tests/unit/test_walk.py`.

Tests: `test_a_missing_stage_is_its_letter_line_then_manis_own_question_about_their_situation` gains a case where A is missing with a feeling and Mani's text asks: the reply is the letter line then Mani's question, not the client's `missing` line; and a case where Mani's text asks nothing: the client's line, with "missing asks nothing" noted. `reach_line` test: no "as written" in it.

`reply_text`: for status missing, `body = own if own_asks and not walked.unjudged else None`; only then the client's `missing` line with the feeling (noting "missing asks nothing" when it is taken), then `ask`. `CONFIRM_ASK` = "Say back what they said for this stage, never another stage's part, to them as you, as what you now understand, and ask in your own words whether that is right, in one or two sentences, asked differently from the stage before. The stage moves only on their yes." `reach_line` Missing branch: "your text is your own question for it, about their situation in their words; its letter line is sent for you." Commit: `walk: Mani's own words at every stage; the client's lines only as fallback`.

### Task 4 delta: history on the understanding record (AC-16)

`understanding.py`: `HISTORY = "history"`, `TRACKED = ("issue", "event", "core_issue")`, `KEPT = 3`. `merge` carries `history` and `feeling_asked` through, and when a tracked key's non-empty value is replaced by a different one, appends the old value to `history[key]` (last `KEPT`). `render` ignores `history`. Test `test_a_replaced_issue_or_event_is_kept_in_the_history`: `merge({"issue": "the list", "history": {"issue": ["x"]}}, UnderstandingUpdate(issue="your partner doesn't help"))` gives `history == {"issue": ["x", "the list"]}` and render has no `history:`. `mani_base.ending` gains: "- When, after the questions, they change what the problem is or what it comes down to, say the change in one sentence from their words and ask one question about it. The framework they finished stays finished." `in_a_framework` gains: "- When their message changes the problem or the event itself, say the change in one sentence and ask one question about it before going on; if it no longer fits these questions, ask whether to stay with them."

### Task 9 (new, after Task 4): a changed feeling is confirmed before it is stored (AC-15)

**Files:** `backend/mani/chat/understanding.py`, `backend/mani/llm/schema.py` (`Reply.feeling_answer`, `reply_for(feeling_asked=...)`), `backend/mani/chat/context.py` (`feeling_change` line and meaning), `backend/mani/chat/orchestrator.py` (pass `reply.feeling_answer`; `reply_for(feeling_asked=...)`), `backend/content/prompts/mani_base.md` (`understanding_them`), tests: `tests/unit/test_understanding.py`, `tests/unit/test_chat_context.py`, `tests/integration/test_turn.py`.

Tests first:

```python
# test_understanding.py
def test_a_changed_feeling_waits_for_their_yes():
    """Spec 0007 decision 8: a different feeling is asked about, stored on yes, dropped on no."""
    asked = understanding.merge(STORED, UnderstandingUpdate(feeling="dread"))
    assert asked["feeling"] == "frustrated" and asked["feeling_asked"] == "dread"
    stored = understanding.merge(asked, None, feeling_answer="yes")
    assert stored["feeling"] == "dread" and "feeling_asked" not in stored
    assert stored["history"]["feeling"] == ["frustrated"]
    assert "feeling_asked" not in understanding.merge(asked, None, feeling_answer="no")
    assert understanding.merge({}, UnderstandingUpdate(feeling="dread")) == {"feeling": "dread"}
    assert understanding.merge(asked, UnderstandingUpdate(feeling="panic"))["feeling_asked"] == "panic"
    assert "feeling_asked" not in understanding.render(asked)
```

`test_chat_context.py`: with `understanding = {"feeling": "anxious", "feeling_asked": "dread"}` the block carries `feeling_change: anxious -> dread` and its meaning; without a pending word it does not. `test_turn.py`: two turns, scripted `Reply(text="Has it moved from anxious to something more like dread?", understanding_update=UnderstandingUpdate(feeling="dread"))` then `Reply(text="Go on.", feeling_answer="yes")`; after the first the row has `feeling: anxious`, `feeling_asked: dread`; after the second `feeling: dread` and no pending. A guarded turn stores nothing, as now.

Implementation: `merge(stored, update, *, before=None, feeling_answer=None)`: a pending word is resolved first (yes stores with history, no clears); then an `update.feeling` that differs from a stored feeling becomes `feeling_asked` instead of `feeling`; with no stored feeling it is stored. `Reply.feeling_answer: Literal["yes", "no"] | None` placed right after `check_answer`, description: "Only while feeling_change is in [ctx]: yes when they go along with the feeling having moved to the second word, no when they say it has not." `reply_for(..., feeling_asked: bool = False)` adds it. `context._MEANING["feeling_change"]`: "your last reply asked whether their feeling has moved from the first word to the second. Set feeling_answer from how they take that, then go on with what the rest of this block says." `build` adds the line when `understanding.get("feeling_asked")`. `mani_base.understanding_them` after the feeling bullet: "- When their message shows a feeling different from the one in understanding, report it in understanding_update and your reply asks, in one question, whether it has changed. The step, or the stage, waits for their answer." Orchestrator: `understanding.merge(before, reply.understanding_update, before=before, feeling_answer=reply.feeling_answer)` in both merge calls; `reply_for(..., feeling_asked=bool(ctx.thread.understanding.get("feeling_asked")))`. Commit: `understanding: a changed feeling is confirmed before it is stored`.

### Task 6 delta

The scenario group also sets `expect` to nothing new; read by eye for: the say-back then yes at each stage, the feeling question if a scenario changes the feeling, and that no stage moved on `answered`.

### Task 7 delta (AC-17)

PORT-STATUS: the decision of 2026-10-14 ("a stage reached as missing is asked with the client's `ask` as written...") edited in place to decision 5; new entries for decisions 6, 8 and 9 in the same form. `requirements.md` Conflicts: muhammad's decision 5 against the ABCDE document's fixed lines and his own decision of 2026-10-14 (recorded as our choice, client to be told).

### After Task 7: spec 0008, the somatic cadence (R18, decision 10)

Written only after the live run of Task 6 is read.
