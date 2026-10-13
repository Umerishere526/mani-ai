---
type: journal
date: 2026-10-13
tags: [journal, prompts, questions, memory, lessons]
---

# A running understanding and one question rule (2026-10-13)

Spec 0005, scope feature 19. Built with a scripted model; the live run is owed (muhammad's yes).

## Why

muhammad's Directive tester run (thread 4ec47e15): the person opened "i am frustrated". After two
questions Mani followed ABCDE's checklist (`to_find_out`, shown as "Finding the fit") and offered
with their judgment of the client in the slot instead of their feeling. Two causes: the checklist
steered the questions toward ABCDE's needs, and the bans ("never hand their own words or feelings
back", "Am I saying back their own words or feelings") kept the feeling out of every question. The
feeling was said once and then nothing held it.

## What changed

- Code keeps `threads.understanding` (`feeling`, `issue`), merged from `understanding_update` in
  every reply shape and sent back as `understanding:` in `[ctx]` (`mani/chat/understanding.py`).
  It replaces `thread_summaries.current_issue` and spec 0004's yes turn `feeling`.
- One positive rule in `mani_base.md` `rules` replaces the checklist and the three bans. Fewer words
  than before (2386 to 2371 across `mani_base.md` and `response_format.md`).
- The offer slot names its source: the stored feeling, their worry only when they named none.

## Gotchas

- A Pydantic model's docstring is sent to the model as the schema description. Keep it in plain
  words; put code pointers in a `#` comment above the class.
- `context.py` renders the line and `understanding.py` needs `context.disarm`: both use
  `from mani.chat import x` and resolve at call time, so the import cycle is harmless in either order.
- The paused frameworks still carry `to_find_out`. Their data was kept (it holds clinical
  distinctions such as "whether anyone is at risk (then safety, not this)"); only the comments that
  said the prompt reads it were corrected. If one comes back, decide then whether that data has a home.
- Migration numbers 019 to 022 on this branch differ from the `feat/*` branches, which hold their own
  019 to 026. Main has only 001 to 010. See [[switching-branch-leaves-the-database-ahead-2026-10-09]].

## Still to learn

Whether the prompt cuts alone fixed the frustrated chat. If the live run shows that, say so here;
the record stays anyway, for R6 past the window and for A's slot.

See [[abcde-walk-owned-by-code-2026-10-13]], [[restating-is-not-reflecting-2026-10-12]],
[[general-judgment-over-case-patches-2026-10-12]].
