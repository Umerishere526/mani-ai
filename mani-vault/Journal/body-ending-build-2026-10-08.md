---
type: journal
date: 2026-10-08
tags: [journal, ending, tests, build, gotcha]
---

# Building spec 0009: the body ending as rules

Design notes are in [[body-ending-design-2026-10-08]]. These are what the build added.

## A guard test can hide behind the guard before it

The first test for "a kept `ending` drops a technique button" set `framework_running=True`, so the older running guard dropped the button and the retire guard never ran. It passed. Setting `framework_running=False` isolated it, and switching `retiring = retiring or ending is not None` off turned it red. Same lesson as [[guard-test-passed-without-its-guard-2026-10-07]]: mutation check every guard test.

Mutation checks run this build, each red when the line was switched off and green when restored: the retirement precedence over the state branches, the crisis retire, the cap threshold, the concern clearing `ending`, and the retire guard in `guards.check`.

## My own test asserted a forward move could end the framework

I wrote "a choice wins over the stage the same reply reports" with a stored `somatic_checkin` and a reply reporting `somatic_practice`. That is a forward move, so the guard correctly drops `ending`. The real precedence case holds the stage (stored and reported both `somatic_practice`). When a test fails right after writing the guard it tests, check the test before the code.

## Order the checks so the state is clamped before `ending` reads it

The forward move rule needs the clamped phase, so the `state` block in `guards.check` moved above the buttons loop. Nothing else read the order.

## The cap counter is set on the first ending reply, carried afterwards

`ending_from` is `count_after` on the first reply recorded in an ending phase, carried from the stored row on every later write, and cleared only by the retire update. A step back to `closing` keeps it, so the model cannot restart the cap by stepping back and forth. The upsert writes `excluded.ending_from`, so every code path that builds a `TechniqueState` must carry it or it is silently nulled.

## Left for muhammad

- The `ending` wording in `mani_base.md` is the spec's draft, unchanged. It is not reseeded: until it is, the database still serves the old two line `ending` section and the old `response_format.md`, so the running app would ask for the body check the old way while the code ignores stage blocks.
- `.claude/BACKEND.md` still names `ending.py` and `somatic.md`. The spec leaves that to `/sync`.

Related: [[repairs-guarded-state-by-accident]], [[seeded-content-turns-dormant-paths-live-in-tests]]
