# 0002. Measure turn cost and latency with a repeatable eval baseline: decision record

The build spec is [index.md](index.md).

## Context

The lean prompt scope (`docs/scope/scope.md`) is meant to cut tokens and latency. Today nobody can say what a turn costs. `admin.llm_calls` records input, cached and output tokens and the latency of each provider call. But it drops reasoning tokens (the hidden thinking the model does before it answers, billed as output), and nothing counts how many calls one turn made. One turn can be the first draft, up to two redrafts, a retry inside each, and an exercise pick at the end of a framework.

The only way to drive real conversations is `backend/scripts/eval_replies.py`. It already deletes its own cost rows at the end, on purpose: synthetic rows once skewed the cache average from about 60% to 53%. So every number it produces disappears with the run. The journal also records that one run is noise. The same prompt gave 3 findings and then 7. A change has to be judged on several runs before and several after.

Two constraints shape the answer. First, local and hosted databases are not the same schema. Hosted has migrations 011 to 017 from reverted branches and holds real people's data, while local was reset to 001 to 010 on 2026-10-07. Second, every run spends the client's OpenRouter credit (19.02 dollars on 2026-10-07; `openai/gpt-6-luna` costs 0.10 dollars per million input tokens, 0.01 cached, 0.50 output). The conversations are health content, so nothing that leaves the database should carry reply text.

Without this, each later feature in the scope (short base prompt, 8 line frameworks, one model call) gets judged by feel. That is exactly how the 2026-09-23 audit judged prompt changes on noise.

## Options considered

### Option 1: Fix in place, a `--baseline` mode on `eval_replies.py`

Extend the existing runner. It already drives real conversations, creates and removes synthetic users, and runs the quality checks. Capture each turn's cost rows before cleanup, aggregate across runs, and write a JSON file. The aggregation and comparison go in a small module beside it, so the runner stays a driver.

**Pros**:
- One way to drive conversations, so cost and quality come from the same turns.
- Reuses the user lifecycle, scenario file and validators that already work.

**Cons**:
- `eval_replies.py` is already 332 lines and gains another mode to keep straight.

### Option 2: A separate `measure_turns.py` script

A new script that imports the runner's conversation driver and adds the measurement.

**Pros**:
- The plain eval stays untouched.

**Cons**:
- It either copies the conversation driving (duplication the project rules forbid) or imports private helpers across scripts.
- A second command for running conversations, so cost and quality runs drift apart over time.

### Option 3: A SQL report over real traffic in `admin.llm_calls`

No scripted conversations. Query real turns over a time window.

**Pros**:
- Measures what people actually do, with no credit spent on scripts.

**Cons**:
- No fixed input, so before and after are different conversations and the comparison is meaningless at today's volume.
- Real traffic lives on hosted, a different schema holding real people's health conversations.

## Rationale

The scope's first slice changes the base prompt, the framework content and the call count together for one framework. Its value rests on one number moving: tokens and latency per turn. The runner already produces the turns. What is missing is keeping the numbers and repeating the run. So the smallest change is fix in place. It gives one command, and both cost and quality checks read the same replies. That matters because the cheapest prompt is worthless if the findings double, and AC-6 puts both in one file.

You chose to store reasoning tokens in the database rather than only in the eval output. That costs a migration, and its number has to skip 011 to 017 so it never collides with the hosted migrations of the same numbers (the trap the journal recorded on 2026-10-06). In return, production keeps the number, and feature 11 (choosing a thinking level) can read real traffic later. Adding a column with a constant default is a metadata change in Postgres, so it does not rewrite the table.

Local only enforcement and leaving reply text out follow from the two constraints in Context. Hosted is a different schema with real people on it. A committed file must not carry conversation text, even from synthetic users, because the habit is the risk. Aborting on a failed turn keeps a broken run out of the medians. That is cheap: a run is 24 turns and roughly 30 calls (redrafts and the exercise pick add a few), so a 3 run baseline is about 90 calls at about 17k input tokens each, mostly cached, for about 0.10 to 0.20 dollars. Compare reads saved files, so it never spends anything. A baseline is paid for once, then compared as often as needed.
