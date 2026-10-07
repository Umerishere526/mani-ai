---
type: journal
date: 2026-10-04
tags: [journal, workflow, preference]
---

# Claude marks a feature done when verify and test pass

muhammad's standing instruction, given 2026-10-04 while row 33 waited in `in-progress`: once `/check verify` and `/test`
have both passed for a scope feature, Claude marks it `done` itself (At a glance table, heading, and the governing
spec's status line from `In Progress` to `Accepted`) and says so in its report. It does not wait to be asked.

It covers the marking only. If an acceptance criterion is open, the checks have not passed, and the feature stays
`in-progress` with the blocker named.

Row 33 ([[natural-mani-build-2026-10-04]]) is not there yet: verify and test have not run, and AC-9 and part of AC-7
are open until `/architect` amends them.
