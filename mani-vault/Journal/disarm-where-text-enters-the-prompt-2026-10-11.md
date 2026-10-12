---
type: journal
date: 2026-10-11
apps: [backend, chat-tester]
tags: [journal, backend, security, refactoring, audit]
---

# Guard where text enters the prompt, and verify an audit's claims before cutting

## The bug: three of four transcript builders disarmed `[ctx]`

`context.disarm` rewrites a person's typed `[ctx]` / `[/ctx]` to `(ctx)` so the model never reads it as
backend metadata. It was called by `orchestrator._conversation`, the per-turn prefix and
`memory._transcript`. `summarize.transcript` was the fourth builder and did not call it.

The path from there to the system prompt is the part worth remembering. The summary is **written by the
model**, stored, and `composer.summary_layer` pastes it into the system prompt of every later turn in that
thread. So an injected block could rewrite one conversation's style, cooldown and safety lines permanently,
and it survived restarts because it was stored. Disarming the input alone cannot close that: the model can
emit a marker the person never typed. The guard now also runs where stored text enters the prompt
(`summary_layer`, `user_memory`), so a missed call site upstream stops mattering.

A guard that each caller must remember will eventually be forgotten by one. Put it at the boundary the
text crosses, not at the places that happen to feed it.

Exposure was checked before fixing, on both databases: no `[ctx]` marker in any message, summary or memory
row (hosted: 254 messages, 2 summaries, 4 memory rows). Nothing had been exploited, so no backfill was needed.
Check stored data before assuming a fix needs a data repair, and before assuming it does not.

## The duplicate-send path

`create_message_pair` on a repeated message id writes nothing and returns the *stored* reply's id. The
orchestrator then returned the freshly generated text and buttons beside that id and went on to apply the
draft's state. The person saw buttons that did not exist in the database. Reached only when the pre-check
loses a race the advisory lock is meant to prevent, so the test makes the pre-check miss once on purpose.
The fix reads the stored turn back through the same helper the pre-check uses.

## Traps found while removing duplication

Each of these looked like an obvious duplicate in the audit and was not.

- `running_framework` and `active_framework` in `send()` were identical, but a third copy further down must
  stay: `technique` is rebound in between (the "they asked for the one they declined" branch), so the earlier
  variable would be `None` exactly there.
- `redraft.ruled_out` runs once per draft and once more for `repairs.apply`, but on different reply objects:
  the prompts are rewritten between the two. They are not one computation.
- `chain.build` and `build_tool_choice` share ten lines of setup and nothing else. Their docstring argues
  against merging them, and it is right. Extracting the setup added lines rather than removing them.
- Routing `transcribe_audio` through the shared request method needs that method to stop forcing
  `Content-Type: application/json`, or the multipart boundary is lost.
- `PERMISSION_QUESTIONS` has three identical values today, but the paused frameworks were specified with
  different wording per style. Collapsing it would be undone on resume.

## An audit is a list of claims

The first audit said a column was dead because grepping its name found nothing, and missed four more because
common words (`voice`, `resolution`) match comments. It called a column "read by nothing" when it was seeded
for every framework. It said two functions differed in one line when they differ in four. It called a column
abandoned when `PORT-STATUS.md` says it is designed and not built. Each was caught by reading the code or
querying the live database, not by trusting the previous pass.

For columns: check real SQL, not the name, and ask the live data whether anything ever wrote a value.

Related: [[reverting-code-does-not-revert-the-database]], [[duplicate-migration-versions-after-merge-2026-10-06]],
[[switching-branch-leaves-the-database-ahead-2026-10-09]], [[seeded-content-turns-dormant-paths-live-in-tests]].
