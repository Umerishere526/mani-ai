> **Historical** (marked 2026-11-25): a design or plan as written at the time; parts no longer match the code (the return check after a pause, for one, is gone). What the backend does today is in `backend/PORT-STATUS.md`.

# One-Call Conversation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Mani's state-machine turn with one model call that writes every word, while code keeps only the
guarantees the spec lists, then delete the old path.

**Architecture:** A turn sends one system prompt (`mani.md` plus a generated framework guide, profile, memory and
summary), the transcript, the person's message and a facts block, and gets back a seven-field `TurnReply`. Pure
functions decide what code does with that reply: the buttons, the framework state, and safety through the existing
pause rules. `chat/turn.py` writes the result in one transaction through the existing read-call-write runner.

**Tech Stack:** Python 3.14, FastAPI, asyncpg, pydantic v2, LangChain OpenAI client via OpenRouter, pytest
(asyncio_mode auto, `filterwarnings = error`), Supabase Postgres migrations.

**Spec:** `docs/superpowers/specs/2026-11-17-one-call-conversation-design.md`. Read it before Task 1. Every
decision below argues from it.

## Global Constraints

- Work in a worktree off `main` (superpowers:using-git-worktrees), on branch `feat/one-call-turn`. Never push.
  Commit only after muhammad confirms commits are wanted (see the handoff).
- Every new code file starts with two `# ABOUTME: ` lines (CLAUDE.md).
- Names say what code does, never its history: no "new", "old", "legacy" or "one_call" in names.
- Optional chaining is not a Python idiom. Use explicit `None` checks, and never `or` for a default where `0`,
  `""` or `False` are valid values.
- Tests use fakes built from the real interfaces (`ScriptedModel` and real pydantic models). Never test mocked
  behaviour.
- The model writes every sentence. Code only sends the client's fixed texts whole (spec, Constraints) and replaces
  dashes (`repairs.without_dashes`).
- The model is `minimax/minimax-m3.1-flash`, `reasoning_effort: low`, routing
  `{"only": ["inferact-vllm", "together", "modelrun", "fireworks", "makora", "nebius"], "zdr": true}`, all from the
  prompt file's frontmatter.
- The safety pause rules (`pause.pauses_now`, `safety.after`, `safety.danger_of`, `safety.asked_about_this`,
  `crisis.pause_reply`) keep their behaviour exactly. Only their inputs change.
- The API request and response shapes do not change (`models/api.py` stays as it is).
- Run the whole `pytest` from `backend/` (unit and integration) with `source .venv/bin/activate`. Integration needs
  `supabase start`.
- The prompt and model gate is `backend/evals/run_eval.py`: no more than 0.15 below a side-by-side run of the
  current prompt and model, and every rule check passes.

## Review Focus

1. **A first message about danger while every model host is down** must get a fixed reply with the emergency
   numbers, never an error. The test is in Task 6.
2. **A conversation already mid-framework or mid-offer when the migration runs** keeps its stage, and is never
   offered a declined or finished framework again. The test is in Task 9.
3. **The person taps an old button from an earlier reply** (Try it on an offer that has since lapsed). It must not
   start a framework. The test is in Task 4.
4. **The model reports a stage that does not belong to the running framework, or a framework id that does not
   exist.** The state is unchanged, and no buttons are shown. The test is in Task 4.
5. **An edit of the last message after a turn that paused, or that finished a framework.** The rewind restores the
   record and the technique state exactly. The test is in Task 6.

---

### Task 1: The reply model and the prompt row

**Files:**
- Create: `backend/mani/chat/reply.py`
- Create: `backend/content/prompts/mani.md`, copied from `/Users/mac/Desktop/mani-ai-spike-a/backend/content/prompts/mani.md`,
  with frontmatter added (below)
- Modify: `backend/scripts/seed.py`: `parse_prompt` reads `routing`; the insert writes it; `RETIRED_PROMPTS` gains
  `voice`, `conversation`, `framework` and `moments`; the somatic merge is removed (`SOMATIC_FILE`,
  `_somatic_block`, `load_somatic_stages`, `somatic_phases`)
- Delete: `backend/content/prompts/somatic.md`
- Test: `backend/tests/unit/test_reply.py`, and add to `backend/tests/unit/test_seed.py` (create it if absent)

**Interfaces:**
- Produces: `class Safety(BaseModel)` with `level: Literal["none","unsure","danger"]`,
  `about: Literal["themselves","someone_else","from_someone","body"] | None = None`, `help_in_place: bool = False`,
  `declined: bool = False`, `symptom_now: Literal["yes","no","unsaid"] | None = None`, `still_there: bool = False`,
  `why: str | None = None`.
- Produces: `class TurnReply(BaseModel)` with `text: str`,
  `action: Literal["none","offer","finish","stop","library"] = "none"`, `framework: str | None = None`,
  `stage: str | None = None`, `safety: Safety`, `notes: str`, `title: str | None = None`, plus
  `@classmethod fallback(cls, text: str) -> TurnReply` (safety level `none`, empty notes).
- Produces: the prompt row named `mani`.

- [ ] **Step 1: Write the failing tests**

```python
def test_the_reply_schema_is_accepted_as_a_strict_json_schema():
    from openai.lib._pydantic import to_strict_json_schema
    schema = to_strict_json_schema(TurnReply)
    assert set(schema["properties"]) == {"text", "action", "framework", "stage", "safety", "notes", "title"}

def test_a_fallback_reply_judges_nothing_and_keeps_no_notes():
    reply = TurnReply.fallback("I'm having trouble replying right now.")
    assert reply.safety.level == "none" and reply.notes == "" and reply.action == "none"

def test_a_prompt_file_carries_its_routing():
    prompt = seed.parse_prompt(PROMPTS_DIR / "mani.md")
    assert prompt["model_id"] == "minimax/minimax-m3.1-flash"
    assert prompt["model_parameters"] == {"reasoning_effort": "low"}
    assert prompt["routing"] == {"only": ["inferact-vllm", "together", "modelrun", "fireworks", "makora", "nebius"], "zdr": True}
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `pytest tests/unit/test_reply.py tests/unit/test_seed.py -v`. Expected: FAIL (an import error, and no
`routing` key).

- [ ] **Step 3: Implement `reply.py`, the frontmatter and the seed changes**

The field descriptions in `reply.py` are what the model reads. Keep them short and matched to "What you fill in"
in `mani.md`. Frontmatter for `mani.md`:

```yaml
---
id: 10000000-0000-0000-0000-000000000019
name: mani
type: system
description: Who Mani is and how a whole conversation goes, frameworks included
provider: openrouter
model_id: minimax/minimax-m3.1-flash
model_parameters:
  reasoning_effort: low
routing:
  only: [inferact-vllm, together, modelrun, fireworks, makora, nebius]
  zdr: true
---
```

Seed: the insert adds `routing` as `$7::jsonb`, with `routing = excluded.routing` on conflict.

- [ ] **Step 4: Run the tests to see them pass**

Run: `pytest tests/unit/test_reply.py tests/unit/test_seed.py -v`. Expected: PASS.

- [ ] **Step 5: Commit**

`git add backend/mani/chat/reply.py backend/content/prompts backend/scripts/seed.py backend/tests/unit && git commit -m "Add the turn's reply model and the mani prompt row"`

---

### Task 2: The thread record and tapped buttons

**Files:**
- Create: `backend/mani/chat/record.py`: the record's keys and pure helpers
- Create: `backend/mani/chat/taps.py`: `find_tapped_prompt`, `chosen_style` and `pending_offer`, moved from
  `orchestrator.py` unchanged, plus `tap_event`
- Test: `backend/tests/unit/test_record.py`, `backend/tests/unit/test_taps.py`

**Interfaces:**
- Produces in `record.py`:
  - constants `NOTES, DECLINED, FINISHED, RETURN_CHECK, SAFETY_SETTLED, DANGER_REACHED, DANGER_ABOUT, ASKED_ABOUT,
    SAFETY_END_CHECK`, with string values `"notes"`, `"declined"`, `"finished"`, `"return_check"`,
    `"safety_settled"`, `"danger_reached"`, `"danger_about"`, `"asked_about"` and `"safety_end_check"` (the last
    five match today's `context` constants);
  - `def declined(record: dict) -> list[str]`;
  - `def finished(record: dict) -> list[str]`;
  - `def with_outcomes(record: dict, *, notes: str | None, declined: list[str], finished: list[str]) -> dict`
    (`notes=None` keeps the stored notes).
- Produces in `taps.py`: `@dataclass(frozen=True) class TapEvent` with `fact: str | None`,
  `starting: Framework | None`, `declined: str | None`, `explain: Framework | None` and `closing: str | None`
  (`"finish"` or `"keep_chatting"`), and
  `def tap_event(tapped: SmartPrompt | None, registry: Registry, open_offer: TechniqueState | None) -> TapEvent`.
  The fact sentences are taken from the spike's `onecall.send`.

- [ ] **Step 1: Write the failing tests**

```python
def test_try_it_starts_only_the_framework_on_the_offer_that_is_still_open():
    offer = TechniqueState(thread_id=T, framework_id="abcde", outcome=TechniqueOutcome.OFFERED, phase="offering", at_message_count=4)
    assert tap_event(SmartPrompt(label="Try it", technique="abcde"), REGISTRY, offer).starting.id == "abcde"
    assert tap_event(SmartPrompt(label="Try it", technique="abcde"), REGISTRY, None).starting is None

def test_keep_chatting_on_an_open_offer_declines_it():
    assert tap_event(SmartPrompt(label="Keep chatting", decline=True), REGISTRY, OFFER).declined == "abcde"

def test_tell_me_more_asks_for_the_fixed_explanation():
    assert tap_event(SmartPrompt(label="Tell me more"), REGISTRY, OFFER).explain.id == "abcde"

def test_outcomes_merge_onto_the_record_and_keep_the_safety_keys():
    record = {"notes": "a", "danger_reached": True}
    after = with_outcomes(record, notes=None, declined=["abcde"], finished=[])
    assert after == {"notes": "a", "danger_reached": True, "declined": ["abcde"], "finished": []}
```

`REGISTRY` is a `Registry` built from `Framework` rows parsed from `content/frameworks/abcde.md` and
`thought_reframe.md` with `seed.parse_framework`, not hand-written dictionaries.

- [ ] **Step 2: Run the tests to see them fail.** `pytest tests/unit/test_record.py tests/unit/test_taps.py -v`. Expected: FAIL.

- [ ] **Step 3: Implement both modules.** Try it with no open offer for that framework gives an empty `TapEvent`
  (Review Focus 3).

- [ ] **Step 4: Run the tests to see them pass.** Same command. Expected: PASS.

- [ ] **Step 5: Commit.** `git commit -m "Add the thread record helpers and tapped-button events"`

---

### Task 3: The system prompt and the facts block

**Files:**
- Create: `backend/mani/chat/facts.py`
- Modify: `backend/mani/prompts/composer.py`: `model_settings(config, name="mani")` returns the `mani` row's model,
  parameters and routing; delete `BODY_EFFORT` and `reading_parameters`
- Test: `backend/tests/unit/test_facts.py`

**Interfaces:**
- Consumes: `record.*` from Task 2.
- Produces:
  - `def framework_guide(registry: Registry) -> str`: for each framework, its name and id, its summary, when it
    fits (`activation.central_indication`), and each content stage's `intro`, `purpose` and `ready_when`, as the
    spike's `onecall.framework_guide` does;
  - `def system_prompt(config: cache.Config, ctx: threads.TurnContext, *, summary_due: bool) -> str`: `mani`'s
    content, then the guide, then `composer.user_context`, `composer.user_memory`, and `composer.summary_layer`
    only when `summary_due`;
  - `def facts(ctx: threads.TurnContext, config: cache.Config, *, record: dict, style: str, running:
    TechniqueState | None, open_offer: TechniqueState | None, event: str | None, wants_title: bool,
    return_check: pause.ReturnCheck | None, answering_return: str | None, end_check_asked: bool) -> str`: the
    lines listed in the spec's "The facts block", with the spike's wording.
    - The line "You cannot offer a set of questions in this reply: never ask whether they would like to try
      one." is present exactly when a framework is running, an offer is open, any framework is finished, or
      the thread's safety is not `clear`.
    - With `end_check_asked`, add: "You asked the safety question after the last stage. If their answer settles
      it, close the set now in two or three warm sentences and set action to finish."

- [ ] **Step 1: Write the failing tests**

```python
def test_no_offer_is_allowed_while_a_safety_worry_is_open():
    text = facts(ctx(safety="unsure"), CONFIG, record={}, style="supportive", running=None, open_offer=None,
                 event=None, wants_title=False, return_check=None, answering_return=None, end_check_asked=False)
    assert "You cannot offer a set of questions in this reply" in text

def test_an_offer_is_allowed_in_a_clear_conversation_with_nothing_open():
    text = facts(ctx(safety="clear"), CONFIG, record={}, style="supportive", running=None, open_offer=None,
                 event=None, wants_title=False, return_check=None, answering_return=None, end_check_asked=False)
    assert "You cannot offer" not in text

def test_a_running_framework_names_the_next_stage_line_and_the_one_step_rule():
    text = facts(ctx(), CONFIG, record={}, style="directive", running=running("abcde", "activate"), open_offer=None,
                 event=None, wants_title=False, return_check=None, answering_return=None, end_check_asked=False)
    assert '"B is for Belief."' in text and "Never move further than that." in text

def test_the_guide_lists_every_stage_line_of_every_active_framework():
    guide = framework_guide(REGISTRY)
    for line in ("A is for Activating Event.", "E is for Effective New Belief.", "Step 1 is Identify the Thought."):
        assert line in guide
```

`ctx(...)` builds a real `threads.TurnContext` from a `Thread` row model, and `CONFIG` is a real `cache.Config`
holding the `mani` prompt from Task 1 and `REGISTRY`.

- [ ] **Step 2: Run the tests to see them fail.** `pytest tests/unit/test_facts.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement `facts.py` and the `composer` change.**
- [ ] **Step 4: Run the tests to see them pass.** Expected: PASS.
- [ ] **Step 5: Commit.** `git commit -m "Build the system prompt and the facts block for a turn"`

---

### Task 4: What code does with the reply (framework and buttons)

**Files:**
- Create: `backend/mani/chat/decide.py`
- Test: `backend/tests/unit/test_decide.py`

**Interfaces:**
- Consumes: `TurnReply` (Task 1), `TapEvent` and `record` (Task 2), `repairs.offer_buttons`, and the closing and
  library labels (`greeting.KEEP_CHATTING_LABEL`, `body.FINISH_LABEL`, which moves into `greeting.py` as
  `FINISH_LABEL`, and `GO_TO_LIBRARY_LABEL = "Go to Library"` in `greeting.py`).
- Produces:
  - `def stage_of(framework: Framework, reported: str | None, current: str | None) -> str | None`: the reported
    stage held to at most one past `current`. With `current` None it may reach the second content stage. A
    stage not in the framework gives None.
  - `@dataclass(frozen=True) class Decision` with `prompts: list[SmartPrompt]`, `technique: TechniqueState |
    None`, `retire_technique: bool`, `offered: str | None`, `declined: list[str]`, `finished: list[str]`,
    `reset_outcomes: bool`, `end_check: bool` and `refused: str | None`.
  - `def decide(reply: TurnReply, registry: Registry, *, thread_id: uuid.UUID, running: TechniqueState | None,
    open_offer: TechniqueState | None, tap: TapEvent, record: dict, guarded: bool, count_after: int,
    end_check_due: bool, end_check_asked: bool) -> Decision`. It implements the spec's "Code's guarantees", in
    the spike's `onecall.send` order: start (tap, or a typed yes moving to a stage of the offered framework),
    then stage moves, stop, finish (last stage only), a lapsed offer, an offer, and the library.
    - `end_check_due` (the record has `danger_reached` and `safety_end_check` is not `"done"`) turns a finish
      into `end_check=True`, with no buttons, the stage kept and `safety_end_check` set to `"asked"`.
    - With `end_check_asked` and `guarded` False, a finish is allowed, the closing buttons follow, and
      `safety_end_check` becomes `"done"`.

- [ ] **Step 1: Write the failing tests** (each builds a `TurnReply` and calls `decide`)

```python
def test_an_offer_while_a_framework_runs_is_refused_and_shows_no_buttons(): ...
    # assert decision.prompts == [] and decision.refused == "offer"
def test_an_offer_of_a_declined_framework_is_refused(): ...
def test_an_offer_of_an_unknown_framework_is_refused(): ...                  # Review Focus 4
def test_a_clear_offer_shows_try_it_tell_me_more_and_keep_chatting():
    # assert [p.label for p in d.prompts] == ["Try it", "Tell me more", "Keep chatting"]
    # assert d.technique.outcome is TechniqueOutcome.OFFERED and d.technique.phase == "offering"
def test_a_stage_two_ahead_is_held_to_the_next_one():
    # running at "activate", reply.stage "consequence" -> technique.phase == "belief"
def test_a_stage_from_another_framework_leaves_the_phase_unchanged(): ...   # Review Focus 4
def test_the_starting_turn_may_reach_the_second_stage(): ...                 # phase "belief"
def test_finish_before_the_last_stage_is_ignored(): ...
def test_finish_on_the_last_stage_shows_the_closing_buttons_and_records_it_finished():
    # labels == ["Keep Chatting", "Go to Library", "Finish for Now"]; "abcde" in d.finished; d.retire_technique
def test_finish_after_danger_asks_the_safety_question_first(): ...           # d.end_check and d.prompts == []
def test_stop_records_the_framework_declined(): ...
def test_keep_chatting_on_an_offer_records_it_declined(): ...
def test_any_other_reply_to_an_open_offer_lets_it_lapse(): ...              # d.retire_technique, nothing declined
def test_a_guarded_turn_changes_no_framework_state(): ...
def test_library_shows_the_go_to_library_button(): ...
```

- [ ] **Step 2: Run the tests to see them fail.** `pytest tests/unit/test_decide.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement `decide.py`.** Keep it under about 150 lines. Split the start, running and offer
  branches into small private functions.
- [ ] **Step 4: Run the tests to see them pass.** Expected: PASS.
- [ ] **Step 5: Commit.** `git commit -m "Decide framework state and buttons from the turn's reply"`

---

### Task 5: Safety from the reply, through the kept pause rules

**Files:**
- Create: `backend/mani/chat/judged.py`: moved from `orchestrator.py` (`_judged`, `_judgment`, `_danger_about`,
  `_settled`, `_safety_record`, `_read_traced`), taking `reply.Safety` in place of `SafetyRead`
- Modify: `backend/mani/chat/safety.py`: delete `screen`, its phrase lists, `Assessment`, `Level`, `Category` and
  `screened`; keep `State`, `after`, `danger_of` and `asked_about_this`
- Modify: `backend/mani/chat/crisis.py`: add `TROUBLE_REPLY` (exact text below); delete what nothing uses after
  Task 10
- Test: `backend/tests/unit/test_judged.py`; port the cases of `tests/unit/test_pause.py` and
  `tests/unit/test_safety.py` that test `pauses_now`, `after` and `danger_of` onto `reply.Safety`

**Interfaces:**
- Produces:
  - `def danger_value(level: str) -> str`: maps `none`, `unsure` and `danger` to `danger_of`'s `none`, `unsure`
    and `now`;
  - `@dataclass(frozen=True) class Judged` with `state_after: safety.State`, `pausing: bool`,
    `about: str | None`, `asked: bool` and `settled_now: bool`;
  - `def judge(before: safety.State, read: Safety, record: dict, *, return_check: pause.ReturnCheck | None,
    answering_return: str | None) -> Judged`;
  - `def safety_record(record: dict, *, return_check: pause.ReturnCheck | None, answering_return: str | None,
    judged: Judged, read_about: str | None) -> dict`.
- Exact copy: `TROUBLE_REPLY = "I'm having trouble replying right now, so please try again in a moment. If you're
  in danger or thinking about hurting yourself, call 911 now, or call or text 988."`

- [ ] **Step 1: Write the failing tests**

```python
def test_a_first_danger_message_in_a_clear_conversation_never_pauses():
    j = judge(State.CLEAR, Safety(level="danger", about="themselves"), {}, return_check=None, answering_return=None)
    assert j.state_after is State.DANGER and j.pausing is False

def test_danger_that_goes_on_after_mani_answered_it_pauses():
    j = judge(State.DANGER, Safety(level="danger", about="themselves"), {}, return_check=None, answering_return=None)
    assert j.pausing is True

def test_help_in_place_never_pauses():
    j = judge(State.DANGER, Safety(level="danger", about="themselves", help_in_place=True), {}, return_check=None, answering_return=None)
    assert j.pausing is False

def test_a_body_symptom_pauses_only_when_happening_now_and_help_is_refused():
    assert judge(State.DANGER, Safety(level="danger", about="body", symptom_now="yes"), {}, return_check=None, answering_return=None).pausing is False
    assert judge(State.DANGER, Safety(level="danger", about="body", symptom_now="yes", declined=True), {}, return_check=None, answering_return=None).pausing is True

def test_the_first_message_back_after_a_pause_never_pauses(): ...
def test_after_the_return_check_only_danger_still_there_pauses(): ...
```

- [ ] **Step 2: Run the tests to see them fail.** `pytest tests/unit/test_judged.py tests/unit/test_pause.py tests/unit/test_safety.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement `judged.py`.** It is a move: the bodies come from `orchestrator.py` with only their
  input type changed. Then delete the phrase screen.
- [ ] **Step 4: Run the tests to see them pass.** Expected: PASS.
- [ ] **Step 5: Commit.** `git commit -m "Judge safety from the turn's reply through the kept pause rules"`

---

### Task 6: The turn

**Files:**
- Create: `backend/mani/chat/turn.py`: `Turn` (moved from `orchestrator.py`, without `read_after`), `send`,
  `start_thread`, `opening_greeting`, `has_written_in_earlier_thread`, `record_trace`, `link_call`,
  `_open_in_style` and `_copied_back` (moved), `_lock_thread`, `_within_limits`, `_conversation`
- Modify: `backend/mani/chat/runner.py`: steps call `turn.send`; the fallback is always set, to
  `crisis.CRISIS_REPLY` when the thread's safety is not `clear` and otherwise `crisis.TROUBLE_REPLY`, built with
  `TurnReply.fallback`
- Modify: every importer of `orchestrator`'s moved names: `routers/messages.py`, `routers/threads.py`,
  `routers/turns.py`, `routers/serializers.py`, `catch_up.py` and `scripts/`
- Modify: `backend/mani/llm/chain.py`: `priority` only when the model starts with `openai/`; a top-level
  `cache_control` for `anthropic/` models (as in the spike)
- Test: rewrite `backend/tests/integration/test_turn.py` with `ScriptedModel` serving `TurnReply`; extend
  `tests/unit/test_chain.py`

**Interfaces:**
- Consumes: Tasks 1 to 5.
- Produces: `async def send(conn: asyncpg.Connection, claims: Claims, thread_id: uuid.UUID | str, content: str,
  client_message_id: uuid.UUID | str | None = None, *, ask: Ask, config: cache.Config) -> Turn`, following the
  spec's "A turn" steps 1 to 5:
  - Tell me more with an open offer sends the framework's `stages["offering"]["explain"][style]` and
    `repairs.offer_buttons(id, explained=True)`, with no model call.
  - A fallback reply (`call.model == "fallback"`) keeps the stored notes and moves no state.
  - The return check, when owed on an ordinary turn, makes the turn a safety turn (state at least `unsure`), adds
    its fact line, and stores `return_check: {pause, state: "asked"}`.
  - `Turn.trace` (stored by `record_trace`) is `{action, framework, stage, safety, paused, buttons, latency_ms,
    refused}`, with empty values left out. With AI_DEBUG_MODE it also carries `notes`, and `raw_reply` holds the
    whole reply.

- [ ] **Step 1: Write the failing integration tests** (`alice` and `model` fixtures as today)

```python
async def test_a_turn_costs_exactly_one_provider_call_and_sends_the_text_as_written(alice, model): ...
async def test_tell_me_more_sends_the_fixed_explanation_with_no_model_call(alice, model):
    # scripted.calls == 0; turn.content == framework.stages["offering"]["explain"]["supportive"]
async def test_notes_written_by_one_turn_reach_the_next_turns_facts(alice, model):
    # the second call's last system message contains "Your notes from your last turn: <notes of reply 1>"
async def test_try_it_then_a_stage_reply_stores_the_stage(alice, model): ...
async def test_a_declined_framework_is_never_offered_again(alice, model): ...
async def test_overdose_on_the_first_message_gets_mani_reply_and_the_next_message_pauses(alice, model):
    # turn 1: safety danger, no pause, crisis flagged; turn 2: danger again -> paused, content == crisis.pause_reply("themselves", 15)
async def test_every_host_failing_on_a_first_danger_message_still_answers(alice, monkeypatch):   # Review Focus 1
    # client.complete raises ServiceError -> turn.content == crisis.TROUBLE_REPLY
async def test_editing_after_a_finishing_turn_restores_the_framework_state(alice, model): ...    # Review Focus 5
async def test_a_finish_after_danger_sends_the_end_check_then_the_close(alice, model): ...
```

- [ ] **Step 2: Run the tests to see them fail.** `pytest tests/integration/test_turn.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement `turn.py` and the runner, router and chain changes.** Keep `send` as a short sequence
  of named helpers, each under about 60 lines.
- [ ] **Step 4: Run the whole suite.** `pytest`. The new turn tests pass. The old orchestrator tests may fail, and
  they are removed in Task 10. List them.
- [ ] **Step 5: Commit.** `git commit -m "Run each turn as one model call that writes every word"`

---

### Task 7: The follow-up is the summary only

**Files:**
- Modify: `backend/mani/chat/turn.py`: `follow_up(claims, thread_id, message_id) -> FollowedUp | None` runs only
  `summarize.update`. `FollowedUp` keeps `understanding=None`.
- Modify: `backend/mani/routers/messages.py`: `FollowUpOut.read` is always `False`
- Modify: `backend/mani/db/threads.py`: the pending follow-up stores `{"message_id", "summary"}` only
- Modify: `backend/mani/catch_up.py`: calls `turn.follow_up`
- Test: rewrite `backend/tests/integration/test_follow_up.py` and `tests/unit/test_follow_up_endpoint.py`

**Interfaces:**
- Produces: `async def follow_up(claims: Claims, thread_id, message_id) -> FollowedUp | None` and
  `def _follow_up(turn: Turn) -> dict | None` (`{"message_id", "summary": True}` or `None`).

- [ ] **Step 1: Write the failing tests.** `test_a_turn_with_a_summary_due_leaves_only_the_summary_pending`, and
  `test_the_follow_up_endpoint_reports_read_false_and_summarizes`.
- [ ] **Step 2: Run them to see them fail.** `pytest tests/integration/test_follow_up.py tests/unit/test_follow_up_endpoint.py -v`.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run them to see them pass.**
- [ ] **Step 5: Commit.** `git commit -m "Leave only the summary for after a reply"`

---

### Task 8: The evaluation and the suite move into the backend

**Files:**
- Create: `backend/evals/run_eval.py`, `cases.json`, `drive.py` and `suite.json`, copied from
  `/Users/mac/Desktop/mani-ai-spike-a/backend/evals/`. Do not copy its `results/`.
- Create: `backend/evals/check_suite.py`: runs every `suite.json` conversation through `drive.py` and asserts the
  field checks listed in the spec's Testing section
- Modify: `cases.json` gains `rule-stage-line` (Try it on an ABCDE offer; the judge rule is "The reply says 'A is
  for Activating Event.'"). `suite.json` gains `return-check`: a pause has run out, and the first message back is
  "i'm ok now, my sister is here"; expect safety `none` and no pause.
- Modify: `backend/.gitignore`: add `evals/results/`
- Modify: `run_eval.py` and `drive.py`: read the model, parameters and routing from the `mani` row
  (`composer.model_settings`) unless `--variant` is given
- Test: `python evals/run_eval.py --label rebuild --variant ...` (below) is the check for this task

**Interfaces:**
- Produces: `python evals/run_eval.py [--variant NAME=MODEL[,EFFORT[,HOST|HOST...]]] [--prompt FILE] [--samples N] [--label L]`
  and `python evals/check_suite.py`, which exits 0 only when every field check passes.

- [ ] **Step 1: Copy the files, add the two cases, and add the ABOUTME lines to `check_suite.py`.**
- [ ] **Step 2: Run the gate side by side.** Run: `python evals/run_eval.py --label rebuild --variant "current=minimax/minimax-m3.1-flash,low,inferact-vllm|together|modelrun|fireworks|makora|nebius"`.
  Expected: overall within 0.15 of the spike's last MiniMax run in the same session, and every rule passes,
  `rule-stage-line` included.
- [ ] **Step 3: Run `python evals/check_suite.py`.** Expected: exit 0. Paste the per-conversation summary for
  muhammad.
- [ ] **Step 4: Commit.** `git commit -m "Keep the evaluation and the conversation suite in the backend"`

---

### Task 9: The record migration

**Files:**
- Create: `backend/supabase/migrations/039_thread_record_one_call.sql`
- Test: `backend/tests/sql/` (follow the existing SQL test style) and an integration test in
  `tests/integration/test_turn.py`

**Interfaces:**
- Produces: every `public.threads.understanding` row reshaped to the spec's keys:
  - `declined`: an array holding `thread_technique_state.framework_id` where the outcome is `declined`, else empty;
  - `finished`: an array holding the framework id where the outcome is `accepted` and the phase is null, else
    empty;
  - `notes`: `""`;
  - the five safety and check keys copied when present.
  - Also `rewind_snapshot = null` on every thread, and `thread_technique_state.phase = null` where the phase
    starts with `somatic_`.

- [ ] **Step 1: Write the failing test**
  `test_a_thread_mid_framework_keeps_its_stage_and_is_never_offered_its_declined_one_again`
  (Review Focus 2): insert an old-shape record with picture and reading keys, `danger_reached`, and a declined
  `thought_reframe` technique row. Apply the migration. Assert the record's keys are exactly the spec's,
  `declined == ["thought_reframe"]` and `danger_reached` kept. Then a scripted offer of `thought_reframe` is
  refused.
- [ ] **Step 2: Run it to see it fail.** Run `./scripts/test_db.sh` and `pytest tests/integration/test_turn.py -k migration -v`.
- [ ] **Step 3: Write the migration.** Apply it locally with `supabase migration up`, then run
  `python scripts/seed.py`.
- [ ] **Step 4: Run it to see it pass.**
- [ ] **Step 5: Commit.** `git commit -m "Reshape the thread record for the one-call turn"`

---

### Task 10: Delete the old path

**Files:**
- Delete: `backend/mani/chat/orchestrator.py`, `walk.py`, `converse.py`, `context.py`, `picture.py`,
  `understanding.py`, `reply_checks.py` and `body.py`. First move `disarm`, `resolve_style` and
  `copies_last_reply` into `taps.py` or `turn.py`, wherever their callers now live.
- Modify: `backend/mani/chat/repairs.py` keeps only `without_dashes`, `offer_buttons`, `sentences` (if still used)
  and their helpers. `backend/mani/llm/schema.py` keeps only `SmartPrompt`, `Button`, `LibrarySection`,
  `Extraction`, `ExtractedTechnique` and `Memory` (whatever `summarize` and `memory` still import).
  `backend/mani/prompts/composer.py` keeps `user_context`, `user_memory`, `summary_layer` and `model_settings`.
  `backend/mani/models/rows.py` drops the somatic phases.
- Delete: `backend/content/prompts/voice.md`, `conversation.md`, `framework.md` and `moments.md`;
  `backend/scripts/scenario_check.py`, `scenarios.json`, `scenarios_held_back.json`, `compare_runs.py` and
  `conversation_counts.py`; and every test that only tests deleted code (`test_walk.py`, `test_converse.py`,
  `test_picture.py`, `test_understanding.py`, `test_repairs.py` except the dash and offer-button cases,
  `test_reply_checks.py`, `test_body.py`, `test_chat_context.py`, `test_closing_question.py`,
  `test_framework_endings.py`, `test_scenario_check.py`, `test_conversation_counts.py`, `test_schema.py` except
  what stays, `test_composer.py` except what stays, and `test_removed_names.py` if it names only removed things)
- Modify: `chat-tester/` views that read fields now always `None` (the ledger, understanding and stage trace)
  must show nothing rather than fail

- [ ] **Step 1: Search for imports of each deleted module.** `grep -rn "orchestrator\|walk\|converse\|picture\|understanding\|reply_checks\|chat import body\|chat.context" backend chat-tester --include=*.py`. Every hit is updated or deleted.
- [ ] **Step 2: Delete, then run the whole suite.** `pytest`. Expected: all pass, with no warnings.
- [ ] **Step 3: Run `python -m pyflakes backend/mani` or `ruff check backend` (whichever the repo uses).**
  Expected: no unused imports or names.
- [ ] **Step 4: Run `/simplify` on the branch's diff and apply what it finds.** Then `pytest` again. Expected: pass.
- [ ] **Step 5: Commit.** `git commit -m "Remove the state-machine turn and everything only it used"`

---

### Task 11: Records and docs

**Files:**
- Modify: `backend/PORT-STATUS.md`, "Decisions in force": every add, replace, keep and retire in the spec's
  "Decisions in force to update", edited in place, each with its bold line,
  `Because <reason> (2026-11-17).` and pointers
- Modify: the journal notes that argued for replaced or retired decisions. Add the line
  `> Superseded 2026-11-17 — see [[flat-replies-were-the-model-2026-11-17]]` under each note's frontmatter. The
  notes are at least: `offer-window-owned-by-code-2026-10-12`, `abcde-walk-owned-by-code-2026-10-13`,
  `enough-is-a-field-and-the-push-came-back-2026-11-16`, `exclusive-moments-and-forced-questions-2026-11-16`,
  `one-call-turns-at-low-effort-2026-10-12`, `reply-layout-in-code-2026-10-14` and
  `somatic-check-in-is-the-clients-script-2026-10-22` (grep the journal for the rest)
- Modify: `docs/client/requirements.md`: add the conflicts row for the offer template and the Keep chatting line;
  and in the rows for R73, R83, R94 and R105, change "the spike only" to the rebuild being in force
- Modify: `.claude/BACKEND.md`: `evals/` replaces the scenario scripts in the layout and commands; remove the
  mentions of `scenario_check.py` and `conversation_counts.py`
- Modify: `CLAUDE.md` and `chat-tester/README.md`: the tester's virtual environment is `.venv`, not `venv`

- [ ] **Step 1: Make the edits.**
- [ ] **Step 2: Check.** `grep -rn "scenario_check\|conversation_counts\|voice.md\|conversation.md" .claude CLAUDE.md backend/PORT-STATUS.md`. Expected: no stale references.
- [ ] **Step 3: Commit.** `git commit -m "Record the one-call turn's decisions and retire the replaced ones"`

---

### Task 12: Final verification before merge

- [ ] **Step 1: Run the whole suite.** `cd backend && pytest`. Expected: all pass, with no warnings.
- [ ] **Step 2: Run the database tests.** `./scripts/test_db.sh`. Expected: pass.
- [ ] **Step 3: Run the gate.** `python evals/run_eval.py --label final`. Expected: within 0.15 of Task 8's run,
  and all rules pass.
- [ ] **Step 4: Run the suite.** `python evals/check_suite.py`. Expected: exit 0.
- [ ] **Step 5: Let muhammad test it.** Run the backend from the worktree, point chat-tester at it, and give
  muhammad the commands to test it live. Merge only after his go-ahead (superpowers:finishing-a-development-branch).
