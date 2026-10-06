---
type: index
tags: [index, decision]
---

# Decisions

One row per ADR. Status changes only here and in the ADR's own status line. How the ADRs work and where
other knowledge lives: [[ADR-009-where-knowledge-lives]].

| # | Decision | Status | Amends or superseded by | Implemented in |
|---|---|---|---|---|
| 001 | [[ADR-001-project-knowledge-lives-in-two-places]] | superseded | by 009 | n/a |
| 002 | [[ADR-002-one-model-call-per-chat-turn]] | accepted | | `backend/mani/chat/orchestrator.py`, `tests/integration/test_turn.py` |
| 003 | [[ADR-003-mobile-design-token-architecture]] | accepted | | `mobile/src/global.css` |
| 004 | [[ADR-004-web-admin-styling-tailwind-only]] | accepted | | `web/app/globals.css` |
| 005 | [[ADR-005-per-person-memory-across-conversations]] | accepted | | `backend/mani/memory.py`, migration `009`, `scripts/fold_idle_threads.py` |
| 009 | [[ADR-009-where-knowledge-lives]] | accepted | supersedes 001 | `CLAUDE.md`, this vault |
| 010 | [[ADR-010-a-person-in-panic-is-guided-not-quizzed]] | accepted | amended by 019 | `context.build`, `dbt_stop.md`, `structured_problem_solving.md` |
| 018 | [[ADR-018-a-stuck-person-is-offered-abcde]] | proposed | amended by 019 | `router.stuck_framework`, `orchestrator.stuck_offer_candidate`, `context.py`, `abcde.md` (`stuck_offer`), `mani_base.md` |
| 019 | [[ADR-019-mani-follows-the-clients-documents]] | proposed | deletes 006, 007, 008, 011 to 017 | the prompts, `context.py`, `repairs.py`, `router.py`, `techniques.py`, `orchestrator.py`, migrations `013` to `015`, spec 0010 |

## In force, recorded elsewhere, no ADR yet

Decisions that `backend/PORT-STATUS.md` or `.claude/` treat as settled. Each needs an ADR if it is ever
questioned; until then the source named here is the record.

| Decision | Recorded in |
|---|---|
| OpenRouter is the only model provider; LangChain composes the call; the key stays in the environment | `.claude/BACKEND.md`, PORT-STATUS |
| Postgres is reached with `asyncpg`, not PostgREST, because a turn needs one transaction | `.claude/BACKEND.md` |
| Two schemas: `public` (user data, RLS) and `admin` (config and analytics, never exposed to the Data API) | `.claude/SUPABASE.md` |
| Ordinary traffic runs as `mani_service`, a member of `authenticated`, so RLS applies to real requests; never granted to `authenticator` | `.claude/SUPABASE.md` |
| Three writes are security definer functions, not grants: `create_message_pair`, `create_greeting`, `mark_thread_crisis` | `.claude/SUPABASE.md` |
| The deterministic safety screen is the only thing that locks a thread; the model's crisis flag never locks | `backend/mani/chat/safety.py`, commit `541b2f9` |
| Structural repairs are code, not model calls; no code enforces tone | `backend/mani/chat/repairs.py`, [[ADR-019-mani-follows-the-clients-documents]] |
| No streaming in version one | PORT-STATUS |
| One scoped second call at the end of a framework to pick an exercise | PORT-STATUS |
| No exercise hand-off on a crisis turn | PORT-STATUS, awaiting muhammad |
| `llm_calls` and `crisis_events` are written from the first day | PORT-STATUS |
| The grief veto: Behavioral Activation is not offered after loss words (`never_offer_when_said`), kept as built | [[ADR-019-mani-follows-the-clients-documents]], `router.vetoes` |
