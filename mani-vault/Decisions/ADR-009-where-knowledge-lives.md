---
type: decision
status: accepted
date: 2026-10-01
apps: [all]
tags: [decision, tooling, documentation]
---

# ADR-009: Where knowledge lives

**Status:** accepted by muhammad, 2026-10-01. Supersedes [[ADR-001-project-knowledge-lives-in-two-places]].
**Affects:** all

## Context

ADR-001 split knowledge in two: stack facts in `.claude/`, project thinking in the vault. It was right
and it was not enough. Since then the vault was renamed `mani-vault/` and is tracked in the repo's one
git repository; docs also grew in `backend/` (`PORT-STATUS.md`, `docs/specs/`); and planning notes from
before the port kept saying "read this first" while describing a system that was never built.

A documentation audit on 2026-10-01 found about thirty stale statements across CLAUDE.md, `.claude/`,
`PORT-STATUS.md`, `backend/docs/` and the vault. The worst were ones that mislead a decision: a skill
telling Claude that no database exists, a vault reference note saying "Supabase not adopted", a "start
here" note describing a tRPC backend, and a status file saying the safety screen misses phrases it has
caught for a week. The cause was not carelessness. Nothing said who owns each kind of fact, what counts
as current versus history, or where a decision's status lives.

## Options considered

### Option A — keep ADR-001 and fix the stale text once
- Pros: no new rule.
- Cons: it drifts again; the same audit would be needed in a month.

### Option B — one home per kind of fact, history marked as history, every decision indexed
- Pros: a reader knows where to look and which statements to trust; a change has one place to update.
- Cons: discipline, since nothing enforces it.

### Option C — everything in the vault
- Pros: one place.
- Cons: `.claude/` is loaded automatically and `PORT-STATUS.md` sits beside the code it describes;
  moving them makes both less likely to be read when it matters.

## Decision

Option B.

| Kind of fact | Its one home |
|---|---|
| Stack facts, commands, layout, rules | `CLAUDE.md` and `.claude/*.md`; the only copy |
| What the backend does today, what is open | `backend/PORT-STATUS.md` |
| Why we decided something | `mani-vault/Decisions/`, listed in `_Index.md` |
| Lessons and failed approaches | `mani-vault/Journal/` |
| The client's specifications | `backend/docs/specs/` |
| History | `mani-vault/Programme/` and `Journal/`, marked `status: historical` with a banner |

Rules:

1. Elsewhere, link; never copy a fact from its home. If both exist, the home wins.
2. A document that is history says so in its frontmatter and its first lines, and points at the
   current source. A note that is not marked historical is claiming to be true.
3. A change that makes a document false updates that document in the same change. The CLAUDE.md rule
   for `PORT-STATUS.md` is the model.
4. ADRs are immutable once accepted. Only the status line changes, to record a supersession or an
   acceptance. A change of mind is a new ADR. Every ADR appears in `_Index.md` with what amends it and
   the code that implements it.
5. The vault is `mani-vault/` inside the repo; Claude's notes go in `mani-vault/Journal/`.
6. Before a release, compare each home against the code (the audit that produced this ADR is the
   checklist) and record what changed.

## Consequences

- Reading order for anyone, human or Claude: `CLAUDE.md`, the `.claude/` file for the app, `PORT-STATUS.md`,
  then `_Index.md` for why.
- Decisions that exist only as prose in `PORT-STATUS.md` or `.claude/SUPABASE.md` are listed at the foot of
  the index as "recorded elsewhere" until someone writes them up; none is lost, none is an ADR yet.
- ADR-001 stays as written with its status set to superseded.

## Links

- Supersedes: [[ADR-001-project-knowledge-lives-in-two-places]]
- Index: [[_Index]]
