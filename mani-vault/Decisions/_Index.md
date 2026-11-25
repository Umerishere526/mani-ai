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
| 002 | [[ADR-002-one-model-call-per-chat-turn]] | accepted, holds | amended by 006, since reversed | `backend/mani/chat/turn.py`, `chat/runner.py`, `tests/integration/test_turn.py` (the one-call turn, 2026-11-17) |
| 003 | [[ADR-003-mobile-design-token-architecture]] | accepted | | `mobile/src/global.css` |
| 004 | [[ADR-004-web-admin-styling-tailwind-only]] | accepted | | `web/app/globals.css` |
| 005 | [[ADR-005-per-person-memory-across-conversations]] | reversed | by "Memory: none across chats" (PORT-STATUS); migration `041` dropped `admin.user_memory` (2026-11-18) | removed |
| 006 | [[ADR-006-a-turn-may-be-redrafted-once]] | reversed | the redraft loop was removed on 2026-10-12 | removed |
| 007 | [[ADR-007-offers-follow-confidence-and-the-closest-fit-is-owed]] | reversed | by PORT-STATUS "When to offer a set is the model's judgment" (2026-11-17), with the floor `decide.OFFER_FROM_MESSAGE` | removed |
| 008 | [[ADR-008-every-reply-before-an-offer-asks-a-question]] | reversed | by PORT-STATUS "a reply asks one question when it helps" (2026-11-17, the question field 2026-11-24) | removed |
| 009 | [[ADR-009-where-knowledge-lives]] | accepted | supersedes 001 | `CLAUDE.md`, this vault |
| 010 | [[ADR-010-a-person-in-panic-is-guided-not-quizzed]] | retired | the code it names (`context.build`, `repairs.apply`) was deleted with the one-call turn, 2026-11-17 | removed |
| 011 | [[ADR-011-first-stage-by-its-own-test-and-one-draft-when-asked-to-pick]] | retired | the code it names (`context.build`, `redraft.repeats`) was deleted, 2026-11-17; `behavioral_activation.md` is paused | removed |
| 012 | [[ADR-012-prompts-are-structured-rules-and-frameworks-carry-their-own]] | superseded | by the one prompt `content/prompts/mani.md`, which replaced `mani_base`, `response_format` and the style prompts (2026-11-17; PORT-STATUS "Retired 2026-11-17: one home per rule") | `content/prompts/mani.md` |

ADR files 001 to 011 were deleted from the vault on 2026-10-07 (commit `e16c59f`); their links do not resolve, and
their text is in git history. Only ADR-012 remains as a file. Statuses above were checked against
`backend/PORT-STATUS.md` on 2026-11-25; 003 and 004 were not re-checked.

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
| ~~The deterministic safety screen is the only thing that locks a thread~~ Reversed: the screen was deleted 2026-11-17, and danger that continues with nothing in place pauses the chat | PORT-STATUS, the safety entry and "Also settled" |
| ~~Framework routing is in process phrase matching~~ Reversed: `router.py` is gone and the model chooses the framework (2026-11-17) | PORT-STATUS, "Also settled" |
| ~~Six repair checks are code~~ Reversed: the one repair left is replacing dashes; every other word goes out as the model wrote it (2026-11-17) | `backend/mani/chat/repairs.py`, PORT-STATUS |
| Mani's text is not streamed to the person; the provider call is | PORT-STATUS |
| ~~One scoped second call at the end of a framework to pick an exercise~~ Reversed: deleted with the 2026-10-02 flow | PORT-STATUS |
| No exercise hand-off on a crisis turn | PORT-STATUS, awaiting muhammad |
| `llm_calls` and `crisis_events` are written from the first day | PORT-STATUS |
| The grief veto: Behavioral Activation is not offered after loss words (`never_offer_when_said`); moot while Behavioral Activation is paused | `content/frameworks/paused/behavioral_activation.md` |
