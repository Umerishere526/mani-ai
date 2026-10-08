# 0007. Model facing text out of Python, and offers only from the shortlist

**Date**: 2026-10-07
**Status**: In Progress
**Decision record**: [rationale.md](rationale.md) (context, premise notes, options considered, rationale, the inventory of text found in Python)

## Summary

Every sentence the model reads moves out of `backend/mani/` into the seeded prompts, so changing what Mani is told takes a reseed and never a code change. Python sends only facts: ids, names, the person's own data, and short keys whose meaning the prompts explain. The reply schemas carry no descriptions, the router's distinction rules move into each framework's file, and one small migration drops the database check that pinned the six reply shapes. In the same change the closest fit offer goes away: Mani offers a framework only when the router found signs of it (it is on `framework_shortlist`) and Mani judges it fits, so someone whose words match no phrase list is not offered one. Unit and contract tests prove the change, not real model runs, by muhammad's choice.

## Requirements

**User stories**:
- As muhammad, I want every sentence the model reads to live in seeded content, so I can tune what Mani is told with a reseed and no deploy.
- As muhammad, I want Mani to offer only a framework that fits, chosen by Mani from the frameworks the router found signs of, so nobody is offered a nearest fit that does not really fit.
- As a maintainer, I want a test to fail when a sentence creeps back into Python or a key the prompts explain stops being sent, so the two never drift apart silently.

**Acceptance criteria**:
- **AC-1**: The system prompt layers built in `mani/prompts/composer.py` carry only headings and data, and the headings are listed once in a `LAYER_HEADINGS` constant there:
  - `# Framework Index`, then per framework its `## <name> (<id>)` heading (the id in backticks, as today), `Description: <summary>` and its eight lines. No intro paragraph and no closing line.
  - `## User Context`: `nickname: <value>` and `topics: <a>, <b>`, each only when present.
  - `## Memory`: one line per non empty field, keyed by its `Memory` field name (`themes`, `low_times`, `better_times`, `what_helps`, `what_doesnt`, `how_they_talk`), entries joined by `; `.
  - `## Techniques Already Offered`: one `- <framework id>` line per offered framework, and nothing else.
  - `## Conversation Context`: `current_issue: ...`, `summary: ...`, `techniques_tried: ...`, each only when present, and no section when all three are empty.
  - `techniques_tried` is rendered by one helper, `composer.tried_line(techniques) -> str` (`<name> (helpful|not_helpful)` joined by `, `), used by the composer, by `[ctx]` `history:` and by the summary call. The three copies today go.
  - The debug layer is the content of a seeded `debug` prompt row (`content/prompts/debug.md`, keeping its `# Debug` heading), read with `config.prompt("debug")` and added only when `AI_DEBUG_MODE` is on. When debug mode is on and the row is missing, the composer logs a warning and leaves the layer out. `DEBUG_LAYER` no longer exists.
- **AC-2**: Every `[ctx]` line is written through one helper, `_line(key, value)`, whose key must be in a `CTX_KEYS` constant in `mani/chat/context.py`. That includes the stage keys `_stage_lines` builds (`stage`, `next_stage`, and their `_purpose`, `_listen_for`, `_ready_when`, `_boundaries`, `_if_unclear` and `_ask` forms). There is no `stage_note` line, and `_stage_note` no longer exists. `question_focus` is `feelings` or `feeling_then_way_through`. `history:` uses `tried_line`. Every other line stays `key: value` as today, except the lines AC-8 and AC-9 remove or change. The `if <when>: <reply>` joiner inside `_if_unclear` stays, as structure.
- **AC-3**: The messages to the other calls carry only headings and data, and each call's own prompt names its headings and keys:
  - The summary call: `## Existing Summary` (left out when the thread has no summary, or when its fields are all empty) with `current_issue:`, `summary:` and `techniques_tried:` lines, then `## New Messages` with the transcript. The instruction sentence after them is gone, and `summarization.md` says Existing Summary may be absent.
  - The memory fold: `## Known so far` (the memory as JSON), then `## Conversation` (the transcript), both named in `memory_fold.md`.
  - The exercise pick's user message: `current_issue: ...` and one `said: ...` line per message, explained in `exercise_select.md` (spec 0004's row).
  - A tapped button reaches the model as `tapped: <label>`, explained in `response_format.md` `buttons`.

  Speaker tags (`User:`, `Assistant:`, `Person:`, `Mani:`) stay.
- **AC-4**: The JSON schema sent for `Reply`, `Extraction`, `Memory` and the `StartExercise` tool holds no `description` anywhere:
  - not in `model_json_schema()` at any depth, including `$defs`;
  - not in the top level `description` that `convert_to_openai_function` builds from the class docstring.

  Class docstrings become `#` comments above their class, so readers keep them. Each field's meaning lives once in content:
  - every `Reply` field, including the nested `SmartPrompt`, `TechniqueState`, `Crisis`, `Style` and `title` fields, in a `fields` section of `response_format.md`, together with the `LibrarySection` values a button may name;
  - `Extraction` and `ExtractedTechnique` in `summarization.md`, merged with what it already says about `current_issue`;
  - `Memory` in `memory_fold.md`;
  - `exercise_id` in `exercise_select.md`.
- **AC-5**: Every rule that AC-1 to AC-4 take out of Python is said once in `content/prompts/`, and the prompt lines that speak of removed things are edited, not left:
  - The three stage note rules (somatic stage, framework starting, any other stage) go into `response_format.md` `framework_starting` and `stage_lines`, replacing their mention of `stage_note`.
  - What each layer holds goes into a new `layers` section of `response_format.md`.
  - "Say what its questions would help with in fresh words, never its name, its id, or the word framework" goes into `mani_base.md` `offers`.
  - When an offered framework may come back goes only into `response_format.md` `this_thread`.
  - The debug instruction goes into `debug.md`.
  - These lines are edited:
    - `response_format.md` `facts`: drop "a hint ... never a requirement" and `offer`;
    - `response_format.md` `cooldown_passed`: drop "confident" and `closest_fit`;
    - `response_format.md` `question_focus`: the new tokens;
    - `response_format.md` `offer_waiting`: no "as its description says";
    - `response_format.md` `ctx` gains `history`, `since_last` and `current_phase`, which it never named;
    - `mani_base.md` `offers`: no `offer_fit`.

  Changing any of these sentences needs `python scripts/seed.py` and no code change.
- **AC-6**: `SHAPES` no longer exists. `Config` gains `reply_shapes: frozenset[str]` (default empty): the keys of `reply_shapes` in the `mani_base` row's YAML content, trimmed and lowercased, parsed once at cache load with PyYAML (already in `requirements.txt`). Content that does not parse, or has no `reply_shapes` map, logs an error and leaves the set empty. `guards.check` takes a required `shapes` argument, accepts a reported shape when, trimmed and lowercased, it is in `shapes`, and otherwise drops it with today's note. With an empty set every shape is dropped and the turn still runs. `seed.py` refuses a `mani_base.md` with no non empty `reply_shapes` map. Migration `019_reply_shape_not_pinned.sql` drops the `response_styles_shape_known` check, so a shape added in content is stored rather than failing the turn's insert.
- **AC-7**: `DISCRIMINATORS` no longer exists. Each of its six rules lives under `activation.distinctions` in its preferred framework's file, with `name`, `priority`, `phrases`, `over` and `standalone`, and the same phrases, `over` lists and `standalone` values as today. `Registry.distinctions` builds a `Rule` per entry (`prefer` is the owning framework's id), ordered by `priority`. `router.shortlist(messages, activations, rules)` and `router.urgent(messages, rules)` take the rules as an argument, and for every case kept in `tests/unit/test_router.py` the shortlist ranks as today. Seeding is refused in two places:
  - `parse_framework`, one file at a time, refuses: a key other than the five; an empty `phrases` list, or one holding anything but non empty strings; a `priority` that is not a positive whole number; `standalone` that is not a boolean.
  - `check_distinctions(frameworks)`, run once after every file is parsed and before anything is written, refuses: a `priority` used twice; an `over` naming an unknown id or its own; more than one rule with an empty `over`.

  On a portal edit that skips the seed, `Registry` logs an error and drops the offending rule, then sorts the rest stably, so the turn still runs.
- **AC-8**: `closest_fit_due`, `closest_fit_ok`, `cooldown_for`, `CLOSEST_FIT_AFTER`, `COOLDOWN_AFTER_DECLINE`, the `closest_fit:` line and the `offer_fit` field no longer exist, and no prompt mentions a closest fit. A thread whose shortlist is empty gets no offer guidance at the person's fourth message or at any later one.
- **AC-9**: `framework_shortlist:` lists every framework that scored or that a distinction promoted, as ids only, in ranked order, minus `ruled_out`, with no cut. When the router did not run or found nothing, the line is absent. Removed: the `offer:` line, `router.is_confident`, `CONFIDENT_SCORE`, `CONFIDENT_MARGIN`, `MIN_CORROBORATION`, `DEFAULT_LIMIT` and the `limit` parameter, `Signal.spread` and `Signal.time_critical`, and the spread `_score_one` returns. `Signal` keeps `framework_id`, `score`, `matched` and `promoted_by`. A message older than the four `RECENCY_WEIGHTS` keeps the last weight (0.15) rather than dropping out, so a sign stays on the shortlist while its message is in the history window. `mani_base.md` and `response_format.md` tell the model:
  - Offer only a set named on `framework_shortlist`, once you have learned what its Starts when line names, and only when `cooldown_passed: yes`.
  - The list is ranked by how much the router saw, and an absent list means offer nothing.
  - When they ask for a kind of help, ask about it and follow their answer rather than offering.
  - A set already offered in this conversation that they ask for again is a yes.

  The rule is told, not enforced. No guard drops an offer for being off the shortlist (decisions in force).
- **AC-10**: When the person's last two messages carry a phrase from the rule with no `over` (dbt_stop's), the router runs before `ROUTER_MIN_EXCHANGES`, `dbt_stop` is first on `framework_shortlist`, and `cooldown_passed` is `yes` from their first message, exactly as today.
- **AC-11**: On a turn where no framework was running and the reply carries a button with `technique` set, an info log line names the thread id, the offered id, `on_shortlist: yes|no`, the shortlist ids and `cooldown_passed: yes|no`. It carries ids and flags only, never message text. The existing `heading_toward` log line stays as it is.
- **AC-12**: Two contract tests hold the line:
  - For each of `Reply`, `Extraction`, `Memory` and `StartExercise`, neither `model_json_schema()` nor `convert_to_openai_function(...)` holds a `description` at any depth. `tests/unit/test_schema.py` stops reading `.description`.
  - Every key in `CTX_KEYS` is named in `response_format.md` `ctx`, and every heading in `LAYER_HEADINGS` in `layers`. Every key under `ctx` and every heading under `layers` is in those constants, except entries the test names as not keys (`about`, `facts`, `stage_lines`).

  In `test_prompts_name_what_exists.REMOVED`, `closest_fit`, `offer_fit` and `stage_note` are added, and `stage_ready_when`, `stage_ask` and `next_stage_ask` are taken out, because somatic stages still send them.
- **AC-13**: The whole `pytest` passes with pristine output and the integration count checked (not skipped), the migration is applied and the local database reseeded, and `backend/PORT-STATUS.md` is updated in the same change:
  - "Decisions in force": the "Offers follow Mani's confidence" line is edited in place to the shortlist rule, and the homes of the reply shapes and the distinction rules and the end of the closest fit are recorded.
  - The lines describing a nearest fit by the fourth message go.

  `docs/database-schema-reference.md` stops citing `SHAPES` and the shape check. A tokenizer count of the system prompt before and after (no model call) is recorded in PORT-STATUS. No real model run is made (muhammad, 2026-10-07).

**Not in this spec**:
- The exercise pick instruction and the translation prompt. Spec 0004 AC-6 moves both into their own rows; this spec only moves the exercise pick's user message labels.
- `CLARIFICATION_QUESTIONS` and `AFTER_FRAMEWORK_QUESTIONS`. They reach `[ctx]`, but code matches them in past replies, so they move with their matching code in feature 9.
- The greeting, the style question, openers, button labels, the crisis reply, and every timing number (router weights, cooldowns, `ROUTER_MIN_EXCHANGES`, `PROMOTED_FLOOR`): feature 9.
- What the `crisis` field's meaning says. It moves to `response_format.md` word for word here, and feature 10 rewrites it.

## Decision

**Chosen option**: Python sends facts and the prompts hold the words. Combined with that: the router's shortlist is the set Mani may offer from, and there is no closest fit.

Code emits keys, headings and values only, from named constants that a test ties to the prompts. Every instruction moves into the authored prompt that already explains that input. The reply schemas lose their descriptions, the reply shapes come from `mani_base.md`, and the distinction rules become framework data with a priority. Offers are told to come only from `framework_shortlist`, and the closest fit path is deleted.

## Feature design

**Data model sketch**:
- Migration `019_reply_shape_not_pinned.sql`: `alter table public.thread_response_styles drop constraint response_styles_shape_known;`. The voice check and every other constraint stay. `shape` stays `text not null`, and the guard keeps it to the seeded set.
- `admin.frameworks.activation` (jsonb, already checked to be an object) gains `distinctions`: an array of `{name: text, priority: positive int, phrases: non empty text[], over: framework id[] (may be empty), standalone: bool default false}`. `seed.ACTIVATION_KEYS` gains `distinctions`. The rules sit on their preferred framework:

  | Framework file | name | priority | over | standalone |
  |---|---|---|---|---|
  | `dbt_stop.md` | an action is imminent | 1 | (none: the urgency rule) | false |
  | `act_choice_point.md` | the outcome cannot be controlled | 2 | thought_reframe, abcde, structured_problem_solving | true |
  | `behavioral_activation.md` | knows what to do but cannot begin | 3 | structured_problem_solving | false |
  | `structured_problem_solving.md` | does not know what to do | 4 | behavioral_activation | false |
  | `abcde.md` | a specific event triggered the belief | 5 | thought_reframe | false |
  | `abcde.md` | asks to understand why it affected them | 6 | thought_reframe | true |

- `admin.prompts` gains one row, `debug` (id `10000000-0000-0000-0000-000000000014`, after spec 0004's `...012` and `...013`). It is a layer row that only debug mode reads, so it stays out of spec 0004's `CALL_PROMPTS` and out of the expected list that warns at load. Its one warning is the composer's (AC-1).

**State transitions**: unchanged. `offering` → accepted → each id in `phases` → `closing` → `somatic_checkin` → `somatic_practice` → retired. A decline still starts the clear cooldown (`CLEAR_COOLDOWN_AFTER_DECLINE`).

**Model facing interface** (no HTTP change; this is the contract between code and prompts):

| Where | Before | After |
|---|---|---|
| `[ctx]` `stage_note` | one of three sentences, uncached, every framework turn | removed; rules in `response_format.md` |
| `[ctx]` `question_focus` | `feelings` or `feeling, then the way through` | `feelings` or `feeling_then_way_through` |
| `[ctx]` `framework_shortlist` | top 3 with scores, last four messages | every candidate, ids only, ranked, the whole history window |
| `[ctx]` `offer` | router's confident pick | removed |
| `[ctx]` `closest_fit` | `due` or `ok` | removed |
| `[ctx]` `history` | `name (not helpful)` | `name (not_helpful)` |
| A tapped button | `User tapped the button: "<label>".` | `tapped: <label>` |
| Reply schema | descriptions everywhere, `offer_fit` | names and types only, no `offer_fit` |
| System prompt layers | headings plus instruction sentences | headings plus keyed data |
| Summary, memory fold and exercise pick user messages | labels and an instruction sentence | headings and keys |

**Value sourcing**:

| Action | Value | Source |
|---|---|---|
| `guards.check` shape check | the allowed shapes | `Config.reply_shapes`, from the `mani_base` row's `reply_shapes` keys at cache load, passed by the orchestrator as `shapes` |
| Storing a shape | the allowed values | the guard only, once migration 019 drops the check |
| `router.shortlist`, `router.urgent` | the ordered rules | `config.registry.distinctions` |
| `router.urgent` | the urgency phrases | the one rule with an empty `over` |
| Scoring an older message | its weight | `RECENCY_WEIGHTS[-1]` for every distance past the fourth |
| `[ctx]` `framework_shortlist` | ids | `router.shortlist(...)` minus `ruled_out` |
| `[ctx]` keys | the allowed names | `context.CTX_KEYS` |
| Layer headings | the allowed names | `composer.LAYER_HEADINGS` |
| `[ctx]` `question_focus` | token | `resolve_style(ctx) == "direct"` |
| `## User Context` | nickname, topics | `public.profiles` via `ctx.profile` |
| `## Memory` | six lists | `admin.user_memory` via `ctx.memory` |
| `## Conversation Context`, `[ctx]` `history`, `## Existing Summary` | issue, summary, techniques tried | `public.thread_summaries`, techniques via `composer.tried_line` |
| `## Techniques Already Offered` | framework ids | `ctx.techniques_offered` (the `offered` argument) |
| Exercise pick user message | issue, recent lines | `current_issue` and `said` arguments of `client.choose_exercise` |
| Debug layer | text | `config.prompt("debug").content` |
| Every moved sentence | text | `admin.prompts.content` of `mani_base`, `response_format`, `summarization`, `memory_fold`, `exercise_select`, `debug` |
| Offer log | offered id, shortlist ids, cooldown | the kept buttons' `technique`, the turn's `shortlist`, `context.cooldown_passed` |

**Key invariants**:
- No sentence the model reads is written in `backend/mani/`. What may stay: `[ctx]` keys from `CTX_KEYS`, headings from `LAYER_HEADINGS` and the message headings the prompts name, the `Description:` label, the `if <when>:` joiner, speaker tags, values from data, and the two client question lists that feature 9 owns.
- `CTX_KEYS` and `LAYER_HEADINGS` match what `response_format.md` explains, in both directions (AC-12).
- A framework in `ruled_out` is never on `framework_shortlist`.
- At most one distinction has an empty `over`, and priorities are unique.
- The offer rule is told in the prompt, never enforced after the call.

**Security model**: no change in who may read or write what. The prompt cache still reads through `pool.as_admin()`. Logs carry ids and flags only, never message text, because conversations are special category health data. One thing does widen: an admin editing `mani_base`, `response_format` or a framework in the portal now changes the stage rules, the field meanings, the shape list and the distinction rules too. The portal skips the seed's checks, which is why a broken `reply_shapes` empties the set and a broken rule is dropped, rather than failing turns (AC-6, AC-7).

**Configuration required**: none new. `AI_DEBUG_MODE` already exists.

**Critical test scenarios**:
- The composer, with a fake profile, memory, empty and full summaries and an offered list, renders only headings from `LAYER_HEADINGS` and keyed lines, and the debug layer comes from the row. Verifies **AC-1**.
- `context.build` on a framework turn has no `stage_note` line, Direct gives `question_focus: feeling_then_way_through`, and `_line` refuses a key outside `CTX_KEYS`. Verifies **AC-2**.
- The summary user message for a thread with no summary has no `## Existing Summary`. A tapped button reaches the model as `tapped: <label>`. Verifies **AC-3**.
- The schema walk finds no `description` in the four schemas, in either form. Verifies **AC-4**, **AC-12**.
- `CTX_KEYS` and `LAYER_HEADINGS` match `response_format.md` in both directions. Verifies **AC-5**, **AC-12**.
- `guards.check` keeps `Mirror and ask` when `shapes` holds it, and drops every shape for an empty set. The seed refuses a `mani_base.md` with no `reply_shapes`. Against the database, a seventh shape inserts after migration 019. Verifies **AC-6**.
- `check_distinctions` refuses a duplicate priority, an unknown `over` and two urgency rules. `Registry` drops a bad rule with a logged error. The kept `test_router.py` rankings hold from the seeded rules. Verifies **AC-7**.
- A sign said in the person's first message is still on the shortlist at their sixth. Verifies **AC-9**.
- Integration: a thread whose phrases match nothing reaches the person's fifth message with no `framework_shortlist`, no `offer:` and no `closest_fit` line. Verifies **AC-8**, **AC-9**.
- Integration: five frameworks score, all five ids appear without scores, and a ruled out one does not. Verifies **AC-9**.
- Integration: "I am about to send it" as the first message puts `dbt_stop` first with `cooldown_passed: yes`. Verifies **AC-10**.
- An offer of a set off the shortlist logs `on_shortlist: no` with no message text (asserted with `caplog`). Verifies **AC-11**.

## Build plan

Tracer Bullet: the first slice threads one moved rule through every layer (content file, seed, cache, code and contract test), so the path is proven before the rest moves onto it. Each slice leaves the whole `pytest` green. Slices 1 to 5 (the text) and 6 and 7 (the routing) go in separate PRs, so either half can be reverted on its own.

0. Precondition: spec 0004 AC-6 is built (the `exercise_select` row exists, and `CALL_PROMPTS` replaces `EXPECTED_PROMPTS`), and the uncommitted 0005 and 0006 work is committed. If 0004 is not built, build it first with `/develop thinking level required`. Satisfies **AC-3**, **AC-4**.
1. Add `CTX_KEYS` and `_line`, route every `[ctx]` line through it, move the three stage note rules into `response_format.md`, delete `_stage_note`, switch `question_focus` to tokens, name `history`, `since_last` and `current_phase` in the prompt, write the ctx half of contract test (b), and fix `REMOVED`. Rewrite the `stage_note` assertions in `test_chat_context.py` (around lines 313, 352, 373 and 645). Reseed. Satisfies **AC-2**, **AC-5**, **AC-12**.
2. Add `LAYER_HEADINGS` and `tried_line`, rewrite the composer layers as headings and keyed data, add the `layers` section, move the offer wording line into `mani_base.md` `offers`, merge the "may be offered again" rule into `this_thread`, add `debug.md` and its row, use `tried_line` in `context.py` and `summarize.py`, and write the layer half of contract test (b). Rewrite `test_composer.py` (around lines 147 to 198). Satisfies **AC-1**, **AC-5**, **AC-12**.
3. Rewrite the summary, memory fold and exercise pick user messages and the tapped button message, and name their headings and keys in `summarization.md`, `memory_fold.md`, `exercise_select.md` and `response_format.md` `buttons`. Satisfies **AC-3**.
4. Strip every description and class docstring from `schema.py` and `tools.py` (docstrings become comments). Add the `fields` section, with the library sections, to `response_format.md`, move the `Extraction` and `Memory` meanings into their prompts, move `exercise_id` into `exercise_select.md`, edit `offer_waiting`, write contract test (a), and stop `test_schema.py` reading `.description`. Satisfies **AC-4**, **AC-5**, **AC-12**.
5. Add migration 019, `Config.reply_shapes` and the `shapes` argument to `guards.check` (updating every `test_guards.py` caller), delete `SHAPES`, make `seed.py` refuse a missing `reply_shapes`, and point `test_negative_set.py` and `test_queries.py` at the content. Satisfies **AC-6**.
6. Add `distinctions` to the six framework files and to `ACTIVATION_KEYS`, with the per file checks and `check_distinctions`. Add `Registry.distinctions` with its soft failure, pass `rules` into `router.shortlist` and `router.urgent`, delete `DISCRIMINATORS`, and run the kept `test_router.py` cases from the seeded rules. Satisfies **AC-7**, **AC-10**.
7. Delete the closest fit path (`context.py`, the orchestrator's `candidate` branch and argument, `offer_fit`). Delete `is_confident` and its constants, the `offer:` line, `DEFAULT_LIMIT` and `limit`, and `Signal.spread` and `time_critical`. Add the recency tail, render the shortlist as ids only, and write the offer rule into `mani_base.md` and `response_format.md` (`facts`, `cooldown_passed`). Add the offer log line, and add `closest_fit` and `offer_fit` to `REMOVED`. Rewrite or delete the tests that read what goes:
   - `test_router.py`: `is_confident`, `CLOSEST_FIT_AFTER`, `limit=2`, `.spread`, about 15 tests;
   - `test_chat_context.py`: the closest fit and `candidate` cases, around lines 99, 259 to 342, 545 and 564 to 587;
   - `test_turn.py`: `_offer(fit)` and every `offer_fit=`, which pass silently because the schema ignores extra keys, so remove them on purpose; also around lines 288, 308 and 1040 to 1050.

   The `steering` scenarios in `eval_conversations.yaml` expect an offer by the fourth message. Leave them, and note in their comment that an offer now waits for the shortlist. Satisfies **AC-8**, **AC-9**, **AC-10**, **AC-11**, **AC-12**.
8. Take the tokenizer count of the system prompt before and after. Apply the migration, reseed, and run the whole `pytest` against the local database, checking the integration count. Update `PORT-STATUS.md` and `docs/database-schema-reference.md`. Satisfies **AC-13**.

## Consequences

**Positive**:
- Every sentence the model reads can be tuned with a reseed or a portal edit, and each rule has one home, so the prompts and the code stop repeating each other.
- Keys and headings come from two constants that a test ties to the prompts. A rename fails a test instead of leaving the model reading something that is not there.
- The router loses its confidence machinery and the closest fit path. There is less code, and one offer rule instead of a router rule and a model rule that could disagree.
- Nobody is offered a framework that only nearly fits.

**Negative / tradeoffs**:
- Fewer offers. With no closest fit and the shortlist as the gate, the phrase lists' reach is the ceiling on every offer. Someone who never uses a listed phrase (paraphrase, misspelling, indirect talk) is never offered a framework, however clearly one fits. The offer log shows offers off the list, but it cannot show the offers that never came.
- The gate loosens and tightens at once. Any score above zero now puts a set on the list, so a single passing phrase makes it offerable, and the model's own judgement of the Starts when line is the remaining guard. The model also sees no strength, only order.
- The change is unmeasured. A routing change, and the removal of every schema description, ship on unit and contract tests alone. Whether the model keeps to a rule it is only told, and fills fields as well without descriptions, is unknown until real runs (feature 11).
- The stage rules move from `[ctx]` into the cached prefix, but the prefix grows on every turn, including the many that never run a framework. Whether a turn gets cheaper depends on the provider caching it. The tokenizer count shows the size, not the bill.
- A portal edit can now change more behaviour, and the portal skips the seed's checks. The soft failures keep turns running, but a bad edit is only visible in the logs.

**Neutral**:
- Migration 019 drops a check, so stored shapes are no longer guarded by the database. Rows written before a rename keep the old name.
- The somatic stage rule moves word for word. Feature 7 owns its content.
- Spec 0004 must land first.

## Migration plan

**Strategy**: one migration that only drops a check, then reseed, then deploy.
**Phases**:
1. Apply migration 019 on hosted. Old code is unaffected: it only ever writes the six shapes.
2. Run `python scripts/seed.py` against hosted from the new commit. For those minutes, old code runs against the new prompts. It still sends `closest_fit`, `offer:`, `stage_note` and an `offer_fit` field, which the prompts no longer explain. The old router ignores the unknown `distinctions` key, and the old guard does not read `reply_shapes`.
3. Deploy the code.

**Rollback**: revert the commit, check out the previous `content/`, and reseed. The dropped check can stay dropped, since the guard still keeps shapes to the seeded set. Restoring it is a new migration, valid only while no seventh shape has been stored.
**Risks**: deploying before reseeding gives the model no field descriptions and no stage rules until the seed runs. Keep the order.

## Follow-up

- [ ] `PATCH /admin/prompts/{id}` and the framework admin path skip the seed's checks. They should refuse a `mani_base` without `reply_shapes` and a framework whose `distinctions` break AC-7, instead of relying on the soft failures.
- [ ] Measure offers per conversation, offers off the shortlist and offers with `cooldown_passed: no`, before and after, with real runs under feature 11. Until then this change's effect on offers is unknown.
- [ ] Grow the phrase lists from real conversations where an offer fitted but never came.
- [ ] `context.py` keeps `_VAGUE_REPLIES`, `_HEARD_PHRASES` and `_CORRECTION_PHRASES`, phrase lists about the person's message that no model reads. Consider them with feature 9.
- [x] The scope row for feature 8 should say it also removes the closest fit and makes the shortlist the offer gate.

## Rationale

Reasoning, options and the inventory: see [rationale.md](rationale.md).
