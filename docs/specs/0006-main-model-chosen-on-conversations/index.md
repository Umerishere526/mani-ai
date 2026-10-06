# 0006. The main model is chosen on real conversations, first step: Gemini 3.8 Flash

**Date**: 2026-10-05
**Status**: In Progress

## Summary

Every reply Mani writes, and every summary and memory fold, comes from `google/gemini-3.1-flash-lite`, the smallest Gemini tier. On 5 October it failed the framework choice in three of five test chats because it reads the fact checklist by topic and changes it every turn (spec 0005, AC-17). This spec makes the first, cheapest step of scope row 35: test one stronger model from the same family, Gemini 3.8 Flash, on the chats that failed, with low reasoning effort, on Google Vertex's standard tier, the only route for it that keeps no data. If it gets every chat right, it becomes the main model (chat replies, titles and the exercise pick); summaries and memory folding stay on the lite model. The wider comparison across other families and open models stays open on row 35, and the production cost limit is left to the client, who gets the measured cost per conversation.

## Requirements

**User stories**:
- As a person talking to Mani, I want the framework it offers to match what I actually said, so that I am not offered the wrong kind of help.
- As muhammad, I want the model choice made on our own chats and recorded with its cost and speed, so that the client can set the cost limit from real numbers.

**Acceptance criteria**:
- **AC-1** (reasoning effort and room reach the call): `mani_base`'s `model_parameters` may hold `reasoning_effort` (`low`, `medium` or `high`; any other value is refused when the prompt is loaded) and `maxTokens`. The orchestrator passes the effort with temperature and max tokens to `client.complete` at its two chat call sites, `client.complete` passes it to `chain.build`, and `chain.build` sends it as `"reasoning": {"effort": ...}` inside the request body it already builds (the `extra_body` JSON), never through LangChain's own `reasoning` or `reasoning_effort` arguments, which switch the call to a different OpenAI API. With no effort set, nothing is sent, as today. `client.choose_exercise` takes the same effort and a `max_tokens` of its own from the same parameters (`exerciseMaxTokens`, default 200 as today). Unit tests: the request body with and without an effort, a refused effort value, and that the chain's cache key stays stable.
- **AC-2** (routing from the prompt file): `scripts/seed.py` writes a prompt file's `routing` frontmatter into `admin.prompts.routing`, in both the insert and the update of its upsert, and an absent `routing` seeds `{}`. The files are authoritative: reseeding replaces routing set through the admin portal, as it already replaces the model and the content. A unit test asserts the parse.
- **AC-3** (the runner tries a model without touching the app): `scripts/eval_replies.py` gains `--model`, `--reasoning-effort`, `--max-tokens` and `--provider`. When `--model` is given, the runner replaces `composer.model_settings` in its own process with one that returns the given model, the parameters with the effort and max tokens applied, and routing `{"order": [<provider>], "allow_fallbacks": false, "zdr": true, "require_parameters": true}`. Zero retention is on by default and cannot be turned off by a flag; `--model` without `--provider` is refused. The first draft, the redraft, titles and the exercise pick all use the override; summaries and memory folding keep their own rows. Seeded prompts, the database and the running app are untouched. The run header prints the model, effort, max tokens, routing and the git commit and seeded prompt digest in force.
- **AC-4** (no silent downgrade): the candidate's routing is the AC-3 routing with `order: ["google-vertex/global"]`, with `data_collection: deny` as today. If OpenRouter refuses it (the tag is not accepted as an order entry, no zero retention endpoint serves the model, or an endpoint cannot honour structured output or reasoning), the run stops on the first call with the provider's message, and the result goes back to muhammad; it never falls back to another tier or to an endpoint that keeps data. The first call's reported cost (`usage.cost`, which the request already asks for) confirms the tier: it must match the Vertex standard prices.
- **AC-5** (the measurement, asked first): only once muhammad says yes at that moment, with `--model google/gemini-3.8-flash --reasoning-effort low --max-tokens 4096 --provider google-vertex/global --style supportive --verbose`, the runner runs `stress_nothing_named_yet`, `grief_dog_steering` and `deadlines_steering` three times each, `panic_attack_grounding` and `manager_embarrassed_me` once each, and `journey_abcde` once (a whole framework, so the exercise pick runs), after a reseed, recording the commit. Each run is its own invocation. Before it removes its users, the runner prints per thread, from `admin.llm_calls` with `purpose` chat and the candidate model: calls, schema failures, input, cached and output tokens, and cost as (input minus cached) × 0.75 + cached × 0.075 + output × 3.75 per million; and per turn the wall time of `orchestrator.send`, which it measures itself. User removal moves into a `finally`, so a stopped run leaves nothing behind. A provider rate limit or a timeout counts as a failed turn and is reported, never retried silently. Recorded per chat: whether the expected outcome was met (stress: no offer by message 4; grief: an offer, never Behavioral Activation; deadlines: Structured Problem Solving; panic: DBT STOP; manager: ABCDE; journey: reaches the body check and an exercise is picked by the model, not the first candidate by default), the `[choice]` lines, the validators' FAIL lines against the lite model's runs of the same chats, schema failures, redrafts, reply times and cost. Reasoning tokens are inside the output tokens and are not reported separately.
- **AC-6** (the decision rule): Gemini 3.8 Flash replaces the lite model for chat replies when every run meets its expected outcome (stress, grief and deadlines in 3 of 3, the other three once) and no call has a schema failure, counting one that only succeeded on the client's own retry. Then `mani_base.md` sets `model_id: google/gemini-3.8-flash`, `model_parameters` with `reasoning_effort: low` and `maxTokens: 4096` (temperature unchanged), and `routing` as in AC-4; `python scripts/seed.py`; the whole `pytest` passes. Summaries and memory folding keep the lite model. Cost per conversation, reply times and the FAIL line comparison go to muhammad for the client; they do not gate the switch. If any run misses, nothing switches and the result goes back to muhammad as it is: one model, effort and route failed these chats, which is not on its own proof that the design is wrong. No second effort level is tried without his yes.
- **AC-7** (records): a journal note with the runs and figures, whatever the outcome; on a switch, ADR 015 (the main model, its route and why), `backend/PORT-STATUS.md`'s model line and latest measurements; in PORT-STATUS, whatever the outcome, that production chat on AI Studio is probably not zero retention today, and that summaries and memory folding are not; the follow ups of spec 0002 and spec 0005 that wait on the chosen model noted there.

## Decision

**Chosen option**: Option 1: test Gemini 3.8 Flash on the chats that failed and a full journey, low reasoning effort, Vertex standard with zero data retention, and switch the main model only if every run passes.

**Implementation skills**: none (backend Python and content).

## Feature design

**Data model sketch**: no schema change. `admin.prompts.routing` (jsonb, already present) starts being written by the seeder from the `routing` frontmatter. `admin.prompts.model_parameters` may hold `reasoning_effort`, `maxTokens` and `exerciseMaxTokens`.

**Interface surface**:

| Surface | Change |
|---|---|
| `mani_base.md` frontmatter | on a switch: `model_id`, `model_parameters` (`reasoning_effort`, `maxTokens`), `routing` |
| `scripts/seed.py` | writes `routing` (insert and update) |
| `mani/chat/orchestrator.py` | passes the effort to `client.complete` at both chat call sites and to `client.choose_exercise` |
| `mani/llm/client.py` | `complete` and `choose_exercise` take the effort and pass it on |
| `mani/llm/chain.py` `build` | puts `reasoning.effort` in the request body |
| `mani/prompts/cache.py` (or where prompts are read) | refuses an unknown `reasoning_effort` |
| `scripts/eval_replies.py` | the flags, the `composer.model_settings` override, the run header, per thread figures before cleanup, cleanup in `finally`, per turn wall time |

**Value sourcing**:

| Action | Value | Source |
|---|---|---|
| a chat, title or exercise call | model id, parameters, routing | `composer.model_settings` (the `mani_base` row), or the runner's replacement of it (AC-3) |
| a chat call | reasoning effort, max tokens | `model_parameters.reasoning_effort` and `maxTokens` (AC-1); none sent and 2048 when absent |
| the exercise pick | max tokens | `model_parameters.exerciseMaxTokens`, default 200 |
| a chat call | provider order, fallbacks, zero retention, parameter requirement | `admin.prompts.routing` merged over `settings.routing` (AC-2), or the runner's routing (AC-3) |
| the tier check | the cost of the first call | OpenRouter's `usage.cost`, compared with the Vertex standard prices (AC-4) |
| the measurement | expected outcome per chat | AC-5's list |
| the measurement | reply time | the runner's own timing of each `orchestrator.send` |
| the measurement | cost per conversation | `admin.llm_calls` input, cached and output tokens per thread, read before cleanup, with AC-5's formula |
| the measurement | schema failures | `admin.llm_calls.outcome` per thread, read before cleanup |
| the baseline | the lite model's results | journal `framework-fit-from-facts-first-runs-2026-10-05`: run 4 for stress, grief and deadlines (today's design); run 1 for panic and manager. No stored times or costs exist for it. |

**Key invariants**:
- No candidate call goes to an endpoint that keeps data, or to another tier than the one named; a refusal stops the run.
- The runner's override never reaches seeded prompts, the database or another process.
- Summaries and memory folding do not change in this spec.

**Security model**: no change to access. Test conversations use the runner's fresh users, removed after every run, stopped or not. `data_collection: deny` stays on every call; `zdr: true` is added for the candidate and, on a switch, for chat replies, titles and the exercise pick.

**Critical test scenarios**:
- Reasoning effort in the request body when set, absent when not, an unknown value refused, verifies **AC-1**.
- Routing frontmatter seeded on insert and on update, absent frontmatter seeds `{}`, verifies **AC-2**.
- The runner's override changes only its own process's model settings, and `--model` without `--provider` is refused, verifies **AC-3**.
- A refused route stops the run, shows the provider's message and still removes the run's users, verifies **AC-4**, **AC-5**.

## Build plan

Tracer Bullet: the plumbing for one candidate call end to end first (tasks 1 to 3), then the paid run, then the switch or the record.

1. Reasoning effort and max tokens from the parameters through the orchestrator, `client.complete`, `client.choose_exercise` and `chain.build`; refuse an unknown effort; unit tests. Satisfies **AC-1**.
2. `scripts/seed.py` writes `routing`; unit test. Satisfies **AC-2**.
3. `scripts/eval_replies.py`: the flags, the `composer.model_settings` override, the run header, per turn timing, per thread figures before cleanup, cleanup in `finally`. Satisfies **AC-3**, **AC-4**, **AC-5** (the runner part).
4. Ask muhammad; reseed; run the twelve invocations; collect outcomes, FAIL lines, schema failures, reply times and cost. Satisfies **AC-5**.
5. If every run passes: set `mani_base.md`'s model, parameters and routing, reseed, run the whole `pytest`. Otherwise change nothing. Satisfies **AC-6**.
6. Journal note; PORT-STATUS (the retention finding whatever the outcome); on a switch, ADR 015 and the spec 0002 and 0005 follow ups noted. Satisfies **AC-7**.

## Consequences

**Positive**:
- Answers, for about 0.70 dollars, whether a stronger model passes the chats spec 0005 failed.
- On a pass, framework choice works on those chats with no design change, and chat replies move to a zero retention route.
- Model, effort, room and routing become plain content in the prompt file, so a later candidate is a frontmatter change and a run.

**Negative / tradeoffs**:
- On a switch, chat replies cost about three times the lite model's per token price (more with reasoning tokens), less the cached share of the long system prompt; the measured figure goes to the client.
- Replies are slower (median first response about 2.9 s on Vertex against 0.8 s for the lite model on AI Studio), and Vertex was degraded when checked.
- The baseline for panic and manager predates the latest design, and the lite model has no stored times or costs, so the comparison is on outcomes and FAIL lines only.
- Row 35's breadth and row 32's three run check on the new model are deferred; spec 0002's prompt was tuned on the lite model and may read differently.
- Summaries and memory folding keep health data on a route without zero retention.

**Neutral**:
- Spec 0005 is not changed by this spec; its open choice waits on the result.

## Follow-up

- [ ] Row 32's three run check on the chosen model (spec 0002's follow up), when budget allows.
- [ ] Row 35's wider comparison: at least one more family and two open models.
- [ ] The client sets the production cost limit from AC-5's figures.
- [ ] Zero retention for summaries and memory folding: move them to a zero retention route or record why not.
- [ ] If the switch does not happen, decide whether today's chat model stays on a route without zero retention.

## Rationale

Reasoning and options: see [rationale.md](rationale.md).
