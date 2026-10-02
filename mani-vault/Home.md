---
type: index
tags: [index]
---

# mani

Project vault for the `mani` codebase: a Next.js web app, an Expo mobile app, a FastAPI backend and a
Streamlit chat tester, in one repository.

**Building Mani itself?** Read, in order: `CLAUDE.md`, the `.claude/` file for the app you are in,
`backend/PORT-STATUS.md` (what the service does today and what is open), then [[Decisions/_Index|the
decisions index]] for why. This page maps the vault.

## Map

| Folder | Holds |
|--------|-------|
| `Decisions/` | Architecture decision records, with [[Decisions/_Index|an index]] of status and what implements each |
| [[Journal]] | Claude's engineering notes: insights, failed approaches, preferences, and history moved out of other documents |
| `Programme/` | Planning history from before the port. **Historical: evidence, not instructions.** `Programme/archive/` is older still |
| `Reference/` | Pointer notes to `.claude/` and `backend/`; no facts are copied here |
| `Templates/` | Decision, Journal, Feature and Daily note templates (the last two are unused) |

## Source of truth

One home per kind of fact, set by [[ADR-009-where-knowledge-lives]]:

| Kind of fact | Its home |
|---|---|
| Stack facts, commands, layout, rules | `CLAUDE.md` and `.claude/*.md` |
| What the backend does today, what is open | `backend/PORT-STATUS.md` |
| Why we decided something | `Decisions/` |
| Lessons and failed approaches | `Journal/` |
| The client's specifications | `backend/docs/specs/` |

Notes here **link to** those, never copy them. If a fact appears in both places the home wins.

## Apps

[[Web]] · [[Mobile]] · [[Backend]] · [[Supabase]] (pointer notes)

## Conventions

- One idea per note. Link with `[[wikilinks]]`; an unresolved link is a note worth writing later.
- Frontmatter `type:` and `tags:` on every note. A note that is history says `status: historical` and
  points at what is current.
- ADRs are numbered and immutable once accepted; only the status line changes. A change of mind is a new
  ADR, and every ADR goes in the index.
