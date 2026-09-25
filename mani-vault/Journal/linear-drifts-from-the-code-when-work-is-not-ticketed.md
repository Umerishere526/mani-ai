---
type: journal
date: 2026-09-24
apps: [backend, mobile]
tags: [journal, linear, process, testing]
---

# Linear drifts from the code when work is not ticketed as it lands

## What happened

muhammad asked for the work so far to be reconciled against the 30 Day Plan and the Complete
Backlog. Between 2026-09-19 and 2026-09-24, 14 commits and a merged PR (#4) landed with **no
ticket at all**. Reconstructing them from `git log` produced 18 Done tickets (MYM-130 to MYM-147).
Five open tickets turned out to be partly done and moved to Week 2, and one open ticket
(MYM-113) had been satisfied by Week 1 work and never closed.

## Insight

- **"Done" in Linear is a claim, not a fact.** MYM-28 was closed on 09-18 with "summarisation runs
  successfully in a fresh local setup", but no summary had ever succeeded (every call 404'd). MYM-126 was closed
  and then the feature was removed. Check the code before trusting a status. muhammad chose to
  leave such tickets Done, add a comment, and link a new ticket for the real work (MYM-139,
  MYM-134), so each week records what was believed at the time.
- **A green suite can hide a lost check.** `1c9b095` moved the backend to JWKS only, and four
  admin-auth tests in `test_endpoint_auth.py` quietly started skipping. The suite still reports
  517 passed, but nothing verifies admin-only over HTTP. This is exactly the "check the skip
  count" gotcha in `.claude/BACKEND.md`. Read the `-rs` output, not just the total. Tracked as
  MYM-149.
- **Match tickets by acceptance criteria, not by title.** MYM-25's title says rate limiting, and
  what landed is a daily cap that is off by default. MYM-113 asked for new tables, and the work landed as
  `jsonb` on `admin.frameworks`. Record the gap in a comment either way.
- muhammad's placement rule: work done goes to Week 2 of the 30 Day Plan, **except** work that
  actually happened in Week 1, which goes to Week 1.

## Applies to

Any future reconciliation, and every commit: ticket it when it lands. Regenerate
[[AUDIT-TICKET-MAP]] from Linear afterwards rather than editing it by hand.

## Links

- [[AUDIT-TICKET-MAP]]
- [[measure-before-tuning-prompts]]
- [[framework-endings-and-ignored-offers]]
