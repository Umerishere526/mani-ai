---
type: journal
date: 2026-10-01
tags: [journal, documentation, lessons]
---

# Documentation drift: what an audit found and the rule it produced

Four read only audits compared every project document with the code on 2026-10-01 (CLAUDE.md and
`.claude/`, `backend/PORT-STATUS.md`, `backend/docs/` and the chat tester README, and this vault). They
found about thirty stale statements. The rule that came out of it is the "Where each kind of fact lives" table in the root `CLAUDE.md`.

## What went wrong, in order of how much it could mislead a decision

- A skill told Claude "nothing in this repo uses Supabase or Postgres" and to stop and ask before touching
  a database the backend runs on. A vault reference note said the same.
- A note labelled "read this first" described a tRPC and Next.js backend that was never built, and the safety
  section of the status file said the screen misses phrases it had caught for a week.
- Ports in three places said 5434x; the running containers answer on 54321 to 54324.
- The status file kept its own history (about 310 lines) beside its current state, so its own sections
  contradicted each other on the call count, the offer cadence and safety.

## Why it happened

Nothing said who owns each kind of fact, which documents were history, or where a decision's status lives.
Docs were updated when a change was remembered, not when it made a sentence false.

## How to repeat the audit

Compare each home against the code, not against other docs: read the claim, then check the file, command,
port, count or table it names. Four agents in parallel, each given one group of documents and told to verify
and not to edit, took about two minutes; verify their highest stakes findings yourself before acting. Run it
before a release.

## Things worth remembering

- An archived note that says "current instructions are in X" breaks when X is archived; update the pointer
  in the same move.
- Moving a note in Obsidian keeps wikilinks working because they resolve by name; paths in prose do not.
- A counter that says "14 tables" is stale the day a migration lands; say how to count, or generate it.
- The chat tester was missing from CLAUDE.md for weeks because it is "not part of" any app: say what a
  folder is for even when it is a tool.
