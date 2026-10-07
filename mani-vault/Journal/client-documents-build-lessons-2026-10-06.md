---
type: journal
date: 2026-10-06
tags: [journal, backend, tests, lessons]
---

# Building spec 0010: what bit, and what to remember

The build that took the conversation layer back to the client's documents ([[ADR-019-mani-follows-the-clients-documents]]). Lessons worth keeping.

- **`Reply` ignores unknown fields.** `extra="ignore"` on the schema means a test that still passes `Reply(facts=...)` after `facts` was removed runs green and tests nothing. When a field goes, grep the tests for it; the cross check flagged this before the build.
- **A test helper that only bumps `message_count` is not history.** `past_the_opening` raised the counter, but the first message refusal counts the person's real messages, so every test using it read as a first message. It now writes one real exchange. Counts and history can disagree; the code reads history.
- **The retire turn has no framework in `[ctx]`.** The framework is retired before the context is built, so anything the model must report on that turn (`felt_after`) has to be a top level field with its own `[ctx]` line (`answering_practice`), not inside `state`.
- **`test_db.sh` had a race, now fixed.** The Postgres image runs a temporary server on the socket for its init scripts and then restarts; a socket probe could pass just before the restart. The probe now uses TCP. It failed once in four runs before the fix.
- **New public tables need `revoke all ... from anon, authenticated`.** Supabase's default privileges grant them REFERENCES, TRIGGER and TRUNCATE; migration 001 revoked those for its own tables, and a later table must do the same.
- **Multi line signatures break a `(?=^\S)` block regex.** A test whose `def` spans lines ends its match at `):`. Delete such blocks by name and re-run the file before trusting the edit.

Still open: muhammad's three live conversations in chat-tester (spec 0010, AC-14), read against Lolly's nine points with `admin.llm_calls.decision` and `public.framework_outcomes`.

Related: [[stuck-yes-dropped-and-say-back-lost-2026-10-06]], [[measure-before-tuning-prompts]].
