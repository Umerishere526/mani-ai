---
type: index
tags: [index]
---

# mani

Project vault for the `mani` codebase — three apps in one directory: a Next.js web app, an Expo mobile app, and a FastAPI backend.

## Map

| Folder | Holds |
|--------|-------|
| [[Journal]] | Claude's engineering notes — insights, failed approaches, preferences |
| `Decisions/` | Architecture decision records (ADRs) |
| `Features/` | Feature specs, written before building |
| `Reference/` | Stack facts, data models, environment, endpoints |
| `Daily/` | Dev log, one note per day |
| `Templates/` | Note templates for the above |

## Apps

- [[Web]] — Next.js 16, App Router, Tailwind v4
- [[Mobile]] — Expo SDK 57, expo-router, NativeWind v5
- [[Backend]] — FastAPI, Python 3.14
- [[Supabase]] — database practices (not yet adopted)

## Source of truth

Machine-readable project context lives in `.claude/` at the repo root, **not** here:

- `.claude/WEB.md`, `.claude/MOBILE.md`, `.claude/BACKEND.md`, `.claude/SUPABASE.md`
- `.claude/skills/` — coding standards Claude loads automatically

Notes in this vault **link to** those files rather than copying them. If a stack fact appears in both places it will drift; keep it in `.claude/` and reference it here.

## Conventions

- One idea per note. Link liberally with `[[wikilinks]]` — an unresolved link is a note worth writing later, not an error.
- Frontmatter `type:` and `tags:` on every note so the tag pane and search stay useful.
- ADRs are numbered and immutable once accepted. To change one, write a new ADR that supersedes it.
