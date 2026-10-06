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
| 002 | [[ADR-002-one-model-call-per-chat-turn]] | accepted | amended by 006 | `backend/mani/chat/orchestrator.py`, `tests/integration/test_turn.py` |
| 003 | [[ADR-003-mobile-design-token-architecture]] | accepted | | `mobile/src/global.css` |
| 004 | [[ADR-004-web-admin-styling-tailwind-only]] | accepted | | `web/app/globals.css` |
| 005 | [[ADR-005-per-person-memory-across-conversations]] | accepted | | `backend/mani/memory.py`, migration `009`, `scripts/fold_idle_threads.py` |
| 006 | [[ADR-006-a-turn-may-be-redrafted-once]] | accepted | amends 002; amended by 007 and 008 | `backend/mani/chat/redraft.py`, `orchestrator.py` |
| 007 | [[ADR-007-offers-follow-confidence-and-the-closest-fit-is-owed]] | accepted | replaces the 2026-09-24 offer cadence; amends 006; its owed closest fit superseded by 014 once accepted | `backend/mani/chat/context.py` |
| 008 | [[ADR-008-every-reply-before-an-offer-asks-a-question]] | accepted | amends 006 | `redraft.py` (`needs_question`), `context.classify_reply` |
| 009 | [[ADR-009-where-knowledge-lives]] | accepted | supersedes 001 | `CLAUDE.md`, this vault |
| 010 | [[ADR-010-a-person-in-panic-is-guided-not-quizzed]] | accepted | adds to 007 and 008; amended by 011 | `context.build`, `repairs.apply`, `structured_problem_solving.md` |
| 011 | [[ADR-011-first-stage-by-its-own-test-and-one-draft-when-asked-to-pick]] | accepted | amends 010 and 006 | `context.build`, `redraft.repeats`, `behavioral_activation.md` |
| 012 | [[ADR-012-mani-speaks-plainly-and-tone-is-the-prompts-job]] | accepted | supersedes 008; amends 006 and 011 | `context.build` (`short`, `answering`), `redraft.py`, `content/prompts/mani_base.md` |
| 013 | [[ADR-013-a-framework-stage-moves-on-after-one-answer]] | accepted | amends 010 and 011 | `context.build`, `repairs.apply`, `techniques.py`, the six framework files, `mani_base.md` |
| 014 | [[ADR-014-a-framework-is-offered-only-when-the-facts-fit]] | proposed | supersedes 007's owed closest fit | `router.py`, `redraft.py`, `orchestrator.py`, `Reply.facts`, the six framework files |
| 015 | [[ADR-015-what-the-person-said-before-accepting-is-not-asked-again]] | accepted | amends 013 and 012 | `techniques.covered_stages`, `context.py`, `repairs.apply`, `redraft.py`, migration `012`, the six framework files |
| 016 | [[ADR-016-a-framework-ends-with-a-conclusion-and-the-body-check]] | proposed | amends 013 | `context.py`, `repairs.with_the_check_in`, `somatic.md`, `mani_base.md`, the six framework files |
| 017 | [[ADR-017-questions-are-asked-plainly]] | proposed | amends 015 and 012 | `context.py` (stage notes), `mani_base.md`, `response_format.md`, `somatic.md`, `validators.question_findings`, `client_style_counts.py` |
| 018 | [[ADR-018-a-stuck-person-is-offered-abcde]] | proposed | amends 014 and 017 | `router.py` (`stuck`, `stuck_route`), `techniques.passed_over_stages`, `context.py`, `orchestrator.stuck_offer_candidate`, `redraft.py`, `abcde.md`, `mani_base.md` |

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
| Six repair checks are code, not model calls | `backend/mani/chat/repairs.py` |
| No streaming in version one | PORT-STATUS |
| One scoped second call at the end of a framework to pick an exercise | PORT-STATUS |
| No exercise hand-off on a crisis turn | PORT-STATUS, awaiting muhammad |
| `llm_calls` and `crisis_events` are written from the first day | PORT-STATUS |
| The grief veto: Behavioral Activation is not offered after loss words (`never_offer_when_said`), kept as built | [[ADR-006-a-turn-may-be-redrafted-once]] |
