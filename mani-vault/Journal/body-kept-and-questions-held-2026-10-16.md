---
type: journal
date: 2026-10-16
tags: [journal, somatic, walk, prompts, examples, lessons]
---

# A sensation is kept, a question holds the stage, and no test scenario lives in the prompt (2026-10-16)

muhammad asked for three things after the reading check ([[reply-moves-forward-not-recipe-2026-10-16]]):
context kept through the chat, a body sensation named anywhere asked about at the check-in, and the end
of a framework handled when they ask or push back. Then: hardcode nothing to a scenario.

## What was missing

- A sensation was stored nowhere. `feeling` is an emotion word; "my chest gets tight" lived only in raw
  history, and the check-in is fixed client text, so it could never refer back. Now `understanding.body`,
  shown in every `[ctx]`, and `somatic_checkin.ask_known` with a `<body_said>` slot.
- A question at a stage was `not_yet`, so the second one let the stage go, and at E forced the check-in
  over it. Now `stage_answer` asked holds the stage without a try, up to `walk.HELD_FOR_QUESTIONS`.
- At the check-in, anything that fit no branch left `body` null and the phase never moved: a person could
  be held there for ever. Now a question gets Mani's answer and the check-in once more, then the two
  choices; something new (`body` moved_on) is followed with the two choices.
- After retirement `stages_known` left `[ctx]`. Now `finished_framework` keeps it.

## Lessons

- **A cap without a label fails the other way.** The first fix re-asked the check-in for any unmatched
  answer. Live, "I'm being moved to another team and I'm scared" got the body question again in all three
  styles. A closed label for the case (moved_on) fixed it; the cap stays only for answers no label fits.
- **`returned` was read as "it didn't help".** The model sent the panic-waves text to someone still upset.
  The field description now says what returned is not.
- **"no, I haven't" read as no to the reading.** With the check now a forward question, the model judged
  the answer to the question, not the reading. `check_answer` now says it judges the reading, never the
  question, even when the answer is no.
- **The test scenario was the prompt's example.** Her coworker chat was the example, and Mani answered it
  with her lines nearly word for word. Swapped for three short pieces of other situations, one move each
  (a new reading; role before control; why what they tried may not be enough). Held out, Mani now makes
  the moves in its own words in all three styles: asked the role in Directive and Reflective, gave its own
  point-4 reading, offered on "no, I haven't". A scenario used to judge the prompt must never be in it.
- **Scripted scenario lines do not follow the walk.** Off-script lines land a stage early or late, so the
  `off_script_after_e` group is read by eye; the integration tests in `test_turn.py` are what pin each path.

Logs: `scratchpad/offscript2_*.txt`, `heldout_directive.txt`, `cw_*.txt` (session 8aadac11).
