# 0008. Reply text and conversation numbers in seeded content

**Date**: 2026-10-08
**Status**: In Progress
**Decision record**: [rationale.md](rationale.md) (context, premise notes, options considered, rationale, the inventory of what stays in Python and why)

## Summary

The lines Mani sends to people without the model (the greeting, the style question and its buttons, each style's opener, the two clarification lines, the three after framework questions) move into a new seeded row, `replies`. The numbers that shape a conversation (offer timing, cooldowns, router weights, history and memory limits) move into another, `tuning`. Both rows are checked on every write (seed, admin portal, cache load), so a broken edit is refused rather than taking turns down. The files in `content/` stay the source of truth, as for every prompt row: a portal edit lasts until the next seed. In a second commit, four behaviours change: the phrase lists that labelled a person's message as vague, a correction or a request to be heard go, with their rules; the model, not the code, tracks which clarification and after framework lines it has asked; a leftover offer button label goes; and the memory fold is told its entry limit as data. Unit and contract tests prove it, with no real model run, by muhammad's choice.

## Requirements

**User stories**:
- As muhammad, I want every line Mani sends without the model, and every number that shapes a conversation, in seeded content, so I can change one with a reseed and no deploy, and try a change in the portal first.
- As muhammad, I want an edit that would break a turn refused when it is written, so a typo in the portal never takes the chat down.
- As a maintainer, I want a test to fail when a moved constant comes back into Python, so the content stays the one home.

**Acceptance criteria**:

Commit 1, pure moves. Nothing any model sees changes, and every turn, greeting and opener is exactly what it is today for the seeded values. The only new behaviours are the write refusals (AC-4) and the turn loading its config before its context (AC-3).

- **AC-1**: `content/prompts/replies.md` (id `10000000-0000-0000-0000-000000000015`, name `replies`, no `model_id`) holds, in YAML, today's text word for word:
  - `greeting`: `new` (`Hi {name}. It's MANI.`), `returning` (`Hi {name}, good to see you again.`), `default_name` (`there`);
  - `style_question`;
  - `style_labels`: `direct`, `supportive`, `reflective` to `Direct`, `Supportive`, `Reflective`;
  - `openers`: the three, keyed the same way;
  - `clarification_lines`: `Do I have this right?`, `What would you like us to focus on today?`;
  - `after_framework_questions`: the three, in today's order.

  `parse_replies(content) -> Replies` in `mani/prompts/replies.py` (pydantic, `extra="forbid"`, strict string types) refuses:
  - a body that is not a YAML map;
  - an unknown or missing key, a string that is empty or only whitespace, an empty list;
  - a `greeting` template whose fields are anything but `{name}`: positional `{}`, a conversion (`{name!r}`), a format spec (`{name:x}`) and an unbalanced `{` or `}` are all refused (the `ValueError` that `string.Formatter().parse` raises is caught and reported);
  - `style_labels` or `openers` whose keys are not exactly the `SupportStyle` values, and two `style_labels` equal when compared case insensitively (the style tap matches by label);
  - in `clarification_lines` and `after_framework_questions`, a line holding a newline, ` | `, `[` or `]`, because commit 2 sends them inside one `[ctx]` line.
- **AC-2**: `content/prompts/tuning.md` (id `10000000-0000-0000-0000-000000000016`, name `tuning`, no `model_id`) holds today's numbers, keyed by the old constant names in lowercase, each with its allowed range:

  | Group | Key | Today | Allowed |
  |---|---|---|---|
  | `offers` | `clear_offer_after` | 2 | 1 to 20 |
  | `offers` | `clear_cooldown_after_decline` | 4 | 0 to 200 |
  | `offers` | `cooldown_after_complete` | 45 | 0 to 200 |
  | `offers` | `default_style` | `supportive` | a `SupportStyle` value |
  | `router` | `router_min_exchanges` | 2 | 1 to 20 |
  | `router` | `recency_weights` | [1.0, 0.6, 0.3, 0.15] | non empty, each in (0, 1], never increasing |
  | `router` | `strong_weight`, `signal_weight`, `promoted_floor` | 2.0, 1.0, 1.5 | above 0, up to 10 |
  | `windows` | `context_window` | 20 | 4 to 100 |
  | `windows` | `style_window` | 7 | 1 to 50 |
  | `windows` | `recent_openers_words`, `recent_openers_window` | 2, 3 | 1 to 10 |
  | `windows` | `title_after_messages` | 3 | 1 to 21 |
  | `windows` | `ending_turn_cap` | 12 | 2 to 50 |
  | `memory` | `max_entries` | 6 | 1 to 20 |
  | `memory` | `max_entry_chars` | 160 | 1 to 500 |
  | `memory` | `idle_after_hours` | 24 | 1 to 720 |

  `parse_tuning(content) -> Tuning` in `mani/prompts/tuning.py` (pydantic, `extra="forbid"`, `StrictInt` for counts and `StrictFloat` or `StrictInt` for weights, so `true` and `"2"` are refused) refuses a body that is not a YAML map, an unknown or missing key, and any value outside its range.
- **AC-3**: `Config` gains `replies: Replies` and `tuning: Tuning`, declared before `reply_shapes` (which keeps its default), parsed once at cache load. `replies` and `tuning` join `REQUIRED_PROMPTS`. At load, `_read` wraps any parse failure of either row in `ServiceError(CONFIG_ERROR)`, so a missing or broken row fails the turn exactly as a missing `mani_base` does, and is never swallowed as a transient failure that keeps the old snapshot. There is no default in code. `mani_base`'s `reply_shapes` keeps spec 0007's soft handling at load. Neither row is ever put into a model call. The turn calls `cache.load()` before `threads.load_turn_context` (after the duplicate message return, as today), so a broken row is reported before anything else about the turn.
- **AC-4**: One check, `content_problem(name, content) -> str | None` in `mani/prompts/checks.py`, never raises and covers `mani_base` (its `reply_shapes`), `replies` and `tuning`; any other name returns None. `parse_reply_shapes` moves from `cache.py` into `checks.py`, and `cache.py`, `scripts/seed.py`, `test_call_prompts.py`, `test_negative_set.py` and `test_queries.py` import it from there, so `config_tables` importing `checks` makes no cycle. The problem text names the key and the rule, never the value written. It is used:
  - by `scripts/seed.py`, which refuses to seed when it returns a problem and when either new file is missing;
  - by `mani/db/config_tables.py` on the row a write returned, inside the write's transaction (beside `_check_callable`), so `POST /admin/prompts` and `PATCH /admin/prompts/{id}` answer 422 `invalid_request` and store nothing, not even the version snapshot.

  The same write check refuses, for every `REQUIRED_PROMPTS` row (`mani_base`, `response_format`, `replies`, `tuning`), `is_active: false` and a change of `name`.

  The files in `content/` are the source of truth: the seed overwrites these rows as it overwrites every prompt row, so a portal edit lasts until the next seed.
- **AC-5**: The greeting, the style buttons and the openers come from `Config.replies`:
  - `greeting(replies, nickname, returning)` returns the template for `new` or `returning` with `{name}` filled (`default_name` when there is no nickname), then a space, then `style_question`;
  - the greeting's `prompt_options` are `[{label, style}]` from `style_labels`, in `SupportStyle` order;
  - `_open_in_style` takes `replies` from the turn's config and replies with `openers[style]`.

  `DEFAULT_NAME`, `STYLE_QUESTION`, `STYLE_OPTIONS` and `OPENERS` no longer exist, and `start_thread` loads the config.
- **AC-6**: Every number in AC-2 is read from `Config.tuning` and its constant no longer exists:
  - Router: `router.shortlist(messages, activations, rules, weights)` takes `tuning.router`, and `_score_one` and `_promote` read the weights and floor from it. The orchestrator reads `router_min_exchanges`.
  - Context: `context.cooldown_passed(ctx, tuning, *, urgent=False)`, `context.clear_cooldown_for(outcome, tuning)` and `context.resolve_style(ctx, default_style)`. `context.build` takes `replies` and `tuning` as keyword arguments and reads the openers window and word count from `tuning`.
  - History: `messages_db.recent_for_context` takes `limit` with no default. The turn passes `context_window`, and the summary refreshes every `context_window` new messages (`SUMMARY_THRESHOLD` goes). `summarize.reconcile_due`, the cron backstop behind `/internal/cron/fold-summaries`, loads the config and passes `context_window` as its threshold, instead of its default of 20. `routers/threads.py` `_history` passes its own `THREAD_TAIL = 20`, an API page size and not tuning.
  - Styles: `threads.load_turn_context(conn, thread_id, user_id, style_window)` sends the window as a query parameter, not into the SQL text.
  - Memory: `memory.bounded(memory, limits)` takes `tuning.memory`, passed by `fold_one`, which already loads the config. `IDLE_AFTER` goes, and `scripts/fold_idle_threads.py` computes `idle_before` from `idle_after_hours` after it opens the pool and loads the config. `fold_finished` keeps taking `idle_before` from its caller.
  - Title: generated from `title_after_messages`.
  - Ending: the cap that retires a framework stuck in its ending (spec 0009, AC-10) reads `ending_turn_cap`.

  `OPENING_MESSAGES`, `MAX_FOLDS_PER_RUN`, `MAX_TITLE_LENGTH` and every infrastructure number stay in code (see *Not in this spec*).
- **AC-7**: `AFTER_FRAMEWORK_QUESTIONS` and `CLARIFICATION_QUESTIONS` no longer exist. The code that reads them reads `Config.replies` instead, with today's matching. Outside a turn:
  - `scripts/eval_replies.py`, `tests/evals/validators.py` and `tests/evals/test_style_findings.py` read the after framework questions from `replies.md` through `seed.parse_prompt` and `parse_replies`;
  - `eval_replies._open_chat` taps the label from `replies.style_labels`, not `style.value.capitalize()`;
  - `eval_replies._framework_after` passes `style_window` to `load_turn_context`;
  - `baseline.content_hashes` adds `replies` and `tuning`, so a saved baseline shows when either changed;
  - `test_prompt_lines_the_code_reads.py` reads the lines from `replies.md`.
- **AC-8**: `tests/unit/test_prompts_name_what_exists.py` gains `REMOVED_NAMES`, and a test fails when any module under `mani/` or `scripts/` binds one at module level. Commit 1 lists every constant AC-5, AC-6 and AC-7 delete, including `SUMMARY_THRESHOLD`, `IDLE_AFTER` and `ENDING_TURN_CAP`.

Commit 2, behaviour changes.

- **AC-9**: `context.classify_reply`, `_VAGUE_REPLIES`, `_HEARD_PHRASES`, `_CORRECTION_PHRASES` and the `their_last` argument and `[ctx]` line no longer exist, and `their_last` leaves `CTX_KEYS`. In `response_format.md`, the `their_last` entry and its three rules (vague, correction, heard) are deleted. Reasoning step 1 loses "Deal with their_last first if present." and keeps the rest. In `mani_base.md`, the mirror and hold shape reads "Only after the questions ended, or when they ask only to be listened to." `normalize` stays, because the router and the safety screen use it.
- **AC-10**: `clarification_used` no longer exists. While no framework is running, `[ctx]` carries `clarification_lines: <line> | <line>`, the lines from `Config.replies.clarification_lines` joined by ` | `. In `response_format.md`, `clarification_available` becomes `clarification_lines`: when several distinct things have come up and you cannot tell which matters most, you may ask one of these lines word for word, and only if none of your earlier replies here already asked one; then follow their answer. No line is quoted in the prompt. `test_prompt_lines_the_code_reads.py` is deleted.
- **AC-11**: The "already asked" matching in `_after_framework_question` goes. While the reply that offered Chat More is in the history window and there is no safety concern, `[ctx]` carries `after_framework_questions: <q1> | <q2> | <q3>` from `Config.replies`, in order. Finding that reply by its Chat More button stays (feature 7 owns the ending). In `response_format.md`, `after_framework_question` becomes `after_framework_questions`: they kept chatting after the questions ended, on the same issue; reflect what they said, then ask the first of these you have not yet asked, word for word, one per reply; once all are asked, carry on as usual.
- **AC-12**: `TELL_ME_ABOUT_THIS_LABEL` and `EXPLAIN_LABELS` no longer exist. `guards._is_offer_button` is `technique or decline`, and the guard comments say Keep chatting, not Tell me about this, answers an offer. The tests that assert Tell me about this is dropped with the offer (`test_guards.py` around lines 86 to 100, `test_turn.py` around lines 1499, 1528, 1556 and 1586) are rewritten to the new rule.
- **AC-13**: The memory fold user message starts with a `max_entries: <n>` line from `tuning.memory.max_entries`, and `memory_fold.md` names that key instead of saying "six". The `test_memory.py` cases that assert the fold message are updated.
- **AC-14**: `REMOVED` gains `their_last`, `clarification_available` and `after_framework_question`, and its matching becomes whole word (as `_named` in `test_prompt_contract.py`), so `after_framework_question` does not match `after_framework_questions`. `REMOVED_NAMES` gains `classify_reply`, `clarification_used`, `_VAGUE_REPLIES`, `_HEARD_PHRASES`, `_CORRECTION_PHRASES`, `TELL_ME_ABOUT_THIS_LABEL` and `EXPLAIN_LABELS`. Spec 0007's contract test passes with `clarification_lines` and `after_framework_questions` in `CTX_KEYS` and in `response_format.md` `ctx`.
- **AC-15**: After each commit, the whole `pytest` passes with pristine output and the integration count checked (not skipped), and the local database is reseeded. `backend/PORT-STATUS.md` is updated in the same change:
  - commit 1 adds a "Decisions in force" line: user facing lines live in the `replies` row and conversation numbers in the `tuning` row, both required, checked on every write, with the files as the source of truth;
  - commit 2 edits in place the "base prompt is short rules" line (the only lines the model says word for word are the clarification lines and the after framework questions, sent in `[ctx]` from `replies`, and the model tracks which it has asked), and the lines that name `their_last` (around line 64) and `clarification_used` and `test_prompt_lines_the_code_reads.py` (around line 145).

  `docs/database-schema-reference.md` lists the two rows. No real model run is made (muhammad, 2026-10-08).

**Not in this spec**:
- The body ending labels `CHAT_MORE_LABEL` and `GO_TO_LIBRARY_LABEL`. Spec 0009 (feature 7, built before this spec) kept them in code and deleted the rest of the ending's lists.
- Crisis: `CRISIS_REPLY`, `RESOURCES`, `PROTOCOLS`, `CLARIFICATION`, `_CRISIS`, `_CONCERN` and `RECENT_CRISIS_DAYS`. Feature 10.
- The `user_message` strings on `ServiceError`. The frontends own error wording in their dictionaries, keyed by the error category.
- Infrastructure numbers: pool sizes, timeouts, cache TTLs, token budgets, `MAX_AUDIO_BYTES`, page sizes, batch sizes, `MAX_FOLDS_PER_RUN`, `MAX_TITLE_LENGTH`, and model settings, which already live in each call's prompt row.
- `OPENING_MESSAGES`: it counts what the code itself writes (greeting, style, opener), so it is not a tuning number.
- Any language but English.

## Decision

**Chosen option**: two seeded YAML rows, `replies` and `tuning`, read into a typed `Config` at cache load and checked on every write, with the files as the source of truth. A second commit hands three tracking jobs from code to the model.

Python keeps the logic and the closed sets it owns (`SupportStyle`, `CTX_KEYS`), and reads every line it sends and every conversation number from the config, just as spec 0007 made it read every sentence the model sees from the prompts.

## Feature design

**Data model sketch** (no migration; two rows in `admin.prompts`, whose YAML is the schema; ranges in AC-2):

```yaml
# replies.md (body)
greeting:
  new: "Hi {name}. It's MANI."
  returning: "Hi {name}, good to see you again."
  default_name: there
style_question: How would you like me to speak with you today?
style_labels: {direct: Direct, supportive: Supportive, reflective: Reflective}
openers:
  direct: How can I help you today?
  supportive: How can I support you today?
  reflective: What's on your mind today?
clarification_lines:
  - Do I have this right?
  - What would you like us to focus on today?
after_framework_questions:
  - What feels most important about this now?
  - What do you think you need to do differently from here?
  - How could you take one small step toward that?

# tuning.md (body)
offers: {clear_offer_after: 2, clear_cooldown_after_decline: 4, cooldown_after_complete: 45, default_style: supportive}
router: {router_min_exchanges: 2, recency_weights: [1.0, 0.6, 0.3, 0.15], strong_weight: 2.0, signal_weight: 1.0, promoted_floor: 1.5}
windows: {context_window: 20, style_window: 7, recent_openers_words: 2, recent_openers_window: 3, title_after_messages: 3}
memory: {max_entries: 6, max_entry_chars: 160, idle_after_hours: 24}
```

Both files carry the usual front matter (`id`, `name`, `type`, `description`) and no `provider`, `model_id` or `model_parameters`. They join `REQUIRED_PROMPTS`, which also puts them in `EXPECTED_PROMPTS`. They stay out of `CALL_PROMPTS`, because no model call is made from them.

**State transitions**: unchanged. A change to `tuning` applies from the next turn after the cache reloads, including in conversations already open. A cooldown counted under the old number is checked against the new one.

**Interface changes** (no HTTP change; the admin routes keep their shapes and gain refusals):

| Where | Before | After |
|---|---|---|
| `POST`/`PATCH /admin/prompts` | `mani_base`, `replies`, `tuning` content unchecked; `response_format` and `mani_base` could be deactivated or renamed | content checked by `content_problem`; the four required rows cannot be deactivated or renamed; refusal is 422 `invalid_request` |
| `[ctx]` `their_last` | `vague`, `correction` or `heard` | removed (commit 2) |
| `[ctx]` `clarification_available` | `yes` until a line was found in a past reply | `clarification_lines: <line> \| <line>` while nothing is running (commit 2) |
| `[ctx]` `after_framework_question` | the next unasked question | `after_framework_questions: <q1> \| <q2> \| <q3>` while the ending is in the window (commit 2) |
| Memory fold message | `## Known so far`, `## Conversation` | `max_entries: <n>` first, then the same headings (commit 2) |

**Value sourcing**:

| Action | Value | Source |
|---|---|---|
| `start_thread` greeting | template, name, style question | `Config.replies.greeting`, `profiles.nickname` (else `default_name`), `Config.replies.style_question` |
| `start_thread` greeting | new or returning | `_has_earlier_thread`, as today |
| Greeting buttons | `{label, style}` pairs | `Config.replies.style_labels` in `SupportStyle` order |
| Style tap | style from label | the options stored on the greeting message, as today (`orchestrator.py` around line 197), so a label renamed later never breaks an open thread |
| Style turn reply | opener | `Config.replies.openers[style]`, passed to `_open_in_style` |
| `cooldown_passed`, `clear_cooldown_for` | the three offer counts | `Config.tuning.offers` |
| `resolve_style` | the default | `Config.tuning.offers.default_style` |
| Router scoring | recency weights, strong and signal weight, floor | `Config.tuning.router`, passed as `weights` |
| Router start | `router_min_exchanges` | `Config.tuning.router` |
| History the model sees, summary refresh in a turn | `context_window` | `Config.tuning.windows` |
| Summary backstop (`reconcile_due`, cron) | threshold | `Config.tuning.windows.context_window`, loaded by `reconcile_due` |
| `GET` thread tail (`routers/threads.py` `_history`) | 20 | `THREAD_TAIL` in that module, an API page size |
| `recent_styles` | `style_window` | `Config.tuning.windows`, a query parameter |
| `recent_openers` | word count and window | `Config.tuning.windows`, via `context.build(tuning=...)` |
| Title | when | `Config.tuning.windows.title_after_messages` |
| Memory bound | entries, characters | `Config.tuning.memory`, passed by `fold_one` |
| Memory fold message | `max_entries` | `Config.tuning.memory.max_entries` (commit 2) |
| Idle fold | `idle_before` | now minus `Config.tuning.memory.idle_after_hours`, computed by `fold_idle_threads.py` |
| `[ctx]` `clarification_lines` | the lines | `Config.replies.clarification_lines`, joined by ` \| `, via `context.build(replies=...)` |
| `[ctx]` `after_framework_questions` | the questions | `Config.replies.after_framework_questions`, joined by ` \| ` |
| Eval harness | the questions, the style label to tap, `style_window` | `content/prompts/replies.md` and `tuning.md` through `seed.parse_prompt` and the parsers |
| Baseline content hashes | the two rows | `config.require("replies")`, `config.require("tuning")` |
| Seed and admin write refusals | the problem text | `content_problem(name, content)`; deactivate and rename refusals from the required rows check |
| Tests | a `Replies` and a `Tuning` | one shared test helper that parses the seeded files, overridden per test with `model_copy(update=...)` where a test needs another value |

**Key invariants**:
- No line Mani sends without the model and no conversation number in AC-2 is a constant in `backend/mani/` or `backend/scripts/`. `REMOVED_NAMES` holds the old names out.
- `replies` and `tuning` are always present, active and parseable in a database written through the seed or the portal. A direct SQL edit that breaks one fails the next load loudly with `CONFIG_ERROR`, never silently.
- The files in `content/` are the source of truth. A reseed restores them over any portal edit.
- The `style_labels` and `openers` keys are exactly the `SupportStyle` values, and no two labels are equal ignoring case.
- With a fixed `context_window`, the summary refreshes (in the turn and in the backstop) every `context_window` messages, so no message is ever outside both the history and the summary.
- Neither row is sent to any model.

**Security model**: no change in who may read or write what. The rows sit in `admin.prompts`, read through `pool.as_admin()` at cache load, written only by the seed and the admin routes. One thing widens: an admin can now change what every person is greeted with and how the conversation is timed, from the portal. The write check and the ranges keep that from breaking turns or reopening the memory caps, and `admin.prompt_versions` keeps the history of every portal edit. Refusals and logs carry keys and rules only, never the value written or any message text.

**Configuration required**: none new.

**Critical test scenarios**:
- `parse_replies` and `parse_tuning` accept the seeded files and refuse each bad case in AC-1 and AC-2 (an unknown key, `{nickname}`, `{}` or a stray `{` in a greeting, a missing style, two labels equal ignoring case, ` | ` in a clarification line, increasing recency weights, a `context_window` of 3 or 101, `max_entry_chars` 501, `"2"` for a count). Verifies **AC-1**, **AC-2**.
- Cache load with a fake row list missing `tuning`, or with `replies` that does not parse, raises `CONFIG_ERROR`, also when an earlier good snapshot exists. Verifies **AC-3**.
- `content_problem` returns a problem for a bad `tuning` that does not contain the bad value, and None for an unchecked name. Seed refuses a prompts directory without `replies.md`. Against the database, a `PATCH` with bad `tuning` content, a `PATCH` setting `response_format` inactive and a `PATCH` renaming `replies` each return 422 and leave the row and `prompt_versions` unchanged. Verifies **AC-4**.
- The greeting for a nickname, for none, and for a returning person, its buttons, and each opener, built from the parsed seeded `replies`, equal today's strings exactly. Verifies **AC-5**.
- With a `Tuning` from the helper and one value overridden: `cooldown_after_complete` 3 lets an offer through 3 messages after a completed set; `context_window` 4 sends 4 messages of history and `reconcile_due` uses 4 as its threshold; `recency_weights` [1.0] scores an old message at full weight; `max_entries` 2 bounds each memory list at 2. With the seeded values, every kept `test_router.py` ranking and `test_chat_context.py` case holds unchanged. Verifies **AC-6**.
- The eval validator still finds the three questions, read from `replies.md`, and `content_hashes` changes when `tuning` changes. Verifies **AC-7**.
- A module that binds `OPENERS` fails the removed names test (checked by the test's own fixture, not by editing `mani/`). Verifies **AC-8**, **AC-14**.
- `context.build` for "idk" carries no `their_last`. With no framework running it carries `clarification_lines` with both lines, even after one was asked. After a Chat More reply, it carries all three `after_framework_questions`, and none while a safety concern is on. Verifies **AC-9**, **AC-10**, **AC-11**.
- A reply whose technique button is dropped keeps a `Tell me about this` button that has no `decline`, and drops its Keep chatting. Verifies **AC-12**.
- The fold message starts with `max_entries: 6` for the seeded tuning. Verifies **AC-13**.
- The `CTX_KEYS` and `response_format.md` contract test passes, no prompt names `their_last`, `clarification_available` or `after_framework_question` as a whole word, and `after_framework_questions` does not trip the check. Verifies **AC-14**.

## Build plan

Tracer Bullet: the first task threads one line, the openers, through every layer (content file, parser, check, seed, admin write, cache, code, test), so the path is proven before the rest moves onto it. Two commits on `feat/model-text-out-of-python` (muhammad, 2026-10-08): tasks 1 to 6 are commit 1, the pure moves, and tasks 7 to 11 are commit 2, the behaviour changes, so commit 2 can be reverted alone. The whole `pytest` stays green after every task.

**Commit 1: pure moves**

1. Tracer: write `replies.md` with `openers` only, `parse_replies` for that key, `mani/prompts/checks.py` with `content_problem` and `parse_reply_shapes` moved in (repointing its five importers), the seed refusal, the required rows check in `config_tables` (content, deactivate, rename, 422), `Config.replies` declared before `reply_shapes`, `replies` in `REQUIRED_PROMPTS`, `_read` wrapping parse failures in `CONFIG_ERROR`, the shared test helper, and `_open_in_style` replying from `openers`. Fix the direct `Config(...)` builds in `test_composer.py` and `test_stt.py`. Delete `OPENERS`, start `REMOVED_NAMES`, reseed. Satisfies **AC-1**, **AC-3**, **AC-4**, **AC-5**, **AC-8**.
2. Fill `replies.md` with the greeting, the style question and labels, and the two line lists, and finish `parse_replies` with every refusal in AC-1. Move `greeting()` and the buttons onto it in `start_thread`, and point the clarification and after framework matching, `eval_replies.py` (including `_open_chat`), `validators.py`, `test_style_findings.py` and `test_prompt_lines_the_code_reads.py` at it. Delete `DEFAULT_NAME`, `STYLE_QUESTION`, `STYLE_OPTIONS`, `AFTER_FRAMEWORK_QUESTIONS` and `CLARIFICATION_QUESTIONS`, and rewrite `test_greeting.py`. Satisfies **AC-1**, **AC-5**, **AC-7**, **AC-8**.
3. Write `tuning.md`, `parse_tuning` with the ranges, `Config.tuning`, `tuning` in `REQUIRED_PROMPTS` and the checks, and add both rows to `baseline.content_hashes`. Move the turn's `cache.load()` before `load_turn_context`. Move offer timing and `default_style` into `context.py` (`context.build` takes `replies` and `tuning`), and the router weights into `router.py` (the `weights` argument). Update the callers in `test_router.py` (about 35, through a module level fixture), `test_chat_context.py` and `test_turn.py` (`context.build` around lines 484 and 1184, `COOLDOWN_AFTER_COMPLETE` around line 1139). Satisfies **AC-2**, **AC-3**, **AC-4**, **AC-6**, **AC-7**.
4. Move the windows: `recent_for_context` without a default (callers in the orchestrator, `test_turn.py` around lines 989, 1024 and 1067, `test_memory.py` around line 131, `test_queries.py` around line 96), `THREAD_TAIL` in `routers/threads.py`, the summary on `context_window` in the turn and in `reconcile_due` (updating `test_summarize.py` and `test_cron.py` where they rely on 20), `style_window` as a query parameter for `load_turn_context` (about 12 calls in `test_turn.py`, about 8 in `test_queries.py` including `STYLE_WINDOW` around line 228, and `eval_replies._framework_after`), the openers window and words, and `title_after_messages`. Satisfies **AC-6**, **AC-7**.
5. Move the memory limits: `bounded(memory, limits)` from `fold_one`, and `idle_after_hours` in `fold_idle_threads.py`. Delete `IDLE_AFTER` and give `test_memory.py` (around lines 156 and 204) an explicit value. `memory_fold.md` and the fold message are untouched in this commit. Satisfies **AC-6**.
6. Complete `REMOVED_NAMES` for commit 1, reseed, run the whole `pytest` against the local database with the integration count checked, and update `PORT-STATUS.md` (the new decision line) and `docs/database-schema-reference.md`. Commit. Satisfies **AC-8**, **AC-15**.

**Commit 2: behaviour changes**

7. Delete `classify_reply`, the three lists and `their_last` (argument, line, `CTX_KEYS`), and edit `response_format.md` (the entry, reasoning step 1) and `mani_base.md` (mirror and hold). Delete or rewrite the `test_chat_context.py` cases that read them. Satisfies **AC-9**.
8. Replace `clarification_used` and `clarification_available` with `clarification_lines`, and the after framework matching with `after_framework_questions`, in `context.py`, `CTX_KEYS` and `response_format.md`. Delete `test_prompt_lines_the_code_reads.py`. Satisfies **AC-10**, **AC-11**.
9. Delete `TELL_ME_ABOUT_THIS_LABEL` and `EXPLAIN_LABELS`, simplify `_is_offer_button`, correct the guard comments, and rewrite the `test_guards.py` and `test_turn.py` cases named in AC-12. Satisfies **AC-12**.
10. Add the `max_entries:` line to the fold message and name it in `memory_fold.md`, updating the `test_memory.py` assertions on the message. Satisfies **AC-13**.
11. Extend `REMOVED` (with whole word matching) and `REMOVED_NAMES`, reseed, run the whole `pytest` with the integration count checked, and edit the three `PORT-STATUS.md` lines in place. Commit. Satisfies **AC-14**, **AC-15**.

## Consequences

**Positive**:
- The greeting, the openers, the check lines and every conversation number can be changed with a reseed and no deploy, and tried in the portal first, with a version history.
- A bad edit is refused when it is written, and the ranges keep a typo from reopening the memory caps or summarising every message. The same check also closes part of spec 0007's follow-up: a portal edit can no longer empty `mani_base`'s `reply_shapes`, or deactivate or rename a required row.
- The code loses three phrase lists, a classifier, two history scanners and a dead label set, and the clarification lines have one home instead of two.
- Saved baselines now record when the lines or the numbers changed.

**Negative / tradeoffs**:
- Nothing tells the model what to do with "idk", "I already told you" or "just listen" any more. The tuned rules went with the lists (muhammad's choice). Expect more repeated questions after a vague reply, and corrections answered less directly, until real runs show otherwise. The eval scenarios that test these cases (`pain_vague_clarification`, the one with `heard: true`) are left as they are, so feature 11's runs will show it.
- The model now tracks the clarification line and the after framework questions from its own history. It may ask a line twice, or skip one, and no code catches it. As today, a line asked more than `context_window` messages ago is out of sight and may come back. `after_framework_questions` is sent until the ending leaves the window, so after all three are asked, stopping depends on the model. `clarification_lines` is sent on every turn where nothing is running, uncached, so each such turn costs a few more input tokens than `clarification_available: yes` did.
- All of commit 2 is unmeasured. It ships on unit and contract tests alone.
- A portal edit to these rows is a trial: the next seed, which runs before every deploy, puts the file's value back. A change meant to last goes into `content/` and git.
- An admin can change the greeting every new conversation opens with, or set a cooldown that makes offers rare. The checks stop broken values, not bad judgement. A portal edit reaches the instance that served it at once and the others after the cache TTL.
- A direct SQL edit, or a deploy before the seed, makes every turn fail with `CONFIG_ERROR` until the rows are fixed. That is the price of no defaults in code.
- Lowering `context_window` mid conversation can leave the messages between the old and new window outside both the history and the summary once, until the next refresh catches up.

**Neutral**:
- `THREAD_TAIL` keeps the thread endpoint's page at 20 even if `context_window` changes, so what the app shows and what the model sees can differ.
- The `style_labels` and `openers` keys stay tied to `SupportStyle`. Adding a style is still a code change.
- A crisis locked thread with a broken row now gets `CONFIG_ERROR` rather than its usual refusal, because the config loads first.
- `mobile/src/dictionaries/en.json` still carries its own copy of the style question (`stylePrompt`). See Follow-up.

## Migration plan

**Strategy**: no schema migration. Seed first, then deploy, once per commit.
**Phases**:
1. Run `python scripts/seed.py` against hosted from commit 1. Old code ignores the two new rows.
2. Deploy commit 1. It requires both rows, which phase 1 wrote.
3. For commit 2, seed, then deploy. For those minutes, old code sends `their_last`, `clarification_available` and `after_framework_question`, which the prompts no longer explain, and the fold prompt names a `max_entries` line the old code does not send. That is the same short window spec 0007 accepted.

**Rollback**: revert the commit, check out the previous `content/`, and reseed. The two rows can stay, because old code never reads them.
**Risks**: deploying commit 1 before seeding fails every turn with `CONFIG_ERROR`. Keep the order. Any portal edit to these rows is overwritten by phase 1 and phase 3.

## Follow-up

- [ ] Delete `mobile/src/dictionaries/en.json` `stylePrompt` once mobile renders the greeting from the API, so the style question has one home.
- [ ] `threads.vague_streak` (migration 002, with a `mani_service` grant) is read and written by nothing. Drop it in its own migration.
- [ ] When the frontends call the API, map each error category to dictionary text, and stop showing `ServiceError.user_message`.
- [ ] Spec 0007's follow-up still owes the framework admin path a check of `distinctions`.
- [ ] Measure commit 2 with real runs under feature 11 (vague, correction and heard scenarios, clarification asked at most once, the three questions in order), after muhammad's yes.
- [ ] `.claude/BACKEND.md` says `fold_idle_threads.py` is also reachable as `GET /internal/cron/fold-summaries`. That route runs `reconcile_due`, not the idle fold. For `/sync`.
- [ ] Update the scope: feature 7 gains the ending labels and patterns, and feature 10 gains `CRISIS_REPLY` and `RECENT_CRISIS_DAYS`.

## Rationale

Reasoning, options and the inventory: see [rationale.md](rationale.md).
