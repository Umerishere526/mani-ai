---
type: journal
date: 2026-10-11
apps: [backend]
tags: [journal, backend, prompts, evals, analytics, practice]
---

# Improving the chat with evidence: a working method

What worked on 2026-10-11, in the order to use it. The aim is to find a real defect, change one thing,
and show it moved, without reading private conversations or trusting one run.

## 1. Count before you read

Hosted conversations are special-category health data. Start with queries that return counts and
never message text (read-only, `.env.hosted`):

- Failures by purpose and outcome: `select purpose, outcome, count(*) from admin.llm_calls group by 1,2`.
  Memory folds were timing out while chat was clean, which pointed somewhere chat tests never looked.
- Structural signals in Mani's replies: no question and no buttons, internal words
  (`nearest fit`, `cooldown`, `[ctx]`), the same opener twice in a row, very short or very long replies.
- Gaps that show up as missing links: chat calls with no `message_id` were redrafts whose cost row never
  reached the stored reply (13 of 108).
- Time around an odd row: a call recorded at 675s against a 60s timeout, with nothing else in the window,
  said more than its own row did.

Read an actual conversation only when it is yours (the local dev thread) or you were handed it.

## 2. Reproduce one turn, then count

`backend/scripts/replay_turn.py` seeds a thread with a scenario's history and framework state, sends one
message to the real model, and prints each reply. Scenarios live in `replay_scenarios.json`; add one by
copying a real conversation's messages and the state it was in.

- Run at least three times. One reply is noise. The same prompt supplied a belief in 2 of 3 tries and
  0 of 3 the next time.
- Read every reply when the number is small. The pattern that counts "supplies an answer" missed one that
  was plainly a suggestion.
- `--override module.NAME=value` swaps a constant for one run, so a wording is compared with and without
  itself on the same scenarios.
- It makes paid calls and removes its own users and cost rows. Use the local database.

## 3. Measure what you might have broken, not only what you meant to fix

The "not sure" rule fixed the belief stage and quietly displaced the client's own dispute line, which the
model had been using. Scenarios for the neighbours caught it: the dispute stage's own line, and the
activate stage where a confirm is allowed. Adopt a wording only when the target moved and the neighbours
did not.

## 4. Verify an audit's claims before cutting

A first audit called a column dead, another "read by nothing", and a third "designed, not built" when a
later decision had already ruled the design out. Before acting on any "unused": grep real SQL not the
name, ask live data whether anything ever wrote a value, and read the decisions in force for a
contradiction. A column called `vague_streak` was waiting on a design the 2026-10-09 "no phrase lists
judge the conversation" decision had superseded.

## 5. Habits that held

- A regression test that fails against the old code comes first. Record the failure.
- Cap a timeout by total time as well as silence; the SDK's one is per read.
- Seed test threads through the pool's own codec, and pass a list, not `json.dumps(...)`.
- Check hosted is untouched at the end of any session that touched a migration.

Related: [[replaying-one-turn-against-the-real-model-2026-10-11]], [[measure-before-tuning-prompts]],
[[disarm-where-text-enters-the-prompt-2026-10-11]], [[stages-are-skipped-not-confirmed-2026-10-09]].
