# 0002. Measure turn cost and latency with a repeatable eval baseline

**Date**: 2026-10-07
**Status**: In Progress
**Decision record**: [rationale.md](rationale.md) (context, options considered, rationale)

## Summary

Before you shrink the prompts, you need a way to prove each change makes a turn cheaper or faster. This spec adds a `--baseline` mode to the existing eval runner. It plays three fixed conversations three times, and records for every turn the tokens (input, cached, output and reasoning), how many model calls it made, and how long it took. It saves the numbers to a JSON file in the repo, and a separate offline command compares any two saved files at no cost. Production calls also start recording reasoning tokens through one new database column, and each call's latency stops counting the retries before it.

## Requirements

**User stories**:
- As muhammad, I want one command that measures what a turn costs today, so that every prompt change after it can be shown to save tokens or time.
- As muhammad, I want to compare two saved runs, so that I can see the change per scenario without reading two files by hand or paying for another run.

**Acceptance criteria**:
- **AC-1**: `python scripts/eval_replies.py --baseline --label <name>` runs only the scenarios tagged `baseline: true` in `eval_conversations.yaml` (`anxiety_free_chat`, `criticism_abcde`, `journey_abcde`), in the Supportive style only, 3 times by default, with a fresh user for each scenario in each run. Runs go in order: the whole set once, then the whole set again. `--runs N` (N at least 1) changes the count. `--label` (letters, digits, `-`, `_`) is required with `--baseline`. `--runs` and `--label` without `--baseline`, and `--scenario` or `--user` with it, are refused by `parser.error`.
- **AC-2**: For every script line that sends a message through `orchestrator.send` (not the greeting or the style tap), the run records: its position in the scenario's YAML `turns` list, the raw script token and its kind (`typed`, `tap`, `accept`, `fallback`), the number of provider calls, the summed input, cached, output and reasoning tokens, the summed model latency, the whole turn latency (wall time of `send`), and the purpose and outcome of each call in the order the rows were written. Redrafts, retried attempts and the exercise pick all count.
- **AC-3**: Every provider call, in production and in evals, stores its reasoning tokens in `admin.llm_calls.reasoning_tokens`, taken from the provider's usage. That includes failed attempts whose usage the SDK kept, which also start recording their cached tokens. It is 0 when the provider reports none.
- **AC-4**: The numbers are read before the eval removes its users. After the run, no `admin.llm_calls` or `auth.users` row from that run remains, as today.
- **AC-5**: A successful run writes `backend/scripts/baselines/<YYYY-MM-DD>-<label>.json` (UTC date at the start of the run). It holds:
  - a header: label, start time, git commit, a hash of the code diff, model, effort per call purpose, content hashes, a hash of the tagged scripts, database host, run count, scenarios, and `reasoning_reported`;
  - the per run turn rows;
  - per scenario totals for each run, and their median, minimum and maximum across runs (the main numbers for comparison);
  - per line median, minimum, maximum and `present_in` (for diagnosis);
  - the median of each total across runs.

  The file never holds reply text, button labels the model wrote, or database credentials. If the file already exists, the run stops before any model call, with a message, and exits 1.
- **AC-6**: The eval's existing quality checks still run and print in a baseline run. The finding count per scenario per run goes into the JSON, alongside the cost numbers. Findings do not change the exit code: a completed baseline exits 0.
- **AC-7**: `python scripts/baseline.py compare <before.json> <after.json>` prints a table per scenario and in total: the median before, the median after, the difference and the percent change, for each token kind, calls, model latency, turn latency and findings. It uses the per scenario totals. Header differences (model, effort per purpose, content hashes, script hash, code diff hash, commit, run count) print above the table. It makes no model call and needs no database. A missing file, or one that is not a baseline file, exits 1 with a message.
- **AC-8**: A baseline run whose `DATABASE_URL` host is not `localhost`, `127.0.0.1` or `::1` stops before creating any user or making any model call, with a message, and exits 1.
- **AC-9**: If `orchestrator.send` raises on any turn, the run stops. It names the scenario, run and line that failed, writes no file and exits 1. If the run is interrupted (Ctrl C), it stops the same way. In both modes, the users the run created and their rows are removed even when the run stops partway.
- **AC-10**: Without `--baseline`, a run that completes behaves exactly as today: same scenarios, styles, output and exit code, and no file written.
- **AC-11**: A first baseline, labelled `before-lean-prompts`, is taken against the current content and committed, and its median totals are written in `backend/PORT-STATUS.md`. It is taken only after muhammad approves the real model run.
- **AC-12**: A baseline run stops before creating any user if `admin.llm_calls.reasoning_tokens` does not exist. It also stops (AC-9 rules) if any chat turn produced no cost row, since every chat turn makes at least one call, so lost cost rows can never pass as zeros.
- **AC-13**: Every `admin.llm_calls.latency_ms` is the time of that one attempt alone: not the attempts before it, and not the pause between retries.
- **AC-14**: When some call's effort is not `none` but every reasoning count in the run is 0, the run prints a warning and the file records `reasoning_reported: false`. Otherwise `true`.

## Decision

**Chosen option**: Option 1: a `--baseline` mode on `eval_replies.py` that measures and writes, an offline `scripts/baseline.py compare` that reads two files, and reasoning tokens stored in a new `admin.llm_calls` column (migration `018`).

Small calls I made (each with the runner up):
- **Matching a turn's rows**: each scenario in each run has its own fresh user and thread, and no baseline scenario uses `@newchat`. So after each `send`, the turn's rows are the thread's rows with an id the run has not seen yet, ordered by `created_at`. Every row is written and committed inside `client.complete` or `choose_exercise` before `send` returns. Runner up: a time window from the database clock, which is fragile if two rows share a timestamp.
- **Effort per purpose**: a new `chain.effective_effort(model, settings, effort)` returns what `_reasoning` sends (the given effort, else the configured default, or `None` for a model that takes no effort), and `_reasoning` uses it too. The header records it per purpose: `chat` from the `mani_base` row's `reasoning_effort`, `exercise_select` from the configured default (it passes none today). Runner up: one value for the run, which would be wrong for the exercise pick.
- **Content hashes**: the first 12 hex characters of sha256 over sorted key JSON of what the turns actually read, taken from `prompts.cache.load()` at the start. That covers the `mani_base` and `response_format` prompt content, plus each active framework's `activation` and `stages`. Chat calls store no `prompt_version_id`, and the git commit says nothing about what was seeded, so this is the reliable record of which content was measured. Runner up: reading `config_tables` directly, which can differ from the cache the turns use.
- **Code state**: the commit from `git rev-parse --short HEAD`, plus the first 12 hex characters of sha256 of `git diff HEAD -- backend/mani backend/content backend/scripts`. A plain dirty flag would always be true in this repo. Both are `null` when git is unavailable. Runner up: the dirty flag.
- **Script hash**: sha256 (first 12 hex characters) of the tagged scenarios' names and `turns`, so a changed script never compares as the same lines.
- **Where aggregation and compare live**: `backend/scripts/baseline.py`, pure functions (turn rows in, summary and deltas out) plus the `compare` command, unit tested with plain data. Runner up: inside `eval_replies.py`, which would force compare to run live.
- **The main number is the per scenario total.** In `journey_abcde` the offer can land on a different turn in each run, which shifts later lines by one. So scenario totals per run are what compare uses, and per line numbers (with `present_in`) are kept for diagnosis only.
- **Medians**: of each number on its own, kept as numbers with one decimal place (with an even run count a median can fall between two values). The "median totals" are therefore not one real run.
- **Cold cache**: no warm up turn. Run 1 starts colder than the others, and the median across 3 runs discounts it. Turn rows carry their run number, so a cold run stays visible.
- **Per attempt latency**: `client.complete` starts its clock at the top of each attempt, not once before the loop, so a retry row and the final row each record only their own time (AC-13). Runner up: documenting the sum as inflated on retry turns, which would make "whole turn minus model" go negative.

## Feature design

**Data model sketch**:

`admin.llm_calls`, one column added by `backend/supabase/migrations/018_llm_call_reasoning_tokens.sql`:

| Column | Type | Rule |
|---|---|---|
| `reasoning_tokens` | `integer not null default 0` | `check (reasoning_tokens >= 0)`. It is a part of `output_tokens`, never added on top of it. |

In code:
- `llm_calls.Usage` gains `reasoning_tokens: int = 0`, and `llm_calls.record` writes it.
- `chain.usage_from` reads it from `usage_metadata["output_token_details"]["reasoning"]`, or else from `response_metadata["token_usage"]["completion_tokens_details"]["reasoning_tokens"]`. Which shape OpenRouter's reply arrives in through LangChain is confirmed in the first build task by one recorded call, and noted in the code comment.
- `client._usage_of` (failed attempts) reads `completion_tokens_details.reasoning_tokens` and `prompt_tokens_details.cached_tokens` from the SDK's usage, as well as the two counts it reads today.
- `client.complete` takes `started` at the top of each attempt.

Baseline file `backend/scripts/baselines/<YYYY-MM-DD>-<label>.json`:

```json
{
  "label": "before-lean-prompts",
  "created_at": "2026-10-07T14:02:11Z",
  "git": {"commit": "85c3791", "diff": "9f2c41aa07be"},
  "model": "openai/gpt-6-luna",
  "reasoning_effort": {"chat": "high", "exercise_select": "high"},
  "reasoning_reported": true,
  "content": {"mani_base": "a1b2c3d4e5f6", "response_format": "…", "frameworks": {"abcde": "…"}},
  "scripts": "5e0d7c11ab90",
  "database_host": "127.0.0.1",
  "style": "supportive",
  "runs": 3,
  "scenarios": ["anxiety_free_chat", "criticism_abcde", "journey_abcde"],
  "results": [
    {"run": 1, "scenario": "journey_abcde", "findings": 2,
     "totals": {"calls": 19, "input_tokens": 301220, "cached_input_tokens": 248100,
                "output_tokens": 9310, "reasoning_tokens": 420,
                "model_latency_ms": 61200, "turn_latency_ms": 64900},
     "turns": [
      {"line": 4, "token": "@accept|Yes, let's look at it", "kind": "accept", "calls": 2,
       "input_tokens": 17120, "cached_input_tokens": 13900, "output_tokens": 610,
       "reasoning_tokens": 26, "model_latency_ms": 4100, "turn_latency_ms": 4380,
       "purposes": ["chat", "chat"], "outcomes": ["ok", "ok"]}
    ]}
  ],
  "summary": {"journey_abcde": {
    "totals": {"calls": {"median": 19.0, "min": 17, "max": 22}, "…": "same shape per number"},
    "lines": [{"line": 4, "present_in": 3, "calls": {"median": 2.0, "min": 1, "max": 2}, "…": "…"}]
  }},
  "totals": {"median": {"calls": 31.0, "…": "…"}, "min": {"…": "…"}, "max": {"…": "…"}}
}
```

`token` is the script line exactly as written in the YAML. `kind` says what was sent: `typed` (the text itself), `tap` (an `@tap:` button), `accept` (the offer button was tapped) or `fallback` (no offer was there, so the `@accept` fallback text was sent). The button label itself is never stored.

**API surface** (command line):

| Command or flag | Takes | Effect | Errors |
|---|---|---|---|
| `eval_replies.py --baseline` | nothing | Tagged scenarios, Supportive only, measured, file written | exit 1 when not local (AC-8), the column is missing (AC-12), the file exists (AC-5), a turn raised or had no cost row (AC-9, AC-12) |
| `eval_replies.py --runs` | integer at least 1; `None` by default, meaning 3 | How many times the tagged set runs | `parser.error` without `--baseline` or below 1 |
| `eval_replies.py --label` | letters, digits, `-` and `_` | Names the file | `parser.error` when missing with `--baseline`, given without it, or malformed |
| `baseline.py compare` | two paths to baseline JSON files | Prints the header differences and the delta table | exit 1 when a file is missing or not a baseline file (AC-7) |

`--verbose` keeps its meaning in both modes. `--scenario` and `--user` are refused with `--baseline`, so every baseline runs the same set with fresh users.

**Value sourcing**:

| Action | Value | Source |
|---|---|---|
| select scenarios | which scenarios | `baseline: true` in `eval_conversations.yaml` |
| per turn row | `line`, `token` | position and text of the line in the scenario's YAML `turns` list, carried on `Exchange` |
| per turn row | `kind` | the branch `_run_one` took for that line (typed, `@tap:`, `@accept` with an offer, `@accept` without one) |
| per turn row | `calls`, `purposes`, `outcomes` | count, `purpose` and `outcome` of the thread's `admin.llm_calls` rows not yet seen by the run, ordered by `created_at` |
| per turn row | token counts | sums of `input_tokens`, `cached_input_tokens`, `output_tokens`, `reasoning_tokens` of those rows |
| per turn row | `model_latency_ms` | sum of `latency_ms` of those rows (each attempt's own time, AC-13) |
| per turn row | `turn_latency_ms` | `time.perf_counter` around `orchestrator.send` in `_run_one`, not including the commit when the connection closes |
| scenario result | `totals` | sums of the turn rows of that scenario in that run |
| scenario result | `findings` | length of `_score(...)` for that scenario in that run |
| header | `model`, `reasoning_effort` | `composer.model_settings` on the `mani_base` row, then `chain.effective_effort` per purpose |
| header | `reasoning_reported` | false when some purpose's effort is not `none` and every turn's `reasoning_tokens` is 0 |
| header | `content` hashes | sha256 of sorted key JSON of what `prompts.cache.load()` returns at the start |
| header | `scripts` | sha256 of the tagged scenarios' names and `turns` |
| header | `git.commit`, `git.diff` | `git rev-parse --short HEAD`, and sha256 of `git diff HEAD -- backend/mani backend/content backend/scripts`; `null` when git is unavailable |
| header | `created_at`, file date | UTC time at the start of the run |
| header | `database_host` | `urlparse(Settings.database_url).hostname`, never the full URL |
| summary | median, min, max, `present_in` | `scripts/baseline.py` over the per run scenario totals, and over turn rows by scenario and line |
| compare | before and after values | the `summary` and `totals` of the two files given |

**Key invariants**:
- `reasoning_tokens` is never negative (database check), and is counted inside `output_tokens`, never added to it in a total.
- Every row the run created belongs to exactly one turn. No row counts twice.
- Every chat turn in a written file has at least one cost row.
- A file is written only by a run that completed every turn of every run.
- When a run completes without `--baseline`, nothing in this feature changes what the eval prints or returns.

**Security model**:
- Runs only against a local database (AC-8). Hosted is never measured by this command.
- Reads `admin.llm_calls` through `pool.as_admin()`, as the cleanup already does. `admin` is not exposed through the Data API.
- The file holds the authored script lines, numbers and hashes. It holds no reply text, no button labels the model wrote, no user ids, and no credentials (the database host only).
- The new column needs no grant changes: rows are written over the admin connection.

**Critical test scenarios**:
- `usage_from` returns the reasoning tokens from each of the two usage shapes, and 0 when neither carries them. `_usage_of` returns reasoning and cached tokens from a failed attempt's usage. Verifies **AC-3**.
- A real write through `llm_calls.record` stores `reasoning_tokens`, and an insert with a negative value is refused. Verifies **AC-3**.
- A fake model that fails once with a transient error, then succeeds, produces two rows whose latencies are each that attempt's own time, not including the pause. Verifies **AC-13**.
- Per run scenario totals from three fake runs give the right median (one decimal), minimum and maximum. Turn rows with a line missing from one run give the right `present_in`. Verifies **AC-5**.
- Two fake files give the right differences and percents, a zero before value prints no percent, and differing script hashes or run counts print in the header differences. Verifies **AC-7**.
- `reasoning_reported` is false when effort is `high` and every count is 0, and true otherwise. Verifies **AC-14**.
- The host check accepts `127.0.0.1`, `localhost` and `[::1]` URLs, and refuses a hosted Supabase URL. Verifies **AC-8**.
- The live run is checked by `/check verify`, not by a test, because it spends credit: **AC-1**, **AC-2**, **AC-4**, **AC-6**, **AC-9**, **AC-10**, **AC-11**, **AC-12**.

## Build plan

Ordered as a thin thread first (one run, one file), then thickened, following the project's Tracer Bullet approach.

1. Honest cost rows: migration `018_llm_call_reasoning_tokens.sql` with the column and check. `Usage.reasoning_tokens`, `usage_from` reading both shapes, `_usage_of` reading reasoning and cached tokens, `record` writing it, and `started` per attempt in `client.complete`. Confirm which usage shape OpenRouter sends with one recorded call (needs muhammad's yes, a fraction of a cent). Unit tests for both usage readers and the per attempt latency, plus an integration test doing the real write and the refused negative. Satisfies **AC-3**, **AC-13**.
2. Thin thread: `--baseline` and `--label`, scenario tags in the YAML, the host and column checks, line index, token and kind on `Exchange`, per turn row capture in `_run_one` (unseen rows plus wall time), read before cleanup, `try/finally` cleanup in `main()` for both modes, abort on a raised turn or a chat turn with no row, and a one run file with header and results. Satisfies **AC-1**, **AC-2**, **AC-4**, **AC-5**, **AC-8**, **AC-9**, **AC-10**, **AC-12**.
3. Thicken: `--runs N` in run major order, `scripts/baseline.py` with scenario totals, medians, ranges, `present_in`, findings counts and `reasoning_reported`. Unit tests for the aggregation. Satisfies **AC-1**, **AC-5**, **AC-6**, **AC-14**.
4. `baseline.py compare`: the header differences and the delta table per scenario and in total, with unit tests. Satisfies **AC-7**.
5. Docs in the same change: both commands in `.claude/BACKEND.md`, the column and the per attempt latency in `backend/docs/database-schema-reference.md`, and one line under "Decisions in force" in `backend/PORT-STATUS.md` (a prompt change is judged by `--baseline`, 3 runs before and 3 after, compared with `baseline.py compare`). Satisfies **AC-11** (the decision part).
6. Take the first baseline, `before-lean-prompts`, after muhammad's yes (about 0.10 to 0.20 dollars). Commit the file and write its median totals in `PORT-STATUS.md`. Satisfies **AC-11**.

## Consequences

**Positive**:
- Every later feature in the scope can be judged with numbers: tokens, calls and latency per turn, next to the findings count.
- Production starts recording reasoning tokens, which feature 11 needs to choose a thinking level.
- Whole turn latency minus model latency shows how much of the wait is ours (database, router, repairs), not the provider's.

**Negative / tradeoffs**:
- Three runs is still a small sample. Model latency varies with the provider's load, so a latency difference under about 15% should not be trusted on its own.
- Local migrations jump from 010 to 018. `supabase db push` to hosted stays blocked until 011 to 017 are reconciled, and that is not solved here.
- Baseline files accumulate in the repo. They are small (tens of kilobytes), but nothing prunes them.
- `eval_replies.py` gets a second mode, so there is more to keep straight in a script that is already long.
- `latency_ms` changes meaning for retried calls. Rows written before this change count the earlier attempts too, so an average over a window that spans the change mixes the two.
- Per line numbers in `journey_abcde` can mix framework stages across runs, because the offer lands on different turns. They are for diagnosis only; scenario totals are what to trust.
- Run 1 runs on a colder cache than runs 2 and 3, and a before and an after taken hours apart can differ in cache warmth as well. Cached token counts and latency carry that noise.

**Neutral**:
- The baseline runs only Supportive. Cost barely differs between styles, and the quality checks per style stay with `/check verify`.
- Content hashes, not the git commit, say what was measured, because the model reads seeded content, not the files.

## Migration plan

**Strategy**: no migration needed beyond one additive column.
**Phases**:
1. Local: `supabase db reset` (or apply `018` alone) and deploy the code that writes the column in the same change.
2. Hosted: only after 011 to 017 are reconciled (see Follow-up). Until then, hosted code must not ship this change, because `record` would write a column hosted does not have.
**Rollback**: revert the commit and drop the column in a new forward migration. The column holds only counts.
**Risks**: shipping the code to hosted before the column exists makes every cost row insert fail, which `_record` logs and swallows, so turns still work but cost rows stop. That is the same failure the journal saw with `llm_calls.decision` on 2026-10-06.

## Follow-up

- [ ] Reconcile hosted migrations 011 to 017 with this branch before any of this reaches hosted (already open in `PORT-STATUS.md`, "Open engineering").
- [ ] The config allows reasoning efforts `low|medium|high|xhigh|max`, but `gpt-6-luna` also takes `none`. That belongs to feature 2 (thinking level required), not here.
- [ ] Chat calls pass `prompt_version_id=None`, so `admin.llm_calls` cannot say which prompt version produced a reply. The content hashes cover the baseline; production traceability is a separate gap.
- [ ] The plain eval mode still removes its users from whichever database `DATABASE_URL` names, hosted included. That is unchanged here; worth a journal note.
- [ ] The tally and per style table at the end of a baseline run cover all runs together, and the "script" finding (a missing tap button) counts as a finding. Both are as today; the JSON is the place to read per run numbers.
