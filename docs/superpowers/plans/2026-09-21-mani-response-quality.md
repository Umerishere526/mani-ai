# Mani response quality, styles, memory and token control — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Mani's replies behave the way they are specified to — three genuinely distinct
conversation styles, memory that survives a new conversation, and a measured token and cost
ceiling.

**Architecture:** Nothing here adds a new subsystem. The style system, the memory layers and the
quality rules are all already written; most of the work is connecting things that were authored
and never wired, and deleting prompt text that is paid for on every turn and reaches nothing.

**Tech Stack:** FastAPI on Python 3.14, LangChain over OpenRouter (`google/gemini-3-flash-preview`),
Postgres via asyncpg under RLS as `mani_service`, prompts and frameworks seeded from
`backend/content/` into the `admin` schema.

**Spec:** No prior design doc — this plan is written from a direct read of the code, recorded in
Part 1 and Part 2 below. Part 1 is the file map muhammad asked for and is the reference an
implementer should read first.

## Global constraints

Copied from `backend/PORT-STATUS.md` "Decisions already taken — do not re-litigate" and
`.claude/BACKEND.md`. Every task inherits these.

- **One provider call per turn.** The only exception is the exercise hand-off on the turn a
  framework completes. `test_a_turn_costs_exactly_one_provider_call` is exact and must stay exact.
- **OpenRouter is the only provider.** LangSmith stays off — it would receive transcripts, which
  are special-category health data.
- **No streaming in v1.**
- **Six repair checks are code, not model calls.** Do not answer a quality problem with a second
  generation.
- **The static prompt prefix must stay byte-identical across turns.** Layers 1–3 of
  `composer.compose` are what makes provider prefix caching work (measured: 44% cached on an
  immediate repeat). Never insert a varying layer before `response_format`.
- **`clinical_note` is never persisted.** That is a deliberate privacy decision, not an oversight.
- **Activate the venv first:** `cd backend && source .venv/bin/activate`.
- **`pytest.ini` sets `filterwarnings = error`.** A warning fails the suite.
- **Re-seed after any `content/` edit:** `python scripts/seed.py`. Editing a markdown file changes
  nothing at runtime until it is seeded.

---

# Part 1 — The file map

What each file does, what it takes in, what it gives back, and where it can change how Mani sounds.

## 1.1 The authored content (`backend/content/`)

Seeded into Postgres by `scripts/seed.py`, read from the database at runtime. **The running app
never reads these files.**

| File | What it does | Takes | Gives | Reaches the model? |
|---|---|---|---|---|
| `prompts/mani_base.md` | Mani's identity, the three styles, the five supportive moves, the six response shapes, prompt-injection defence, and the full framework procedure. Its frontmatter also selects the chat model and temperature. | — | `admin.prompts` row named `mani_base`; `model_id`, `model_parameters` | **Yes — layer 1, ~4,400 tokens, ~52% of the static prompt** |
| `prompts/response_format.md` | Reply constraints: length, forbidden vocabulary, the `[ctx]` contract, capsule rules, the reasoning field, the clinical note, the pre-answer checklist. | — | `admin.prompts` row named `response_format` | **Yes — layer 3, ~2,550 tokens** |
| `prompts/title_generation.md` | One instruction to produce a 3–6 word thread title. | — | `admin.prompts` row `title_generation` | Only on the turn a title is wanted (~44 tokens) |
| `prompts/summarization.md` | Instructions for the rolling thread summary. Own model (`openai/gpt-oss-120b`), temp 0. | — | `admin.prompts` row `summarization` | **No** — used only by the background summarizer |
| `frameworks/*.md` (×6) | Per-framework clinical definition: activation signals, phase list, and per-stage `purpose` / `listen_for` / `ready_when` / `boundaries` / `if_unclear` / `ask.{supportive,reflective,direct}`. Plus a long prose body. | — | `admin.frameworks` row: `activation`, `phases`, `stages` jsonb, `body` | **Frontmatter only, and only in part.** See below |

**What actually reaches the model from a framework file:** one row in the generated Framework
Index (`name`, `id`, `activation.central_indication`), its `activation.distinctions` entries, and
— only while that framework is running or being offered — the current and next stage's `purpose`,
`listen_for`, `ready_when`, `boundaries`, `if_unclear`, and **one** `ask` line matching the
resolved style. Roughly 150 tokens per framework.

**What reaches nothing.** The prose body below the closing `---` lands in `frameworks.body`, which
no code reads. So the worked examples, the "Responses MANI must avoid" tables and the safety prose
are documentation for humans only. Same for the `summary`, `appropriate_when`, `not_when`,
`redirects` and `activation_conditions` fields. That is roughly 85% of the ~2,000 lines of
framework markdown.

> This matters for the rewrite muhammad is considering: **rewriting the framework prose changes
> nothing about how Mani sounds.** Only the frontmatter is live, and within it only the fields
> listed above.

### Rewriting rules — what must be preserved

- The file must start with `---` on line 1 and have a closing `---`. `seed.py` uses
  `raw.split("---", 2)`, so a stray `---` before the closing one breaks parsing.
- **Prompt bodies are free-form.** Nothing parses the text below the frontmatter. `mani_base.md`
  and `response_format.md` can be rewritten wholesale, headings and all, with zero seeding risk.
- **Never change a prompt's `name:`.** It is the upsert key *and* the lookup key
  (`composer.require("mani_base")`), and `cache.REQUIRED_PROMPTS` refuses to boot without
  `mani_base` and `response_format`.
- **Framework `id`, `name`, `phases` are mandatory.** `phases` must be an ordered list whose
  entries exactly match the `stages:` map keys — a mismatch makes `context._stage_lines` emit a
  bare `stage: <phase>` with no guidance, and the model runs that stage blind. Nothing validates
  this at seed time.
- `ask` must use exactly the keys `supportive`, `reflective`, `direct`.
- `if_unclear` entries need both `when` and `reply` or `context.py:145` raises `KeyError`.

## 1.2 Prompt assembly (`backend/mani/prompts/`)

| File | What it does | Takes | Gives |
|---|---|---|---|
| `cache.py` | Holds one process-global frozen snapshot of all prompts plus the framework `Registry`. Reloads when the TTL expires (**1s in development, 300s in production**). Refuses to boot if `mani_base` or `response_format` is missing. | — | `Config` — `prompts` dict, `registry`, `loaded_at` |
| `composer.py` | Assembles the system prompt from layers in a fixed order, and reads the model settings off the `mani_base` row. | `Config`, `Profile \| None`, `should_generate_title`, `offered`, `summary` | `SystemPrompt(text, layers)`; `model_settings → (model_id, parameters, routing)` |

**Layer order in `compose` — fixed, joined with `\n\n`:**

1. `mani_base` — required, raises if absent
2. `framework_index` — generated from the registry, not authored
3. `response_format` — required
4. `user_context` — only if a profile has a nickname, topics or support style
5. `title_generation` — only when a title is wanted; **silently dropped if the row is missing**
6. `techniques_used` — only if something was already offered
7. `debug` — only when `AI_DEBUG_MODE`
8. `summary` — only if the thread has one

Layers 1–3 are identical for every user and every turn. That is deliberate and is what makes
provider prefix caching work. **Do not put a varying layer before layer 4.**

Editing a prompt row in the database takes effect without a restart. Editing a markdown file does
nothing until `seed.py` runs — and seeding does not invalidate the cache, so expect up to five
minutes of stale prompt in production after a seed.

## 1.3 The per-turn context block (`backend/mani/chat/context.py`)

| Function | Takes | Gives |
|---|---|---|
| `build(ctx, *, shortlist, framework, candidate) -> str` | `TurnContext`, the router's shortlist, the active framework, the candidate framework | The `[ctx]…[/ctx]` string prefixed to the user's message, **this turn only, never stored** |
| `resolve_style(ctx) -> str` | `TurnContext` | `thread.conversation_style` ?? `profile.support_style` ?? `"supportive"` |
| `_stage_lines(prefix, framework, phase, style) -> list[str]` | a stage and a resolved style | the stage's guidance lines, including **one** `ask` for that style |

`build` can emit exactly these lines: `cooldown_passed`, `since_last`, `this_thread`,
`library_pending`, `current_phase`, `history`, `recent_styles`, `framework_shortlist`,
`active_framework`, `framework_stages`, and the `offer_*` / `stage_*` / `next_stage_*` groups.

**There is no `style:` line.** This is the central defect — see Part 2.

## 1.4 Turn logic (`backend/mani/chat/`)

| File | What it does | Takes | Gives |
|---|---|---|---|
| `orchestrator.py` | One user message from arrival to stored reply. Idempotency check, load context, retire a finished technique, resolve button taps, safety screen, router, compose, **one** model call, crisis check, repairs, write the message pair, update thread state. | connection, `Claims`, `thread_id`, `content`, `client_message_id` | `Turn` — reply text, capsules, title, crisis flags, `needs_summary`, and (debug-gated) `reasoning` and `clinical_note` |
| `safety.py` | Deterministic phrase screen before any model call. Crisis locks the thread; concern only suppresses the router. | one message string | `Assessment(level, category, matched)` |
| `router.py` | Deterministic framework shortlisting — substring signal scoring over the last 3 user messages, recency-weighted, then five hardcoded discriminators, then a corroboration gate. **Not a model call, and holds no state.** | last user texts, `activations` dict | `list[Signal]`; `is_confident(signals) -> bool` |
| `repairs.py` | Fixes a reply in code rather than regenerating: strips leaked script metadata, dedupes and trims capsules, drops unknown or already-offered techniques, validates and clamps the phase transition, cleans the title. | `Reply`, `Registry`, turn state | `Repaired(text, prompts, title, framework_id, phase, notes)` |
| `techniques.py` | The framework `Registry` — membership, `get`, `is_final`, `validate_transition`, `clamp`. | seeded framework rows | registry lookups used by repairs and the orchestrator |
| `greeting.py` | The opening line on a new thread, written not generated. | `nickname`, `returning` | `"Hi {nickname}. {opener} How can I support you today?"` |
| `crisis.py` | The crisis reply text and resource list. **`RESOURCES` ships empty** — needs real services from muhammad. | — | `CRISIS_REPLY` |

**The router does not consider:** the style, `not_when` / `appropriate_when` (authored at length,
read by nothing), the authored `distinctions` (the five discriminators are hardcoded Python),
negation ("I'm *not* about to send it" scores as "about to send"), Mani's own messages, the
summary, or already-offered frameworks. It is substring matching only.

## 1.5 The model call (`backend/mani/llm/`)

| File | What it does | Takes | Gives |
|---|---|---|---|
| `chain.py` | Builds the LCEL runnable — a cached `ChatOpenAI` pointed at OpenRouter, with `with_structured_output(..., include_raw=True)`. Holds no conversation state, `max_retries=0`. | schema, model, temperature, max_tokens, routing | a `Runnable`; `usage_from(raw) -> Usage` |
| `client.py` | One attempt, real timeout, one retry on schema failure only, and a cost row written for every call including failures. | messages, schema, model, purpose, ids | `Call(value, model, usage, latency_ms, call_id)` |
| `schema.py` | **The JSON shape Mani must reply in — and every field description is prompt surface the model reads.** `text`, `prompts`, `title`, `crisis`, `state`, `reasoning`, `style`, `clinical_note`. | — | the `Reply` model |
| `tools.py` | `StartExercise`, the one real bound tool call. | — | tool schema |

`schema.py` is an under-appreciated quality lever: the field descriptions are instructions, and
they are sent on every turn.

## 1.6 Persistence (`backend/mani/db/`, `summarize.py`)

| File | What it does | Takes | Gives |
|---|---|---|---|
| `threads.py` | One composed read builds the whole turn snapshot; one collected write applies every change. | connection, ids, `ThreadUpdates` | `TurnContext(thread, profile, technique, techniques_offered, summary, recent_styles)` |
| `messages.py` | `recent_for_context` — **`order by created_at desc limit 20`**, re-sorted ascending. Plus the definer-function write of a message pair. | connection, thread, user | `list[Message]`; `Pair` |
| `profiles.py` | Read/upsert the onboarding profile — `nickname`, `topics`, `support_style`, `age_bracket`. Coalescing upsert so partial edits don't blank. | connection, user, fields | `Profile` |
| `summaries.py` / `summarize.py` | The rolling thread summary. Triggered when `count_after - summarized >= 30`, run as a background task on its own connection, failures swallowed. | thread messages | `ThreadSummary(summary, techniques_tried, summarized_message_count, …)` |
| `llm_calls.py` | Every call's cost row in `admin.llm_calls`. `spend_since()` exists and **has no caller.** | call metadata | `call_id`; spend query |

**The summary is genuinely read back** — `load_turn_context` → `compose(summary=…)` → the
`## Conversation Context` layer, plus `techniques_tried` in `[ctx]` as `history:`.

## 1.7 Quality measurement (`backend/tests/evals/`)

| File | What it does | Takes | Gives |
|---|---|---|---|
| `validators.py` | The specification as executable checks: feeling words the user didn't use, clinical labels, forced positivity, assumed motive, added scale, multiple questions, over-length, standalone mirror inside a framework, capsule rules, repeated openers across a sequence. | a reply, the user message, `in_framework` | `list[Finding]` — empty means it passed |
| `test_negative_set.py` | Runs those checks against examples transcribed from the framework docs. | — | pass/fail |

**`validators.check()` has never been run against a reply the model actually produced.** Every
call site passes a hardcoded string. This is the most valuable asset in the repo for the problem
muhammad is describing, and it is currently pointed at fixtures.

---

# Part 2 — Why the responses are not what you asked for

Ranked by how much of the problem each explains.

### 1. The style never reaches the model on most turns, and the prompt says it does

`mani_base.md:49` — *"Your style comes from the `[ctx]` block alone."* `context.build()` never
emits a style line. The ~35 lines of per-style behavioural instruction at `mani_base.md:61-94`
("Direct leads. Supportive accompanies. Reflective mirrors and explores.") are therefore dead:
nothing ever tells the model which one is in force.

The only thing style changes today is which of three `ask` strings appears in `[ctx]` — and that
code path runs only when a framework is active or a confident candidate exists. The router is
suppressed until two exchanges have passed. **So for the entire opening stretch of every
conversation, and every free-chat turn after it, the three styles are byte-identical.**

This is not the model ignoring instructions. On most turns there are no style instructions to ignore.

### 2. Two sources of style that contradict each other

`composer.user_context` (`composer.py:99-100`) puts `profile.support_style` into the system
prompt as free text. `context.resolve_style` prefers `thread.conversation_style`. Set a thread to
`direct` on a `reflective` profile and the system prompt says reflective while the stage `ask` is
written direct.

### 3. Three spellings of one axis

`mani_base.md` says **Direct**. The enum, the database check constraint and all 52 `ask` keys
say **`direct`**. `profile.support_style` is injected as free text on top. Nothing translates.

### 4. The reachable reply space collapses to one shape

The prompt defines six response shapes and then prohibits most of what would distinguish them: no
labelling, no sympathy line, no feeling word the person didn't use, no added scale, a banned
phrase list, and "presence" gated behind three conditions. What survives is *mirror their words +
ask one question* — every turn. That is very likely what "not what I want" feels like in practice.

Paired with `temperature: 1` (`mani_base.md:9`), which is a poor match for a prompt that is
mostly prohibitions: it produces variance in the wrong places and sameness in the right ones.

### 5. ~1,100 tokens of framework procedure on every turn, including turns with no framework

`mani_base.md:208-265` — the framework cadence, the mid-framework table, the ending sequence with
three verbatim somatic questions — is in layer 1, so it is sent on the first message of a
conversation that may never touch a framework. It costs money and it biases free chat toward
framework-shaped behaviour.

### 6. A ten-message hole in Mani's memory

`CONTEXT_WINDOW = 20` (`messages.py:20`) but `SUMMARY_THRESHOLD = 30` (`orchestrator.py:47`).
Messages older than the last 20 and newer than the last summary checkpoint are in neither. Mani is
silently blind to up to ten messages at a time, in the middle of a conversation.

### 7. Nothing is user-scoped, so Mani cannot recognise anyone

Every durable record — summaries, technique history, response styles — is keyed by `thread_id`. A
new thread starts empty. The only cross-thread signal in the codebase is a boolean that flips the
greeting to "Nice to see you again." Recognising a returning user is a missing table, not a
tuning problem.

### 8. No token budget and no spend ceiling

There is no token counting anywhere. The 20-message window is a row count, not a byte count, so
the worst case is ~80k characters of history — a fixed ceiling nobody measured. `spend_since()`
exists, is indexed, and is called by nothing.

### Smaller, verified

- `threads.vague_streak` — column, grant, no reader and no writer. The pacing rules it belongs to
  are designed and not built.
- `profiles.age_bracket` — collected at onboarding, reaches nothing.
- `create_greeting`'s `p_prompt_options` — added by migration 002 for greeting style capsules;
  `messages.py:186` still calls it with two arguments, so the capsules are never sent.
- `context.py:17-18` claims `conversation_style` "is not wired to any endpoint yet". Stale —
  `routers/threads.py:105` handles it, and `chat-tester` already uses it.
- Several `ask` strings carry meta-instructions inside the question text the model is handed,
  e.g. `abcde.md:188`: `"…what is happening in your body? - use \"easier to accept\" only if the
  user said it"`. The model has to guess which half is speech.
- `abcde.md:121`'s reflective variant is character-identical to its own `if_unclear` fallback at
  `:118`.

---

# Part 3 — The work

Four phases. **Phase 1 is independently valuable and should be done and verified before anything
else** — it is small, it is the highest-leverage change in the repo, and the rest is much easier to
judge once styles actually reach the model.

## Decisions needed from muhammad before Phase 2

1. **Which spelling wins — `direct` or `Direct`?** Changing the prose in `mani_base.md` is a
   one-file edit. Changing the enum means a migration, a check-constraint change, `rows.py`, and
   52 `ask` keys across six files plus a re-seed. **Recommendation: keep the wire value `direct`
   and make the prompt say `direct`**, keeping "Direct" only as a human-facing label in the UI.
2. **What may a cross-conversation memory contain?** This is health data and a product decision,
   not a schema one. Phase 4 is blocked on it.
3. **What is the per-user daily spend ceiling, in dollars?** PORT-STATUS asks for a number rather
   than a guess. Phase 4 is blocked on it.

---

## Phase 1 — Make the style real

### Task 1: Emit the resolved style into the `[ctx]` block

The single highest-value change here. It activates ~35 lines of already-authored instruction that
currently reach nothing, and it makes `mani_base.md:49` true.

**Files:**
- Modify: `backend/mani/chat/context.py:75-76`
- Test: `backend/tests/unit/test_chat_context.py`

**Interfaces:**
- Consumes: `resolve_style(ctx) -> str` (already exists, `context.py:42`)
- Produces: `[ctx]` blocks now always open with a `style: <supportive|reflective|direct>` line

- [ ] **Step 1: Write the failing test**

```python
def test_the_ctx_block_always_names_the_style():
    """mani_base.md tells the model its style comes from [ctx] alone. Before this, [ctx]
    never carried one, so every line of per-style guidance in the prompt was unreachable."""
    ctx = _context(conversation_style=SupportStyle.DIRECT)

    block = context.build(ctx)

    assert "style: direct" in block


def test_the_style_is_named_even_with_no_framework_running():
    """The failure this pins: style only ever reached the model through a framework stage's
    `ask`, so free conversation - most of a conversation - was styleless."""
    ctx = _context(conversation_style=SupportStyle.REFLECTIVE, technique=None)

    block = context.build(ctx, shortlist=[], framework=None, candidate=None)

    assert "style: reflective" in block


def test_the_thread_style_wins_over_the_profile_style():
    ctx = _context(
        conversation_style=SupportStyle.DIRECT,
        profile=Profile(user_id=USER, support_style=SupportStyle.SUPPORTIVE),
    )

    assert "style: direct" in context.build(ctx)
```

Reuse the existing `_context` helper in that file; if its signature does not already accept
`conversation_style` and `profile`, extend it rather than writing a second builder.

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd backend && source .venv/bin/activate
pytest tests/unit/test_chat_context.py -k "names_the_style or no_framework_running or wins_over" -v
```

Expected: FAIL — `assert 'style: direct' in '[ctx]\ncooldown_passed: yes\n[/ctx]\n\n'`

- [ ] **Step 3: Write the implementation**

In `context.build`, replace:

```python
    technique = ctx.technique
    lines: list[str] = []
```

with:

```python
    technique = ctx.technique
    # First line every turn. mani_base states the style comes from this block alone, and until
    # this was here the block never carried one - the only thing style reached was a framework
    # stage's `ask`, so free conversation had no style at all.
    lines: list[str] = [f"style: {resolve_style(ctx)}"]
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
pytest tests/unit/test_chat_context.py -v
```

Expected: PASS, including the pre-existing tests in that file.

- [ ] **Step 5: Run the whole unit suite — the `[ctx]` shape is asserted in several places**

```bash
pytest tests/unit -v
```

Expected: PASS. If a test asserts an exact `[ctx]` string, update it to include the new first
line; do not weaken the assertion to a substring match.

- [ ] **Step 6: Commit**

```bash
git add backend/mani/chat/context.py backend/tests/unit/test_chat_context.py
git commit -m "Name the conversation style in the turn context block"
```

### Task 2: Remove the contradicting style sentence from the system prompt

With Task 1 done, `[ctx]` is the authoritative source. `user_context` still injects the *profile's*
style as free text, which contradicts a thread-level override.

**Files:**
- Modify: `backend/mani/prompts/composer.py:99-100`
- Test: `backend/tests/unit/test_composer.py`

**Interfaces:**
- Consumes: nothing new
- Produces: `user_context(profile)` no longer mentions support style; `compose()` signature unchanged

- [ ] **Step 1: Write the failing test**

```python
def test_the_system_prompt_does_not_name_a_style():
    """Style is [ctx]'s job. Naming the profile's style here contradicted a thread-level
    override: the prompt said one style while the stage ask was written in another."""
    profile = Profile(user_id=USER, nickname="Al", support_style=SupportStyle.REFLECTIVE)

    prompt = composer.compose(_config(), profile)

    assert "style of support" not in prompt.text
    assert "reflective" not in prompt.text.lower()


def test_the_nickname_and_topics_still_reach_the_prompt():
    profile = Profile(user_id=USER, nickname="Al", topics=["anxiety"])

    prompt = composer.compose(_config(), profile)

    assert "Al" in prompt.text
    assert "anxiety" in prompt.text
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
pytest tests/unit/test_composer.py -k "does_not_name_a_style" -v
```

Expected: FAIL — the prompt contains `They asked for a reflective style of support.`

- [ ] **Step 3: Write the implementation**

In `composer.user_context`, delete:

```python
    if profile.support_style:
        lines.append(f"They asked for a {profile.support_style} style of support.")
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
pytest tests/unit/test_composer.py -v
```

Expected: PASS. Existing tests at `test_composer.py:43` and `:136` construct profiles with a
support style and may assert on it — update them to assert the style is absent.

- [ ] **Step 5: Commit**

```bash
git add backend/mani/prompts/composer.py backend/tests/unit/test_composer.py
git commit -m "Leave the conversation style to the turn context block alone"
```

### Task 3: Make the prompt's style vocabulary match the data

Apply muhammad's decision from the list above. This task assumes the recommended answer — the wire
value stays `direct` and the prompt says `direct`.

**Files:**
- Modify: `backend/content/prompts/mani_base.md` (the "The three styles" section and every later
  reference)
- Test: `backend/tests/evals/test_negative_set.py`

- [ ] **Step 1: Write the failing test**

```python
def test_the_prompt_names_the_styles_the_ctx_block_sends():
    """[ctx] sends `style: direct`. A prompt section headed "Direct" is a third spelling
    of the same axis and the model has to guess they are the same thing."""
    from mani.models.rows import SupportStyle

    voice = (PROMPTS_DIR / "mani_base.md").read_text().lower()

    for style in SupportStyle:
        assert f"**{style.value}" in voice, f"[ctx] can send {style.value!r}, prompt never names it"

    assert "Direct" not in voice, "a third spelling of `direct` is still in the prompt"
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
pytest tests/evals/test_negative_set.py -k "names_the_styles" -v
```

Expected: FAIL — `assert 'Direct' not in voice`

- [ ] **Step 3: Edit the content**

In `mani_base.md`, change every `Direct` to `Direct` — the section heading at `:68`, the summary
line at `:93-94`, the presence rule at `:143-144`, the framework explanation at `:192`, the
acceptance line at `:204`, the somatic check-in at `:258`, and the example heading at `:270`. Add
one line under the styles heading so the model can map the `[ctx]` value explicitly:

```markdown
The `[ctx]` block's `style:` line names the one in force for this turn: `direct`,
`supportive`, or `reflective`. It is the only thing that decides your style.
```

- [ ] **Step 4: Re-seed and run the tests**

```bash
python scripts/seed.py
pytest tests/evals -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/content/prompts/mani_base.md backend/tests/evals/test_negative_set.py
git commit -m "Use one name per conversation style across the prompt and the data"
```

---

## Phase 2 — Measure before tuning

Nothing in Phase 3 can be judged without this. Build it before touching prompt content.

### Task 4: A live reply scorecard

A script, not a pytest gate — live model output is too variable to assert on in CI, and the
existing deterministic evals already hold the CI line.

**Files:**
- Create: `backend/scripts/eval_replies.py`
- Create: `backend/scripts/eval_conversations.yaml`

**Interfaces:**
- Consumes: `tests.evals.validators.check`, `check_capsules`, `repeated_openers`;
  `mani.chat.orchestrator.send`
- Produces: a per-style scorecard on stdout, and a non-zero exit if any style scores worse than
  the baseline recorded in the file's docstring

- [ ] **Step 1: Write the scenario file**

`backend/scripts/eval_conversations.yaml` — start with three conversations of four turns each,
taken from the worked examples already in the framework files so the expected shape is known:

```yaml
- name: anxiety_free_chat
  turns:
    - "I have a presentation tomorrow and I keep going over it"
    - "I keep thinking I'll freeze halfway through"
    - "I don't know, I just want it to be over"
    - "yeah maybe"
- name: criticism_abcde
  turns:
    - "My manager criticized my presentation in front of everyone"
    - "She said two of my recommendations did not have enough support"
    - "I stopped speaking and avoided her afterward"
    - "I keep thinking I am incompetent"
- name: withdrawal_behavioral_activation
  turns:
    - "I have been in bed all day"
    - "I have ignored everyone's messages for a week"
    - "I don't see the point"
    - "I guess I could answer one"
```

- [ ] **Step 2: Write the script**

```python
# ABOUTME: Runs scripted conversations through the real stack and scores every reply.
# ABOUTME: The validators already encode the specification; this points them at live output.

from __future__ import annotations

import argparse
import asyncio
import pathlib
import sys

import yaml

from mani.auth.jwt import Claims
from mani.chat import orchestrator
from mani.db import pool, threads
from mani.models.rows import SupportStyle
from tests.evals import validators

SCENARIOS = pathlib.Path(__file__).with_name("eval_conversations.yaml")


def _claims_for(user_id: str) -> Claims:
    """Claims carries the verified token's `sub`; `user_id` is a read-only property on it.
    Same shape tests/integration/test_queries.py:24 uses."""
    return Claims(sub=user_id, raw={"sub": user_id, "role": "authenticated"})


async def _run_one(user_id: str, style: SupportStyle, turns: list[str]) -> list[tuple[str, str]]:
    """One conversation in one style. Returns (user message, reply) pairs."""
    claims = _claims_for(user_id)
    exchanges: list[tuple[str, str]] = []

    async with pool.as_user(claims) as conn:
        async with conn.transaction():
            thread, _ = await orchestrator.start_thread(conn, claims)
            await threads.apply(
                conn, thread.id, user_id, threads.ThreadUpdates(conversation_style=style)
            )

    for message in turns:
        async with pool.as_user(claims) as conn:
            async with conn.transaction():
                turn = await orchestrator.send(conn, claims, thread.id, message)
        exchanges.append((message, turn.content))

    return exchanges


def _score(exchanges: list[tuple[str, str]]) -> list[validators.Finding]:
    findings = [
        finding
        for message, reply in exchanges
        for finding in validators.check(reply, message)
    ]
    return findings + validators.repeated_openers([reply for _, reply in exchanges])


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", required=True, help="an existing auth user id to run as")
    parser.add_argument("--verbose", action="store_true", help="print every reply")
    args = parser.parse_args()

    scenarios = yaml.safe_load(SCENARIOS.read_text())
    failures = 0

    # pool.as_user() needs the pool open; nothing here runs under FastAPI's lifespan.
    await pool.open_pool()

    for style in SupportStyle:
        for scenario in scenarios:
            exchanges = await _run_one(args.user, style, scenario["turns"])
            findings = _score(exchanges)
            failures += len(findings)

            print(f"\n=== {scenario['name']} / {style.value} ===")
            if args.verbose:
                for message, reply in exchanges:
                    print(f"  > {message}\n  < {reply}\n")
            for finding in findings:
                print(f"  FAIL {finding}")
            if not findings:
                print("  clean")

    await pool.close_pool()
    print(f"\ntotal findings: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
```

- [ ] **Step 3: Run it against local Supabase and a live model**

```bash
cd backend && source .venv/bin/activate
supabase start
python scripts/seed.py
python scripts/eval_replies.py --user <a real auth user id> --verbose
```

Expected: it completes and prints a finding count per style. **Record that number — it is the
baseline every later change is judged against.** A first run with findings is the correct outcome;
a run with zero findings before any prompt work means the scenarios are too easy, so add harder
ones.

- [ ] **Step 4: Check the styles actually differ**

Read the three transcripts of the same scenario side by side. If they are near-identical after
Phase 1, that is a finding worth stopping on — report it rather than proceeding to Phase 3.

- [ ] **Step 5: Commit**

```bash
git add backend/scripts/eval_replies.py backend/scripts/eval_conversations.yaml
git commit -m "Score live replies against the specification validators"
```

---

## Phase 3 — Prompt content

Each task here is one change, measured against the Phase 2 baseline. **Do not batch them** — the
whole point of the scorecard is knowing which change did what.

### Task 5: Load the framework procedure only when a framework is involved

Saves ~1,100 tokens on every non-framework turn and stops free chat being pushed toward
framework-shaped behaviour.

**Files:**
- Create: `backend/content/prompts/framework_procedure.md`
- Modify: `backend/content/prompts/mani_base.md` (remove the moved sections)
- Modify: `backend/mani/prompts/composer.py:137-178`
- Modify: `backend/mani/chat/orchestrator.py:251-257`
- Test: `backend/tests/unit/test_composer.py`

**Interfaces:**
- Consumes: `Config.prompt("framework_procedure")`
- Produces: `compose(config, profile, *, should_generate_title=False, offered=None, summary=None,
  framework_engaged: bool = False) -> SystemPrompt`

- [ ] **Step 1: Write the failing test**

```python
def test_the_framework_procedure_is_absent_from_a_free_chat_turn():
    """It is ~1,100 tokens of cadence, mid-framework table and ending sequence. On a turn with
    no framework it is paid for and it biases the reply toward framework shapes."""
    prompt = composer.compose(_config(), None, framework_engaged=False)

    assert "framework_procedure" not in {name for name, _ in prompt.layers}


def test_the_framework_procedure_is_present_once_a_framework_is_engaged():
    prompt = composer.compose(_config(), None, framework_engaged=True)

    assert "framework_procedure" in {name for name, _ in prompt.layers}


def test_the_cached_prefix_is_identical_either_way():
    """Layers 1-3 are what the provider caches. A conditional layer must go after them or
    caching breaks on every framework turn."""
    free = composer.compose(_config(), None, framework_engaged=False)
    engaged = composer.compose(_config(), None, framework_engaged=True)

    assert [name for name, _ in free.layers][:3] == [name for name, _ in engaged.layers][:3]
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
pytest tests/unit/test_composer.py -k "framework_procedure or cached_prefix" -v
```

Expected: FAIL with `TypeError: compose() got an unexpected keyword argument 'framework_engaged'`

- [ ] **Step 3: Move the content**

Create `backend/content/prompts/framework_procedure.md` with this frontmatter, then move
`mani_base.md`'s "Offering a framework", "Running a framework" and "Ending a framework" sections
(`:176-265`) into its body, deleting them from `mani_base.md`:

```markdown
---
name: framework_procedure
description: How to offer, run and end a framework. Sent only on turns where one is involved.
---
```

- [ ] **Step 4: Write the implementation**

In `composer.compose`, add the parameter and the layer — **after `response_format`**, so layers
1–3 stay byte-identical:

```python
def compose(
    config: Config,
    profile: Profile | None,
    *,
    should_generate_title: bool = False,
    offered: list[str] | None = None,
    summary: ThreadSummary | None = None,
    framework_engaged: bool = False,
) -> SystemPrompt:
```

and after the `response_format` entry in `candidates`:

```python
    if framework_engaged:
        procedure = config.prompt("framework_procedure")
        candidates.append(
            ("framework_procedure", procedure.content if procedure else None)
        )
```

In `orchestrator.send`, pass it — a framework is engaged when one is running or a confident
candidate exists:

```python
    system = composer.compose(
        config,
        ctx.profile,
        should_generate_title=wants_title,
        offered=offered_now,
        summary=ctx.summary,
        framework_engaged=technique is not None or candidate is not None,
    )
```

- [ ] **Step 5: Re-seed and run the tests**

```bash
python scripts/seed.py
pytest tests/unit -v
```

Expected: PASS.

- [ ] **Step 6: Measure**

```bash
python scripts/eval_replies.py --user <id>
```

Compare the finding count against the Phase 2 baseline, and check `admin.llm_calls.input_tokens`
for a free-chat turn — it should drop by roughly 1,100.

- [ ] **Step 7: Commit**

```bash
git add backend/content/prompts backend/mani/prompts/composer.py backend/mani/chat/orchestrator.py backend/tests/unit/test_composer.py
git commit -m "Send the framework procedure only on turns that involve a framework"
```

### Task 6: Lower the temperature

One-line change, measured. `temperature: 1` with a prompt that is largely prohibitions produces
variance where consistency is wanted.

**Files:**
- Modify: `backend/content/prompts/mani_base.md:9`

- [ ] **Step 1: Record the current score**

```bash
python scripts/eval_replies.py --user <id> > /tmp/before.txt
tail -1 /tmp/before.txt
```

- [ ] **Step 2: Change the temperature**

In `mani_base.md` frontmatter, set `temperature: 0.7`.

- [ ] **Step 3: Re-seed and measure**

```bash
python scripts/seed.py
python scripts/eval_replies.py --user <id> > /tmp/after.txt
diff <(tail -1 /tmp/before.txt) <(tail -1 /tmp/after.txt)
```

Keep whichever scores better. If they tie, keep `0.7` — it is the cheaper failure mode.

- [ ] **Step 4: Commit**

```bash
git add backend/content/prompts/mani_base.md
git commit -m "Lower the chat temperature to suit a constraint-heavy prompt"
```

### Task 7: Widen the reachable reply space

This is muhammad's content judgment, not an engineering change, so it is deliberately specified as
a measured experiment rather than a prescribed rewrite.

**Files:**
- Modify: `backend/content/prompts/response_format.md:105-174`
- Modify: `backend/content/prompts/mani_base.md:139-154` (the presence conditions)

- [ ] **Step 1: Read the three transcripts from Phase 2 and name the actual complaint**

Write down, in one sentence, what is wrong with the replies. "Too interrogative", "too flat",
"every reply has the same shape" are different problems with different fixes.

- [ ] **Step 2: Change exactly one thing**

Candidates, in the order I would try them:
1. Relax the presence gate at `mani_base.md:147` so a reply may stay with the person without a
   question more often than the current three conditions allow.
2. Cut the 11-row failure table at `response_format.md:136-151` — roughly 900 tokens of abstract
   prohibitions that a model weights far below the concrete banned-phrase list above them.
3. Split the meta-instructions out of the `ask` strings into a separate `ask_note` key, so the
   model is not handed guidance and utterance in one sentence.

- [ ] **Step 3: Re-seed, measure, keep or revert**

```bash
python scripts/seed.py && python scripts/eval_replies.py --user <id>
```

- [ ] **Step 4: Commit whichever change won**

```bash
git add backend/content/prompts
git commit -m "<what changed and what it was measured to do>"
```

---

## Phase 4 — Memory and cost

### Task 8: Close the memory hole

**Files:**
- Modify: `backend/mani/chat/orchestrator.py:47`
- Test: `backend/tests/unit/test_chat_context.py`

- [ ] **Step 1: Write the failing test**

```python
def test_the_summary_refreshes_before_the_window_slides_past_it():
    """The summary covers up to its checkpoint; history covers the last CONTEXT_WINDOW
    messages. If the refresh threshold exceeds the window, messages older than the window and
    newer than the checkpoint are in neither, and Mani is silently blind to them."""
    from mani.chat.orchestrator import SUMMARY_THRESHOLD
    from mani.db.messages import CONTEXT_WINDOW

    assert SUMMARY_THRESHOLD <= CONTEXT_WINDOW
```

- [ ] **Step 2: Run it to verify it fails**

```bash
pytest tests/unit/test_chat_context.py -k "slides_past" -v
```

Expected: FAIL — `assert 30 <= 20`

- [ ] **Step 3: Change the threshold**

In `orchestrator.py`, replace the constant and its comment:

```python
# How many new messages accumulate before the rolling summary is refreshed. Kept at or below
# messages.CONTEXT_WINDOW: the summary covers up to its checkpoint and history covers the last
# window, so a larger threshold leaves messages in neither.
SUMMARY_THRESHOLD = 15
```

- [ ] **Step 4: Run the suite**

```bash
pytest tests/unit tests/integration -v
```

Expected: PASS. Integration tests skip without a database — check the skip count is not the whole
suite.

- [ ] **Step 5: Commit**

```bash
git add backend/mani/chat/orchestrator.py backend/tests/unit/test_chat_context.py
git commit -m "Refresh the thread summary before the context window slides past its checkpoint"
```

### Task 9: A per-user memory Mani can greet you with

**Blocked on decision 2.** Do not start until muhammad has said what a cross-conversation memory
may contain.

**Files:**
- Create: `backend/supabase/migrations/003_user_memory.sql`
- Create: `backend/mani/db/user_memory.py`
- Modify: `backend/mani/summarize.py`
- Modify: `backend/mani/db/threads.py` (`_TURN_CONTEXT_SQL`, `TurnContext`)
- Modify: `backend/mani/prompts/composer.py`
- Test: `backend/tests/integration/test_queries.py`, `backend/tests/sql/test_rls.sql`

**Interfaces:**
- Produces: `user_memory.get(conn, user_id) -> UserMemory | None`,
  `user_memory.upsert(conn, user_id, *, summary: str) -> UserMemory`;
  `composer.user_memory_layer(memory: UserMemory | None) -> str | None`

- [ ] **Step 1: Write the migration**

```sql
-- ABOUTME: What Mani remembers about a person across conversations, not within one.
-- ABOUTME: RLS from creation; the backend writes it, the person may read and delete it.

create table public.user_memory (
  user_id    uuid primary key references auth.users(id) on delete cascade,
  summary    text not null,
  updated_at timestamptz not null default now()
);

alter table public.user_memory enable row level security;

create policy user_memory_select on public.user_memory
  for select using ((select auth.uid()) = user_id);
create policy user_memory_insert on public.user_memory
  for insert with check ((select auth.uid()) = user_id);
create policy user_memory_update on public.user_memory
  for update using ((select auth.uid()) = user_id);
create policy user_memory_delete on public.user_memory
  for delete using ((select auth.uid()) = user_id);

grant select, delete on public.user_memory to authenticated;
grant select, insert, update on public.user_memory to mani_service;
```

The person can read and delete their own memory but not write it — writing is Mani's job, and a
client that could write it could put words in Mani's mouth about themselves.

- [ ] **Step 2: Add the RLS assertion**

Append to `backend/tests/sql/test_rls.sql`, following the pattern already used there for
`thread_summaries`: assert a second user cannot select another user's `user_memory` row, and that
`authenticated` holds no INSERT or UPDATE privilege on the table.

- [ ] **Step 3: Apply and verify the schema**

```bash
supabase db reset
./scripts/test_db.sh
```

Expected: PASS, including the new assertions.

- [ ] **Step 4: Write the read and write functions**

`backend/mani/db/user_memory.py`, modelled directly on `backend/mani/db/summaries.py` — same
shape, same "caller owns the transaction" contract.

- [ ] **Step 5: Write it from the summarizer, read it into the prompt**

Extend `summarize.update` to also upsert the user-level memory, add `user_memory` to
`_TURN_CONTEXT_SQL` and `TurnContext`, and add a `user_memory` layer to `composer.compose`
positioned next to `user_context` — **after `response_format`**, so the cached prefix is unaffected.

- [ ] **Step 6: Test the round trip**

```bash
pytest tests/integration/test_queries.py -v
```

Add a test asserting a memory written on one thread is present in a second thread's `TurnContext`.

- [ ] **Step 7: Commit**

```bash
git add backend/supabase/migrations/003_user_memory.sql backend/mani/db/user_memory.py backend/mani/summarize.py backend/mani/db/threads.py backend/mani/prompts/composer.py backend/tests
git commit -m "Remember a person across conversations, not only within one"
```

### Task 10: A per-user spend ceiling

**Blocked on decision 3.** `llm_calls.spend_since()` already exists and is indexed; this is wiring,
not building.

**Files:**
- Modify: `backend/mani/config.py`
- Modify: `backend/mani/chat/orchestrator.py` (before `client.complete`)
- Test: `backend/tests/unit/test_config.py`, `backend/tests/integration/test_turn.py`

- [ ] **Step 1: Add the setting**

```python
    # Refuse a turn once a person has spent this much in the trailing 24 hours. Zero disables
    # the check. A number from muhammad, not a guess - see PORT-STATUS "Open".
    daily_spend_ceiling_usd: float = 0.0
```

- [ ] **Step 2: Write the failing test**

```python
async def test_a_turn_is_refused_once_the_daily_ceiling_is_spent(alice, monkeypatch):
    """Without this a person can send unlimited 4000-character turns, each costing a full
    system prompt plus twenty messages."""
    monkeypatch.setattr(get_settings(), "daily_spend_ceiling_usd", 0.01)
    ...
    with pytest.raises(ServiceError) as raised:
        await orchestrator.send(conn, claims, thread.id, "hello")

    assert raised.value.category is ErrorCategory.RATE_LIMITED
```

- [ ] **Step 3: Run it to verify it fails, implement the check, run it again**

The check goes in `orchestrator.send` immediately before `client.complete`, raising a
`ServiceError` with `ErrorCategory.RATE_LIMITED` and a user message that does not mention money.

- [ ] **Step 4: Commit**

```bash
git add backend/mani/config.py backend/mani/chat/orchestrator.py backend/tests
git commit -m "Refuse a turn once a person passes their daily spend ceiling"
```

---

# Part 4 — Deliberately not in this plan

- **Rewriting the framework markdown prose.** It reaches nothing. If it is wrong it should be
  fixed as documentation, but it is not a response-quality lever.
- **A separate persona layer.** `mani_base.md` already is one. Task 5 improves it by removing
  procedure, which is the opposite of adding a layer.
- **Making the router smarter** — embeddings, negation handling, reading `not_when`. Real gaps,
  but framework *selection* is not what muhammad reported as wrong, and the corroboration gate
  already makes a bad pick cost relevance rather than safety.
- **`vague_streak` and the pacing rules.** Designed, not built, and tracked in Linear rather than
  here.
- **Streaming.** Ruled out for v1, and the several-second turn latency is a separate problem with
  a separate answer.
