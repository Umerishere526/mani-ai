# Mani Reply Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Mani's replies better than the client's MVP in all three styles, by rebuilding every prompt file from scratch against a side-by-side measurement.

**Judging:** muhammad is the only judge of reply quality. No automated scoring decides whether a reply is good; `pytest` checks only that the code works.

**Architecture:** A comparison script runs the same scripted conversations through the MVP's prompt stack and through ours, and writes one readable transcript file. Every prompt file is then rebuilt section by section, with muhammad deciding each section before it is written, and measured before and after. Code changes only where a decided behaviour needs enforcing (buttons, the grounding stage) or where a walk decides a rule goes.

**Tech Stack:** Python 3.14, FastAPI backend, asyncpg, LangChain `ChatOpenAI` via OpenRouter (`google/gemini-3-flash-preview`), pytest, markdown prompt files seeded by `scripts/seed.py`.

**Spec:** `docs/superpowers/specs/2026-09-24-mani-reply-quality-design.md`

## Global Constraints

- Run everything from `backend/` with the venv active: `cd backend && source .venv/bin/activate`.
- Local Supabase must be running (`supabase start`); integration tests skip without it, and a run that skipped them is not a pass. Check the count: currently **518 passed, 4 skipped**.
- The client's frame is fixed: three styles, six frameworks, never a framework's name or the word "framework", Try it / Keep chatting, body check-in, Chat More / Go to Library, the three forward-moving questions.
- Never "therapy", "therapist", "session", a diagnosis, or clinical vocabulary in anything Mani says.
- Prompt text is written only after muhammad has confirmed that section. A section he has not confirmed is not written.
- One model call per turn stays; `test_a_turn_costs_exactly_one_provider_call` must stay green.
- Every code file starts with two `# ABOUTME:` lines.
- Commit messages carry no AI attribution and no `Co-Authored-By` trailer.
- After editing any file under `content/`, run `python scripts/seed.py` before measuring; the service reads the database, not the files.
- `backend/PORT-STATUS.md` is updated in the same commit as the behaviour it describes.

## Review Focus

- A person who types past an offer instead of tapping: the button rule must not strip the re-offer's Try it / Keep chatting.
- A person who answers the closing question by describing their body: no second body question, and the grounding practice or the choice follows.
- A person who reports chest pain or trouble breathing at the body check-in: no practice; the safety screen's concern path answers.
- A reply that repairs empty after the button and presence rules: still refused as retryable, never stored empty.
- A thread from before this change whose framework row stopped at `somatic`: it must still finish and hand off, not wait for a `grounding` stage it never reached.

## Before Task 1

The working tree carries muhammad's uncommitted feelings-first change (MYM-148). Ask him whether to commit it as its own commit first. Measuring "now" uses the working tree either way; committing it first keeps the redesign's commits clean.

---

### Task 1: The MVP as a fixed reference, and the side-by-side script

**Files:**
- Create: `backend/docs/mvp-prompts/README.md`, `backend/docs/mvp-prompts/mani_base.md`, `backend/docs/mvp-prompts/techniques.md`, `backend/docs/mvp-prompts/response_format.md`
- Create: `backend/scripts/compare_replies.py`
- Create: `backend/tests/unit/test_compare_replies.py`
- Modify: `.gitignore` (repo root)

**Interfaces:**
- Consumes: `scripts.eval_replies.SCENARIOS`, `_fresh_user(scenario: str, style: SupportStyle) -> str`, `_run_one(user_id, style, turns, start_in=None) -> list[Exchange]`, `Exchange(message, reply, buttons, ...)`, `EVAL_NICKNAME`; `scripts.seed.parse_prompt(path) -> dict`; `mani.llm.client.complete(...)`.
- Produces: `python scripts/compare_replies.py --label <name> [--scenario <name>]`, which writes `backend/.eval/<timestamp>-<label>.md`. Functions `mvp_system_prompt(nickname, prompts_dir=MVP_DIR) -> str`, `mvp_ctx(recent_styles: list[tuple[str, str | None]]) -> str`, `render(name, turns, mvp, ours) -> str`.

- [ ] **Step 1: Copy the MVP prompts, exactly as they were at `e7776ed`**

```bash
MVP="$HOME/Desktop/Mani Repos/mani-app "
mkdir -p docs/mvp-prompts
for f in mani_base techniques response_format; do
  git -C "$MVP" show "e7776ed:apps/backend/prompts/$f.md" > "docs/mvp-prompts/$f.md"
done
```

Write `docs/mvp-prompts/README.md`:

```markdown
# The MVP's prompts

The prompts of the MVP the client used, copied verbatim from `mani-app` at commit `e7776ed`
(2026-01-30, "add stronger structure around conversation variety"), the last change to them.
That commit deleted the three style files, so this is one presence-first voice with two named
techniques.

**Provenance, not configuration.** Nothing seeds these into the database. They exist so
`scripts/compare_replies.py` can run the MVP's stack beside ours: they are the bar the rebuilt
prompts are judged against.
```

- [ ] **Step 2: Ignore the comparison output**

Append to the repo-root `.gitignore`, under `# Python`:

```
backend/.eval/
```

- [ ] **Step 3: Write the failing tests**

`backend/tests/unit/test_compare_replies.py`:

```python
# ABOUTME: Checks the MVP side of the comparison is composed the way the MVP composed it.
# ABOUTME: A baseline built in the wrong order would measure a prompt the client never used.

from scripts.compare_replies import mvp_ctx, mvp_system_prompt, render
from scripts.eval_replies import Exchange


def _write(directory, name, body):
    (directory / f"{name}.md").write_text(f"---\nname: {name}\n---\n\n{body}\n")


def test_the_mvp_prompt_keeps_the_mvps_own_layer_order(tmp_path):
    for name in ("mani_base", "techniques", "response_format"):
        _write(tmp_path, name, f"BODY OF {name}")
    (tmp_path / "README.md").write_text("# not a prompt\n")

    prompt = mvp_system_prompt("Sam", tmp_path)

    order = [prompt.index(f"BODY OF {n}") for n in ("mani_base", "techniques")]
    order += [prompt.index('The user prefers to be called "Sam".'), prompt.index("BODY OF response_format")]
    assert order == sorted(order)
    assert "not a prompt" not in prompt


def test_the_mvp_prompt_leaves_out_user_context_without_a_nickname(tmp_path):
    for name in ("mani_base", "techniques", "response_format"):
        _write(tmp_path, name, name)
    assert "User Context" not in mvp_system_prompt(None, tmp_path)


def test_the_mvp_ctx_block_matches_the_mvps_format():
    assert mvp_ctx([]) == "[ctx]\ncooldown_passed: yes\n[/ctx]\n\n"
    block = mvp_ctx([("mirror and ask", "receiving"), ("presence only", None)])
    assert "recent_styles: mirror and ask (receiving) → presence only\n" in block


def test_every_style_answers_under_each_line_the_person_said():
    ours = {
        "supportive": [Exchange(message="hi", reply="S1"), Exchange(message="more", reply="S2", buttons=["Try it"])],
        "direct": [Exchange(message="hi", reply="D1"), Exchange(message="more", reply="D2")],
    }
    page = render("demo", ["hi", "more"], ["M1", "M2"], ours)

    assert page.index("**Person:** hi") < page.index("M1") < page.index("S1") < page.index("D1")
    assert page.index("**Person:** more") < page.index("M2") < page.index("S2")
    assert "`[Try it]`" in page
```

- [ ] **Step 4: Run them to see them fail**

Run: `pytest tests/unit/test_compare_replies.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.compare_replies'`

- [ ] **Step 5: Write the script**

`backend/scripts/compare_replies.py`:

```python
# ABOUTME: Runs scripted conversations through the MVP's prompts and through ours, side by side.
# ABOUTME: The MVP is the bar the client remembers; a person reads the result and judges.

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from mani.db import llm_calls, pool  # noqa: E402
from mani.llm import client  # noqa: E402
from mani.llm.schema import Reply  # noqa: E402
from mani.models.rows import SupportStyle  # noqa: E402
from scripts.eval_replies import (  # noqa: E402
    EVAL_NICKNAME,
    SCENARIOS,
    Exchange,
    _fresh_user,
    _run_one,
)
from scripts.seed import parse_prompt  # noqa: E402

BACKEND = pathlib.Path(__file__).resolve().parent.parent
MVP_DIR = BACKEND / "docs" / "mvp-prompts"
OUT_DIR = BACKEND / ".eval"

# What the MVP's mani_base row named, so both sides answer on the same model and temperature.
MVP_MODEL = "google/gemini-3-flash-preview"
MVP_TEMPERATURE = 1.0
STYLE_WINDOW = 7

# Conversation before a framework runs: the only part the MVP's two techniques can be compared
# on, and where interrogating and offering too soon show up.
SCENARIO_NAMES = (
    "anxiety_free_chat", "disclosure_no_question_needed", "client_anxiety",
    "client_overthinking", "client_scrolling", "client_stress", "open_losing_someone",
)


def mvp_system_prompt(nickname: str | None, prompts_dir: pathlib.Path = MVP_DIR) -> str:
    """The MVP's system prompt: identity, technique library, user context, response format."""
    body = {name: parse_prompt(prompts_dir / f"{name}.md")["content"]
            for name in ("mani_base", "techniques", "response_format")}
    parts = [body["mani_base"], body["techniques"]]
    if nickname:
        parts.append(f'## User Context\nThe user prefers to be called "{nickname}".')
    parts.append(body["response_format"])
    return "\n\n".join(parts)


def mvp_ctx(recent_styles: list[tuple[str, str | None]]) -> str:
    """The MVP's [ctx] block for a turn before any technique: the cooldown and recent styles."""
    lines = ["cooldown_passed: yes"]
    if recent_styles:
        shown = recent_styles[-STYLE_WINDOW:]
        lines.append("recent_styles: " + " → ".join(f"{s} ({v})" if v else s for s, v in shown))
    return "[ctx]\n" + "\n".join(lines) + "\n[/ctx]\n\n"


async def run_mvp(turns: list[str], nickname: str) -> list[str]:
    """One conversation on the MVP's stack. Raw replies: the MVP regenerated, it did not repair.

    The history carries no [ctx] blocks, although the MVP stored them; that only removes noise
    the MVP itself was fighting. The reply schema's field descriptions are ours, the one part of
    the prompt surface the two sides share.
    """
    system = mvp_system_prompt(nickname)
    history: list[dict[str, str]] = []
    styles: list[tuple[str, str | None]] = []
    replies: list[str] = []
    for message in turns:
        call = await client.complete(
            [{"role": "system", "content": system}, *history,
             {"role": "user", "content": mvp_ctx(styles) + message}],
            Reply, model=MVP_MODEL, purpose=llm_calls.Purpose.CHAT, temperature=MVP_TEMPERATURE,
        )
        reply = call.value
        history += [{"role": "user", "content": message}, {"role": "assistant", "content": reply.text}]
        if reply.style is not None:
            styles.append((reply.style.shape, reply.style.voice))
        replies.append(reply.text)
    return replies


def render(name: str, turns: list[str], mvp: list[str], ours: dict[str, list[Exchange]]) -> str:
    """One scenario: each line the person said, then the MVP's reply and each style's under it."""
    lines = [f"## {name}", ""]
    for index, message in enumerate(turns):
        lines += [f"**Person:** {message}", "", f"- **MVP:** {mvp[index]}"]
        for style, exchanges in ours.items():
            exchange = exchanges[index]
            buttons = f"  `[{' / '.join(exchange.buttons)}]`" if exchange.buttons else ""
            lines.append(f"- **{style}:** {exchange.reply}{buttons}")
        lines.append("")
    return "\n".join(lines)


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="baseline", help="names the output file")
    parser.add_argument("--scenario", help="run only this scenario")
    args = parser.parse_args()

    scenarios = [
        s for s in yaml.safe_load(SCENARIOS.read_text())
        if s["name"] in SCENARIO_NAMES and (not args.scenario or s["name"] == args.scenario)
    ]
    await pool.open_pool()
    sections: list[str] = []
    try:
        for scenario in scenarios:
            turns = scenario["turns"]
            mvp = await run_mvp(turns, EVAL_NICKNAME)
            ours = {}
            for style in SupportStyle:
                user_id = await _fresh_user(scenario["name"], style)
                ours[style.value] = await _run_one(user_id, style, turns)
            sections.append(render(scenario["name"], turns, mvp, ours))
            print(f"done: {scenario['name']}")
    finally:
        await pool.close_pool()

    OUT_DIR.mkdir(exist_ok=True)
    path = OUT_DIR / f"{dt.datetime.now():%Y%m%d-%H%M%S}-{args.label}.md"
    path.write_text(f"# MVP vs now: {args.label}\n\n" + "\n\n".join(sections) + "\n")
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
```

- [ ] **Step 6: Run the tests to see them pass**

Run: `pytest tests/unit/test_compare_replies.py -v`
Expected: 4 passed.

- [ ] **Step 7: Run one scenario live to prove the wiring**

Run: `python scripts/compare_replies.py --scenario client_anxiety --label smoke`
Expected: `done: client_anxiety` and a path under `backend/.eval/`. Open it: three **Person** lines, each with an MVP reply and three style replies, and a findings line.

- [ ] **Step 8: Full suite, then commit**

Run: `pytest -q -rs` — expected 522 passed, 4 skipped.

```bash
git add ../.gitignore docs/mvp-prompts scripts/compare_replies.py tests/unit/test_compare_replies.py
git commit -m "Run the client's MVP prompts beside ours, so reply quality has a bar"
```

---

### Task 2: The baseline

**Files:** none changed. Output in `backend/.eval/`.

- [ ] **Step 1: Three full runs**

```bash
for n in 1 2 3; do python scripts/compare_replies.py --label baseline-$n; done
```

- [ ] **Step 2: muhammad reads them**

Share the three files (publish one as a private artifact if he prefers reading in a browser). Ask him two things: does the MVP column read better than ours on these scenarios, and which three replies in our columns are the worst. Record his answers.

- [ ] **Step 3: If the MVP does not read better, stop**

The bar is wrong. Ask muhammad for real examples of MVP replies the client liked, and add them to `backend/docs/mvp-prompts/README.md` as the bar instead.

- [ ] **Step 4: Journal**

Append the baseline findings (his judgement and the replies he picked as worst) to `mani-vault/Journal/the-mvp-prompts-are-the-reply-quality-bar.md`. Commit:

```bash
git add ../mani-vault/Journal/the-mvp-prompts-are-the-reply-quality-bar.md
git commit -m "Record the baseline: the MVP beside today's Mani"
```

---

### Task 3: Buttons only at a framework's offer and its end

**Files:**
- Modify: `backend/mani/chat/repairs.py` (the end of `apply()`, after the phase is computed)
- Test: `backend/tests/unit/test_repairs.py`, plus existing tests that assumed free-chat buttons survive

**Interfaces:**
- Produces: `repairs.ENDING_STAGES: frozenset[str] = frozenset({"somatic", "grounding"})`. `apply()` keeps its signature.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/unit/test_repairs.py`:

```python
def test_ordinary_chat_carries_no_buttons(registry):
    """The client: buttons in ordinary chat read as a menu, not a conversation (2026-09-24)."""
    chatty = reply(text="What happened next?", prompts=[
        SmartPrompt(label="Tell me more"), SmartPrompt(label="Not sure"),
    ])
    fixed = fix(registry, chatty)
    assert fixed.prompts == []
    assert any("outside an offer or a framework's end" in n for n in fixed.notes)


def test_an_offer_keeps_its_two_buttons(registry):
    offer = reply(
        text="There are some questions that could help with this. Would you like to try them?",
        prompts=[SmartPrompt(label="Try it", technique="abcde"),
                 SmartPrompt(label="Keep chatting", decline=True)],
    )
    assert [p.label for p in fix(registry, offer).prompts] == ["Try it", "Keep chatting"]


def test_the_end_of_a_framework_keeps_its_buttons(registry):
    practice = reply(
        text="Hand on your chest. In for four, out for six, three times.",
        prompts=[SmartPrompt(label="I tried it"), SmartPrompt(label="Still tense"),
                 SmartPrompt(label="Feeling better")],
    )
    fixed = fix(registry, practice, framework_running=True, current_phase="grounding",
                current_framework_id="abcde")
    assert [p.label for p in fixed.prompts] == ["I tried it", "Still tense", "Feeling better"]


def test_a_stage_in_the_middle_of_a_framework_carries_no_buttons(registry):
    mid = reply(text="What did she say?", prompts=[SmartPrompt(label="Not sure")])
    fixed = fix(registry, mid, framework_running=True, current_phase="belief",
                current_framework_id="abcde")
    assert fixed.prompts == []
```

- [ ] **Step 2: Run them to see them fail**

Run: `pytest tests/unit/test_repairs.py -k "buttons or offer_keeps" -v`
Expected: `test_ordinary_chat_carries_no_buttons` and `test_a_stage_in_the_middle...` FAIL (buttons survive); the other two pass already.

- [ ] **Step 3: Implement**

In `mani/chat/repairs.py`, below `MAX_CAPSULE_WORDS`:

```python
# Where a reply may carry buttons besides an offer: the body check-in and the practice that ends
# a framework. Everywhere else a button reads as a menu instead of a conversation (client,
# 2026-09-24). The greeting's style buttons and Chat More / Go to Library are written by the
# orchestrator after this runs, so they are not affected.
ENDING_STAGES = frozenset({"somatic", "grounding"})
```

In `apply()`, immediately before `title = clean_title(...)`:

```python
    at_the_end = framework_running and (phase or current_phase) in ENDING_STAGES
    if kept and not at_the_end and not any(p.technique for p in kept):
        notes.append(f"dropped buttons outside an offer or a framework's end: {[p.label for p in kept]}")
        kept = []
```

- [ ] **Step 4: Run the new tests**

Run: `pytest tests/unit/test_repairs.py -v`
Expected: the four new tests pass. Some older tests now fail.

- [ ] **Step 5: Repair the older tests by their purpose**

Run `pytest -q` and take each failure in turn:

- A test whose point is a button's **content** (feeling words, self-judgments, length, duplicates, the trim to three, library sections): pass `framework_running=True, current_phase="somatic", current_framework_id="abcde"` so it runs where buttons are allowed, and keep its assertion.
- A test whose point is that a free-chat button **survives** (for example `test_a_turn_costs_exactly_one_provider_call` in `tests/integration/test_turn.py`, which expects `["Later", "Not now"]`): it now asserts the buttons are gone (`[]`), and its comment says why.
- Anything else: stop and bring it to muhammad; do not change an assertion you cannot explain.

Run: `pytest -q -rs` — expected all pass, 4 skipped.

- [ ] **Step 6: Commit**

```bash
git add mani/chat/repairs.py tests/unit/test_repairs.py tests/integration/test_turn.py
git commit -m "Offer buttons only on a framework's offer and at its end"
```

---

### Task 4: Rebuild `mani_base.md`

**Files:**
- Modify: `backend/content/prompts/mani_base.md` (body rewritten; frontmatter kept)

This is the foundation, and it is written section by section with muhammad. The new file follows the MVP's structure. These are the sections to propose, in order. For each one, show muhammad the current text it replaces, what is wrong with it against the client's feedback (robotic, loopy, cold, Direct not direct, interrogating, pushing too soon, forgetting the issue), and the replacement. Write only what he confirms.

1. **Who Mani is and the goal.** The MVP's "Goal: Comfort. Help the user feel seen and accepted", widened by the spec: warm, experienced, never clinical, moving the person toward feeling better, holding the core issue throughout.
2. **The five moves** (acknowledgment, acceptance, mirroring, permission, presence), from the MVP, with the spec's one change: a feeling Mani senses may be named **only as a question that checks it**.
3. **The three styles**, each as behaviour, in muhammad's words from the spec (Direct: direct, warm, loving, aiming at closure, questions their perspective then moves on; Supportive: emotional support first, then what would make it better; Reflective: the feeling, not the situation, checked and explored).
4. **How a conversation moves**: the client's flow from the spec's "The flow", with offer timing decided here (spec decision list, first item).
5. **Offering a framework**: description not name, fitted to what they said, then the permission question; Try it / Keep chatting.
6. **Running a framework and ending it**, including the body check-in and grounding practice from the spec.
7. **One whole annotated conversation per style**, written fresh (not copied from any prompt, to avoid templates), each showing the full flow in that style, with the MVP's shape annotations.
8. **What never happens**: only the rules an example cannot carry (no clinical words, no repeated question, no generic check-ins, no narrating plans). The anti-injection section moves to the end, shortened.

- [ ] **Step 1: Walk sections 1 to 8 with muhammad**, one message per section. Record each decision (including the decision-list items it settles) in the journal note as you go.
- [ ] **Step 2: Write the confirmed file**, then `python scripts/seed.py`.
- [ ] **Step 3: Search for templates**: `grep -n -i "holding up\|how are you\|I have a sequence" content/prompts/mani_base.md`. Any hit that is not a deliberate, varied example goes back to muhammad.
- [ ] **Step 4: Measure**: three runs, `python scripts/compare_replies.py --label mani-base-$n` for n in 1 2 3. Show muhammad the files beside the baseline.
- [ ] **Step 5: If he judges it worse on any scenario**, go back to the section that scenario exercises. Do not move on.
- [ ] **Step 6: Suite**: `pytest -q -rs`. Prompt text changes can break tests that assert on it (`tests/unit/test_composer.py`); fix each by its purpose, as in Task 3 Step 5.
- [ ] **Step 7: Commit**

```bash
git add content/prompts/mani_base.md ../mani-vault/Journal/the-mvp-prompts-are-the-reply-quality-bar.md
git commit -m "Rebuild Mani's identity prompt on the MVP's structure and the client's styles"
```

---

### Task 5: Rebuild `response_format.md`

**Files:**
- Modify: `backend/content/prompts/response_format.md`
- Modify: `backend/mani/llm/schema.py` (the `Reply.prompts` description, to match Task 3's rule)

Sections to walk with muhammad, same method as Task 4:

1. **Reading the `[ctx]` block**: only the fields Task 6 will keep; propose Task 6's list here, together.
2. **The reasoning field**: fewer steps, each one aimed at a named complaint: does this reply move toward them feeling better, is this question new, am I still on their actual issue, am I checking rather than stating a feeling.
3. **Buttons**: only the offer and the framework's end.
4. **Library**, **constraints**, **length**, **formatting**: kept only where `mani_base` does not already say it.

- [ ] **Step 1: Walk sections 1 to 4 with muhammad.**
- [ ] **Step 2: Update the `Reply.prompts` description** in `mani/llm/schema.py` to:

```python
        description=(
            "Buttons, only when this reply offers a framework (Try it with its \"technique\", "
            "Keep chatting with \"decline\"), asks the body check-in, or gives the practice that "
            "ends a framework. Null on every other reply. Labels in the person's voice, one to "
            "five words, never a feeling word."
        ),
```

- [ ] **Step 3: Write the confirmed file**, `python scripts/seed.py`, three measured runs (`--label response-format-$n`), muhammad reads.
- [ ] **Step 4: Suite and commit**

```bash
pytest -q -rs
git add content/prompts/response_format.md mani/llm/schema.py
git commit -m "Rebuild the response rules around what the client said was wrong"
```

---

### Task 6: The `[ctx]` contract

**Files:**
- Modify: `backend/mani/chat/context.py` (`build()`)
- Test: `backend/tests/unit/test_chat_context.py`

The block today carries up to about twenty field kinds. Each is a claim on the model's attention every turn.

- [ ] **Step 1: List every line `build()` can emit**, with what reads it in the prompt and what it is for. Take muhammad through the list: keep, drop or change each (`question_focus` and `framework_starting` from the uncommitted diff included).
- [ ] **Step 2: For each dropped field, write the failing test first**: e.g. for a dropped `question_focus`:

```python
def test_the_block_no_longer_tells_the_model_what_to_ask_about():
    ctx = TurnContext(thread=thread(), profile=None, technique=None)
    assert "question_focus" not in context.build(ctx)
```

Run it (`pytest tests/unit/test_chat_context.py -k <name> -v`), see it fail, remove the field, see it pass. Remove or rewrite the tests that asserted the dropped field.
- [ ] **Step 3: Keep `response_format.md`'s `[ctx]` section in step** with the new field list, reseed, three measured runs (`--label ctx-$n`), muhammad reads.
- [ ] **Step 4: Suite and commit**

```bash
pytest -q -rs
git add mani/chat/context.py tests/unit/test_chat_context.py content/prompts/response_format.md
git commit -m "Send the model only the context it needs each turn"
```

---

### Task 7: The grounding stage in every framework

**Files:**
- Modify: all six `backend/content/frameworks/*.md` (`phases` and `stages.grounding`)
- Modify: `backend/mani/chat/orchestrator.py` only if Step 5 shows it is needed
- Test: `backend/tests/integration/test_turn.py` (the ending tests)

- [ ] **Step 1: Get the somatic wording from muhammad.** Until he gives it, the `somatic.ask` lines stay as they are (the client spec's).
- [ ] **Step 2: Add `grounding` as the last phase** in each file: `phases: [..., closing, somatic, grounding]`, and under `stages`:

```yaml
  grounding:
    purpose: "Help them feel something ease before they choose what next. Offer one short practice for where they notice it, then reflect what changed in their own words and ask what they would like to do next."
    listen_for: "Where in the body they notice it (chest, head, stomach, somewhere else), whether they tried the practice, and what changed."
    ready_when: "They have tried the practice or said they would rather not, and have said how they feel now."
    boundaries:
      - "must not give a practice when they describe pain, trouble breathing, dizziness or anything that sounds physical"
      - "must not ask about the body a second time"
      - "must not offer the practice more than twice"
      - "must not tell them the practice worked; reflect only what they say changed"
    if_unclear:
      - when: "still tense after the practice"
        reply: "It can come in waves. Would you like to try it once more, or decide what to do next?"
      - when: "they would rather not"
        reply: "That's okay. What would you like to do next?"
    ask:
      supportive: "Let's try something small together. Put a hand on your chest, breathe in through your nose for four, and out through your mouth for six. Do that three times, at your own pace."
      reflective: "Let's stay with that for a moment. Put a hand on your chest, breathe in through your nose for four, and out through your mouth for six, three times. Notice what shifts."
      direct: "Here's one thing to try. Hand on your chest, breathe in through your nose for four, out through your mouth for six. Three times."
```

The `ask` shows the chest practice; `purpose` and `listen_for` carry the others. Put the four practices from the spec's table in `mani_base`'s ending section (Task 4, section 6) so the model has all of them.

- [ ] **Step 3: Reseed**: `python scripts/seed.py`. Expected: each framework prints one more stage.
- [ ] **Step 4: Write the failing integration test** in `tests/integration/test_turn.py`, next to `test_the_body_check_in_waits_for_their_answer_before_the_two_choices`:

```python
async def test_the_practice_comes_between_the_check_in_and_the_two_choices(alice, model):
    """muhammad, 2026-09-24: before choosing, they try a short practice, so something eases."""
    from mani.db import pool

    thread = await start(alice)
    await send(alice, thread.id, "Supportive")
    async with pool.as_user(alice) as conn:
        await threads.set_technique_outcome(
            conn, thread.id, ALICE, "abcde", TechniqueOutcome.ACCEPTED,
            at_message_count=0, phase="somatic",
        )
    model(Reply(
        text="Your chest feels tight. Put a hand on it, in for four, out for six, three times.",
        prompts=[SmartPrompt(label="I tried it"), SmartPrompt(label="Still tense"),
                 SmartPrompt(label="Feeling better")],
        state=TechniqueState(technique="abcde", step="grounding"),
    ))
    practice = await send(alice, thread.id, "my chest feels tight")
    assert [p.label for p in practice.prompts] == ["I tried it", "Still tense", "Feeling better"]

    model(Reply(text="It feels looser now. What would you like to do next?"))
    after = await send(alice, thread.id, "I tried it")
    assert [p.label for p in after.prompts] == ["Chat More", "Go to Library"]
```

- [ ] **Step 5: Run it**: `pytest tests/integration/test_turn.py -k practice -v`. If it fails, read the failure before touching code: completion is positional (`Registry.is_final`), so the hand-off should already move to `grounding`. Change `orchestrator.py` only for a failure you can explain, with muhammad's approval.
- [ ] **Step 6: Update the other ending tests** (`test_finishing_a_framework_always_offers_chat_more_and_the_library`, `test_the_body_check_in_waits_...`, `test_a_body_they_already_described_ends_...`) to walk `somatic → grounding`. Each keeps its point.
- [ ] **Step 7: The old thread from Review Focus**: a row stored at `somatic` from before this change. Add:

```python
async def test_a_framework_stopped_at_somatic_before_grounding_existed_still_finishes(alice, model):
    from mani.db import pool

    thread = await start(alice)
    await send(alice, thread.id, "Supportive")
    async with pool.as_user(alice) as conn:
        await threads.set_technique_outcome(
            conn, thread.id, ALICE, "abcde", TechniqueOutcome.ACCEPTED,
            at_message_count=0, phase="somatic",
        )
    model(Reply(text="Your shoulders feel looser. What would you like to do next?",
                state=TechniqueState(technique="abcde", step="grounding")))
    await send(alice, thread.id, "my shoulders feel looser")
    model(Reply(text="Okay."))
    done = await send(alice, thread.id, "Chat More")

    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE)
    assert ctx.technique.phase is None and done.content
```

- [ ] **Step 8: Suite, measure a journey, commit**

```bash
pytest -q -rs
python scripts/eval_replies.py --scenario journey_abcde --verbose
git add content/frameworks tests/integration/test_turn.py
git commit -m "End every framework with a short practice before the choice"
```

---

### Task 8: Rebuild the six framework files

**Files:**
- Modify: `backend/content/frameworks/{abcde,thought_reframe,behavioral_activation,structured_problem_solving,act_choice_point,dbt_stop}.md`

One framework per sub-task, same method as Task 4. For each file walk with muhammad:

1. `summary`: the client's description verbatim, with "This framework" as "These questions" (Structured Problem Solving: the client's "moves through five questions", not "a few focused questions").
2. Each stage's `ask` in each style: a real question an experienced person would ask, built for this stage, not a template; no example people or details from the worked examples.
3. `if_unclear` replies: the same test.
4. `activation` signals: phrases a person would really type (compare against `docs/specs/framework-*.md`).

- [ ] **Step 1: ABCDE**: walk, write, reseed, `python scripts/eval_replies.py --scenario journey_abcde --verbose` three times, muhammad reads, `pytest -q -rs`, commit `git commit -m "Rebuild ABCDE's questions"`.
- [ ] **Step 2: Thought Reframe**: same, with `framework_abcde_stages`-style scenario if one exists; otherwise add one to `scripts/eval_conversations.yaml` using `start_in: {framework: thought_reframe, phase: surface}` and turns from `docs/specs/framework-thought-reframe.md`'s worked example. Commit `"Rebuild Thought Reframe's questions"`.
- [ ] **Step 3: Behavioral Activation** with `journey_behavioral_activation`. Commit `"Rebuild Behavioral Activation's questions"`.
- [ ] **Step 4: Structured Problem Solving**: add a `start_in` scenario from its spec's worked example. Commit `"Rebuild Structured Problem Solving's questions"`.
- [ ] **Step 5: ACT Choice Point**: same. Commit `"Rebuild ACT Choice Point's questions"`.
- [ ] **Step 6: DBT STOP**: same. Commit `"Rebuild STOP's questions"`.

`eval_replies.py --verbose` is used here only to print the journey transcripts for muhammad to read; its `FAIL` lines are automated scoring and are not the judge.

`tests/unit/test_router.py` parses these files: run `pytest -q -rs` after each, and fix a failure by its purpose.

---

### Task 9: The repairs that rewrite text

**Files:**
- Modify: `backend/mani/chat/repairs.py`
- Test: `backend/tests/unit/test_repairs.py`, `backend/tests/evals/validators.py`

- [ ] **Step 1: List each rule in `apply()` that changes `text`**: presence stripping, offer-sentence removal, the appended permission question, and the feeling-word note. For each, show muhammad a transcript line from the latest `compare_replies` run where it fired (from the repair notes printed by `eval_replies.py --verbose`), and decide keep, change or remove.
- [ ] **Step 2: For each change, test first.** Example, if presence stripping goes:

```python
def test_presence_is_left_to_the_prompt_in_every_style(registry):
    said = reply(text="I'm here. What happened after she left?")
    assert fix(registry, said, conversation_style="direct").text == said.text
```

See it fail, change `apply()`, see it pass, and delete the tests that asserted the removed behaviour.
- [ ] **Step 3: The feeling rule.** Checking a feeling is now allowed. `apply()` logs a note for every feeling word the person did not use; a feeling named inside a question is a check, not a label. Ask muhammad whether the note stays at all; if it does, test first:

```python
def test_a_feeling_named_as_a_question_is_not_noted(registry):
    checked = reply(text="It sounds like you feel shut out. Is that lonely?")
    assert not any("feeling word" in n for n in fix(registry, checked, said="she left").notes)
```

Implement by only counting feeling words in sentences that do not end in `?`.
- [ ] **Step 4: The offline evals.** `tests/evals/` scores fixed strings against rules this rebuild is changing. Show muhammad what each file asserts and decide together whether it stays, changes, or is deleted. Nothing there judges reply quality from here on.
- [ ] **Step 5: Measure, suite, commit**

```bash
for n in 1 2 3; do python scripts/compare_replies.py --label repairs-$n; done
pytest -q -rs
git add mani/chat/repairs.py tests/unit/test_repairs.py tests/evals
git commit -m "Keep only the repairs that make a reply better"
```

---

### Task 10: Title, summary and memory prompts

**Files:**
- Modify: `backend/content/prompts/title_generation.md`, `summarization.md`, `memory_fold.md`

- [ ] **Step 1: Walk each with muhammad**, one at a time. The question for summary and memory: does what they keep let Mani hold on to the person's actual issue (the "forgets the issue" complaint)?
- [ ] **Step 2: Write, reseed, `pytest -q -rs`**, and for memory run `pytest tests/integration/test_memory.py -v`.
- [ ] **Step 3: Commit** `git commit -m "Rebuild the title, summary and memory prompts"`.

---

### Task 11: Close out

**Files:**
- Modify: `backend/PORT-STATUS.md`, `chat-tester/README.md`, `mani-vault/Journal/the-mvp-prompts-are-the-reply-quality-bar.md`

- [ ] **Step 1: Final comparison**: three runs, `--label final-$n`, plus every journey in `eval_replies.py`. muhammad confirms the new replies beat the MVP on every scenario in every style. If not, back to the task that owns the failing behaviour.
- [ ] **Step 2: `PORT-STATUS.md`**: replace the offer-button, "Tell me about this", offer-timing and style entries with what is now true; add buttons-only-at-offers-and-ends, the grounding stage, and the feeling check; move "the three styles barely differ" out of Open if the measurement shows it closed.
- [ ] **Step 3: `chat-tester/README.md`**: the framework-state, calls and raw-turn panels are behind "Show developer details".
- [ ] **Step 4: Journal**: what worked, what did not, with the numbers.
- [ ] **Step 5: Suite and commit**

```bash
pytest -q -rs
git add PORT-STATUS.md ../chat-tester/README.md ../mani-vault/Journal/the-mvp-prompts-are-the-reply-quality-bar.md
git commit -m "Describe the rebuilt conversation"
```
