# 0008. Decision record: reply text and conversation numbers in seeded content

The build spec is [index.md](index.md). This file holds the why: what forces shaped the decision, what else was weighed, and an inventory of what stays in Python and why.

## Context

> ⚠️ Premise note: the scope row for feature 9 lists the crisis reply and the button labels, but they belong to features whose own work will rewrite them. The ending's labels sit next to code that reads Mani's and the person's words (`_ASKS_WHAT_NEXT`, `_PLACE_WORDS`), which feature 7 is set to replace with rules the model follows. The crisis reply sits beside a screen that feature 10 replaces. Moving that text now would add a content home that the next feature either moves again or deletes. muhammad drew the line: the ending stays for feature 7, all of crisis for feature 10. The scope row is narrowed to match.

> ⚠️ Premise note: the phrase lists and the "already asked" matching are not text Mani sends. They are code that reads what people and Mani said. Deleting them (commit 2) is a behaviour change, not a move, and it ships without a real model run. muhammad chose that knowingly. It is recorded as the main risk in Consequences, and kept in its own commit so it can be reverted alone.

Spec 0007 made every sentence the model reads live in seeded content. What it left is the other half: lines Mani sends without the model, and the numbers that time a conversation. Both are still Python constants: `greeting.py` holds the greeting, the style question and buttons, the openers, and the client's clarification and after framework lines. About twenty numbers are spread over `context.py`, `orchestrator.py`, `router.py`, `memory.py` and `db/`. Changing the wording of a greeting, or a cooldown, means a code change and a deploy, while the prompts beside them change with a reseed.

Three constraints shape where they can go. The client's lines are matched: the code finds the clarification lines and the after framework questions in Mani's past replies to know which were asked, so rewording one silently breaks the tracking (journal: client lines the code matches exactly). The clarification lines already live twice, in `greeting.py` and in `response_format.md`, held together only by a test. And the portal can edit any prompt row while skipping the seed's checks, so content that code depends on can be broken by a single edit. Spec 0007 met that with soft failures, which keep turns running and leave the breakage visible only in logs.

There are numbers that look like tuning but are not: `OPENING_MESSAGES` counts what the code itself writes, and pool sizes, timeouts, TTLs and token budgets belong to the deployment. `SUMMARY_THRESHOLD` is tied to `CONTEXT_WINDOW` on purpose, because a threshold above the window leaves messages in neither the history nor the summary. Any home for the numbers has to keep that tie.

## Options considered

### Option 1: Two seeded YAML rows, checked on every write (chosen)

`replies` and `tuning` as rows in `admin.prompts`, authored in `content/prompts/`, parsed into typed pydantic models at cache load, required like `mani_base`, and checked by one function at seed, at the admin write and at load.

**Pros**:
- Reuses everything that exists: the seed, the portal editor, `prompt_versions` history, the cache and its TTL. The pattern is the one spec 0007 used for `reply_shapes`. No migration, because `admin.prompts` has no type column.
- One typed parser per row means every reader gets checked values, and a bad edit is a refused write, not a broken turn.
- Text and numbers stay separate, each with its own checks and its own edit history.

**Cons**:
- Adds two required rows: a deploy before the seed fails every turn.
- An admin can now change what everyone is greeted with, and how offers are timed.
- YAML in a text column has no database level typing. The checks live in Python.

### Option 2: Everything in `mani_base.md`

Put the lines and numbers next to `reply_shapes` in the base prompt row.

**Pros**:
- No new rows, and it uses the parse path that exists.

**Cons**:
- `mani_base` is the model's system prompt: every line and number would be sent on every call, costing tokens and mixing what the model is told with what is sent to people.
- One edit history for unrelated changes.

### Option 3: Typed admin tables

`admin.reply_text` and `admin.tuning` with a migration, column types and check constraints, RLS and grants.

**Pros**:
- The database itself types and constrains the values.

**Cons**:
- A migration, policies, grants and a portal editor that does not exist, for about thirty values.
- Two homes for the checks (SQL constraints and the Python model the code reads), which spec 0007's journal showed drift.

### Option 4: Environment settings for the numbers

pydantic-settings fields in `config.py`, per environment.

**Pros**:
- Typed and validated at startup, and different per environment.

**Cons**:
- A change needs a redeploy or restart, which is what this feature exists to remove.
- Not editable by an admin, and no history.

## Rationale

The forces are: change without deploys, one home per value, and no edit that can quietly break a turn. Option 1 is the only one that meets all three with no new machinery. The seed, the portal and the version history already exist for prompt rows, and `content_problem` follows the `effort_problem` pattern from spec 0004, run in the same place in `config_tables` as `_check_callable`. Option 2 fails one home in the other direction, by sending people's lines to the model. Option 3 buys database typing at the cost of a second home for every rule. Option 4 keeps the deploy that this feature exists to remove.

On failure, muhammad chose to refuse at every write rather than spec 0007's soft failures. That is the right call for these rows: unlike a dropped distinction rule, there is no safe value to fall back to for a greeting or a cooldown without putting a default back in code, which would recreate the second home. With the seed and the admin routes both refusing, only a direct SQL edit can break a row, and that fails loudly at load.

The second commit hands three jobs to the model: noticing a vague or correcting message, remembering whether it asked the clarification line, and keeping the after framework questions in order. It fits the scope's direction (lean prompts, no code that reads people's words), and it removes the clarification lines' second home. The cost is that each job is now told, not enforced or detected, and is unmeasured. muhammad chose tests only. I would have run a 3 run baseline on the vague and heard scenarios before calling commit 2 done, because the dropped rules were tuned against real failures. That is recorded as a Follow-up for feature 11, not hidden.

Smaller calls I made, each with its runner up:
- **Keys are the old constant names in lowercase**, grouped (`offers`, `router`, `windows`, `memory`), so every value traces back to the code it replaced. Runner up: friendlier names, which would cost that trace.
- **`content_problem` lives in `mani/prompts/checks.py`** and covers `mani_base` too, since it is one dictionary entry and closes part of spec 0007's follow-up. `parse_reply_shapes` moves there from `cache.py`, because `cache.py` imports `config_tables`, which now imports the check, and leaving it in `cache.py` would make an import cycle. Runner up: only the two new rows, leaving `reply_shapes` unchecked in the portal.
- **Deactivating or renaming any required row is refused**, extending `_check_callable`'s rule for call rows. Rename was not asked separately: it empties a required row exactly as deactivating does.
- **`THREAD_TAIL = 20` in `routers/threads.py`** for the thread endpoint's page, so an API response size is not tuned from content. Runner up: pass `context_window`, which would make the app's page change when the model's window is tuned.
- **`style_window` as a query parameter** rather than formatted into the module level SQL, so the statement text stays fixed. Runner up: building the SQL per call.
- **The memory fold message gains a `max_entries:` line** so `memory_fold.md` stops saying "six" and the number has one home. Runner up: leave "six" in the prompt, which would have two homes.
- **Lines joined by ` | `** in `[ctx]` values, which matches spec 0007's single line `key: value` form. Runner up: one key per line, which would need numbered keys in `CTX_KEYS`.
- **Commit 1 moves the matched lines with their matching intact**, and commit 2 removes the matching. That way commit 1 changes nothing any model sees and can be checked against today's tests.

Three more decisions came out of the cross check, each muhammad's:
- **The files are the source of truth** for these rows, as for every prompt row. The seed overwrites a row on every run, so a portal edit is a trial that lasts until the next seed, which runs before every deploy. Runner up: the seed inserts `replies` and `tuning` only when absent, so portal tuning survives deploys. That would leave git no longer saying what is live, and changing a value from the file would need a manual step.
- **The memory fold's `max_entries:` line goes in commit 2**, because it changes what a model call sees. Commit 1 then changes no model input at all.
- **Every tuning number has an upper bound** (AC-2), set well above today's values so it only catches mistakes. Without one, a typo in `max_entries` or `max_entry_chars` reopens the runaway list that `memory.py`'s caps exist to stop, and a tiny `context_window` summarises nearly every message.

## Inventory: what stays in Python, and why

| Constant | Where | Stays because |
|---|---|---|
| `CHAT_MORE_LABEL`, `GO_TO_LIBRARY_LABEL`, `_HANDOFF_LABELS` | `greeting.py`, `orchestrator.py` | the body ending, feature 7 |
| `PLACE_LABELS`, `_PLACE_WORDS`, `_DECLINES_OR_ACTS`, `_COMES_BACK`, `_ASKS_WHAT_NEXT` | `ending.py`, `orchestrator.py` | the body ending, feature 7 |
| `CRISIS_REPLY`, `RESOURCES`, `PROTOCOLS`, `CLARIFICATION`, `_CRISIS`, `_CONCERN` | `crisis.py`, `safety.py` | crisis, feature 10 |
| `RECENT_CRISIS_DAYS` | `db/threads.py` | crisis, feature 10 |
| `_CONTRACTIONS`, `_APOSTROPHES`, `normalize` | `safety.py` | shared text normalising for the router and the screen |
| `OPENING_MESSAGES` | `context.py` | counts what the code writes |
| `MAX_FOLDS_PER_RUN`, `BATCH` | `memory.py`, `db/memory.py`, `summarize.py` | batch bounds of a job |
| `MAX_TITLE_LENGTH` | `guards.py` | a storage limit |
| `DEFAULT_PAGE` (both), `THREAD_TAIL` | `db/messages.py`, `db/threads.py`, `routers/threads.py` | API page sizes |
| `MIN_POOL_SIZE`, `MAX_POOL_SIZE`, `COMMAND_TIMEOUT_SECONDS` | `db/pool.py` | deployment |
| `DEV_PROMPT_CACHE_TTL`, `PROD_PROMPT_CACHE_TTL`, `SIGNED_URL_TTL_SECONDS` | `config.py`, `storage.py` | deployment |
| `DEFAULT_TEMPERATURE`, `DEFAULT_MAX_TOKENS`, `EXERCISE_MAX_TOKENS`, `REASONING_ALLOWANCE_TOKENS`, `REASONING_MODEL_PREFIXES`, `MAX_SCHEMA_ATTEMPTS`, `TRANSIENT_RETRY_DELAY_SECONDS` | `llm/` | model call plumbing; per call settings already live in each prompt row |
| `TIMEOUT_SECONDS`, `MAX_AUDIO_BYTES` | `stt.py` | deployment |
| `ServiceError.user_message` strings | across `mani/` | error wording belongs to the frontends' dictionaries |
| `SupportStyle`, `CTX_KEYS`, `LAYER_HEADINGS` | models, `context.py`, `composer.py` | closed sets the code owns, tied to content by tests |
