---
type: journal
date: 2026-10-02
tags: [journal, tests, exercises, lessons]
---

# Seeded content turns dormant code paths live in tests

Lessons from shipping the library audio.

## The integration tests share the dev database, so seeding changes what they exercise

Once the 18 library exercises were seeded, every test that finished a framework reached the
exercise pick. Before, the pick only ran for exercises linked to the finished framework, and only
fixtures that also stubbed the chooser ever inserted one. The `model` fixture scripts only the chat
call, so four tests made **real, paid OpenRouter calls**.

The suite still passed. What gave it away was `filterwarnings = error` reporting an unclosed socket on
a LAN address rather than loopback. The fix is an autouse `no_real_exercise_call` fixture in
`test_turn.py`.

**How to apply:**
- When seeding content makes a code path reachable, grep the tests for every way into that path.
- An unclosed socket whose `laddr` isn't `127.0.0.1` means a test is reaching the internet.
  Run that file with `-o log_cli=true -o log_cli_level=INFO` and look for `httpx` request lines.

## Two more ways tests depend on the shared dev database

- A test asserted that one user appeared among the first 100 returned by an unordered `limit 100`.
  Eval runs leave an `@eval.mani.local` user behind every time, and once there were 172 the test
  failed. Never assume the shared database is small.
- Content-driven tests fail when the database was seeded from older `content/`. Re-run
  `scripts/seed.py` before believing such a failure.

## Supabase Free limits

50 MB is the cap **per file**, and total storage is 1 GB (checked on supabase.com, 2026-10-02). muhammad
read the 50 MB as a total. The audio was compressed anyway (64 kbps mono, approved by a listen test),
for streaming speed and repo size.
