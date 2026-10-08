---
type: journal
date: 2026-10-07
tags: [journal, chat, lesson]
---

# Repairs guarded state by accident

Found while designing spec 0006 (one model call, no repairs), by the cross check rather than by me.

Some of `repairs.apply`'s "offer timing" drops were doing a second job nobody wrote down. Dropping a technique button on the turn they said no, or on the turn a finished framework retires, also stopped `orchestrator.send` from writing a fresh OFFERED row (the `new_offer` branch runs before the decline and retire branch) over the decline or the retirement. Dropping buttons outside an offer also stopped a stray library button from setting `library_offered` and silencing `library_pending`.

So removing a reply edit can remove a state guard. Before deleting any check that drops a button or a field, trace what the orchestrator writes from that value after the check. Spec 0006 keeps those as explicit state guards (AC-4).

Related: [[client-lines-the-code-matches-exactly]], [[measure-before-tuning-prompts]]
