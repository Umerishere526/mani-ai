---
type: journal
date: 2026-10-12
tags: [journal, prompts, voice, stages, lessons]
---

# Stage questions are asked as written, not reworded (2026-10-12)

Inside ABCDE, stage B, Mani said: "You usually help, but they aren't available when you need
something. What do you find yourself telling yourself about that?" The client's question for B is
plain ("What did you start telling yourself about what was happening?"). The model blended it with
"you find yourself still scrolling" from the client's Reflective example. muhammad: replies must be
plain and simple, fixed for every reply, not by banning one phrase.

## Root cause

The prompt ordered the model to reword every stage question, in five places: "never send it bare"
(`_stage_note`), "never word for word" (`[ctx]` `active_framework`), "in your own tone" (twice), "so
it could only be asked of this person", and "do not reuse your own phrasing". At effort `low`,
rewording means inventing, and invented phrasing comes out stacked and literary.

"Never send it bare" came in on 2026-10-01 (b9c9ed6), when stage questions were generic. Since
2026-10-09 each stage `ask` is the client's own question in the chosen style, so the premise was
gone, and the rule contradicted the Decision in force "Stage questions keep the framework's own
wording".

## What changed

- `mani_base.md` `in_a_framework`: ask the model question as written; change only what it is about,
  in their words, or ask only the missing part.
- `context.py`: the rewording lines cut from `_stage_note`, `_WALK_THE_STAGES` and `active_framework`.
- `mani_base.md` `voice`: seven bullets to four, about 330 words to about 100. The old block was
  itself written in the register we wanted gone. "Do not reuse your own phrasing" cut; R3 stays
  covered by the client's line in each style file and `recent_openers`.
- Net: `mani_base.md` went from 2846 to about 2640 words. No rule added.

## To watch in the first live run

- Stage questions that read as the client's, with at most their words swapped in.
- Whether bare client questions now feel abrupt after a reflection. If they do, the fix is in the
  reflection, not in rewording the question again.
- "Find yourself" or "what do you notice" leaking from the Reflective scrolling example. If it does,
  pick a different pair of the client's four scenarios for Reflective; never edit their words.

See [[styles-from-client-document-2026-10-12]], [[measure-before-tuning-prompts]].
