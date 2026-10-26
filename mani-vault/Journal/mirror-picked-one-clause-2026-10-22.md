---
type: journal
date: 2026-10-22
tags: [journal, prompts, mirror, understanding, lessons]
---

> Superseded 2026-10-25 (the core issue asked as what happens because of the problem, and the oldest entry dropped first) - see [[core-issue-was-situation-2026-10-25]].

# The mirror picked one clause and dropped the headline (2026-10-22)

muhammad's Directive chat (boss put in charge by his father, does no work, team carries it). The first message
ended "lack of leadership and i do not know what to do". Mani said back "You and the team work long days, but your
boss doesn't seem to understand the work you show him" and asked "What is that causing for you most directly?"
with options of its own guesses (extra work, stalled decisions, work not recognized). muhammad: "you missed the
point". The chat never recovered. His verdict: the problem Mani identified was completely wrong; it must read the
whole message, not the first thing it picks up, and be with the person.

## Cause (hypothesis, not measured)

Three places said to select: the mirror rule ("what matters", "never hand their whole message back"), the problem
step ("who, what, how often"), and the core issue step's three question shapes ("what falls on them" gives
"extra work"). With a long message nothing says what to keep, so the model keeps the last concrete clause, and that
becomes the stored problem the rest builds on. Same family as [[direct-questions-have-no-target-2026-10-09]].

## Change

Cut and replaced, no rules added: the mirror says back what runs through the whole message with the name they gave
the problem; the first reasoning step reads the message whole; the core issue question is about what happens because
of the problem as they named it. Edited in `mani_base.md`, `response_format.md`, `context.py` and `schema.py`.
`mani_base.md` grew 45 characters (11017 to 11062, limit 11268), so "flat or down" was not met.

## Second change: the case grows and is never frozen

The same chat showed the other half: the person kept adding (he takes credit, his father will not listen, the pay is
low, they do the work of two) and Mani never held it, because once an offer was open the problem, core issue and
underlying feeling were frozen and new things went only into `also`. They now gather like `feeling` does: each new
entry is added after the stored ones, none twice, nothing replaced (`understanding.GATHERED`, 600 characters each, the
oldest entry goes only past that), in a framework too, and the check no longer writes its sentences over them.
`[ctx]` already rendered them every turn, so the model sees the whole picture and builds its questions on it. The
freeze was made so a detail could not replace the problem; add-only makes that impossible without freezing.
Watch: near-duplicate entries are caught only when identical, and a longer record may lengthen the check.

## Still to learn

Replay that turn with the real history and `AI_DEBUG_MODE=true`, 3 runs, Directive, to read the reasoning (cents;
needs muhammad's yes). All 526 tests pass (unit and integration, scripted model).

See [[measure-before-tuning-prompts]], [[restating-is-not-reflecting-2026-10-12]].
