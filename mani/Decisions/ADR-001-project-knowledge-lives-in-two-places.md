---
type: decision
status: accepted
date: 2026-09-11
apps: [web, mobile, backend]
tags: [decision, tooling]
---

# ADR-001: Project knowledge lives in `.claude/`, project thinking lives in the vault

**Status:** accepted
**Affects:** all

## Context

The project accumulated two places notes could live: `.claude/` at the repo root (machine-readable context Claude loads automatically) and this Obsidian vault. The root CLAUDE.md also mandated a `./journal/` directory that was never created.

Three locations for overlapping content meant no location would be reliably searched — the CLAUDE.md rule instructs Claude to search past notes before complex tasks, and a split store degrades that silently.

## Options considered

### Option A — vault and `./journal/` separate
- Pros: machine notes stay out of a personal vault; easier to commit alongside code later
- Cons: two stores to search, the journal rule degrades, Obsidian's backlinks and graph get a fraction of the content

### Option B — vault replaces `./journal/`
- Pros: one searchable store; Claude's notes gain wikilinks to the decisions and features they relate to; nothing to migrate since `./journal/` was never created
- Cons: machine-written notes sit alongside human ones; awkward if engineering notes should later be committed with the code

## Decision

The vault replaces `./journal/`. Claude's notes go to `mani/Journal/`, kept in their own folder so they stay visually separate from hand-written notes. The root CLAUDE.md journal rules were updated to point there.

Stack facts stay in `.claude/` as the single source of truth. Vault notes **link** to those files rather than copying them.

## Consequences

- One place to search for past context; the CLAUDE.md journal rule works as intended
- `.claude/` stays the machine-readable layer — Claude loads it automatically, so it must not drift
- Duplicating a stack fact into the vault creates drift; if it appears in both, the `.claude/` copy wins
- The project root is not a git repository, so vault notes are unversioned. If engineering notes ever need version control, this decision needs revisiting

## Links

- [[Home]]
- [[Journal]]
