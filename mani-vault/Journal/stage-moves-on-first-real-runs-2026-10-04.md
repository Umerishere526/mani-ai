---
type: journal
date: 2026-10-04
tags: [journal, frameworks, stages, evals]
---

# Row 18 built and run against the real model

Spec: `docs/specs/0003-stage-moves-on-one-answer/`. Design lessons: [[stage-moves-on-design-2026-10-04]]. What the service does now: `backend/PORT-STATUS.md`.

Built: the move on turn (`techniques.moves_on_after`, `context._move_on_lines`, `repairs.apply`), the base prompt rewrite, the six framework files, 26 `if_earlier_missing` questions (muhammad chose each wording from two candidates, 2026-10-04), a walk test over all six real frameworks, and a `held` and a `stage` finding in `eval_replies.py`.

## What the runs showed (54 conversations: six frameworks, three runs, three styles)

- The core change works: one stage per reply, in order, none asked twice, and the stored stage always moved one on except on four holds.
- The `generic` finding ("framework question shares nothing they said") fired on about 130 replies and is noise here: it wants a word in common with what they said, and a good question after "yes" or "I don't know" has none. Judge these runs by reading, not by that count.
- The 26 wordings were used where they belong. One misfire: ABCDE `evidence_against` used its "unsure" line although the belief had been named. The line says "if nothing usable was said at the stage it names", and the model read that as the latest reply.

## Things worth remembering

- **A rule that names a stage is ambiguous in a prompt that shows two stages.** "At `options`..." was read as the stage to ask, not the one just answered, so I wrote "when `answered` is". It changed nothing for Structured Problem Solving, because the real cause was the framework's own boundary ("never choose for them", "must not push the option MANI prefers"), which the model reads on the stage it is about to ask. Look for a content boundary that contradicts a new prompt rule before rewording the prompt.
- **A spec can contradict the client's own specification without anyone seeing it.** AC-5 listed `options` and `select` as places Mani gives one step; the client's Structured Problem Solving says never choose for them. muhammad's answer: offer one of the options they already have, with a short reason, and ask whether it works or another is easier; if still unsure, move on. That is spec 0003 again, through `/architect`.
- **A person who says "what do you mean?" about Mani's own question was held in 3 of 54.** muhammad wants one rephrase, then move on, in plain natural English, and never looping. It needs a count of holds on the stage somewhere (nothing stores it today), so it is a design question, not a prompt line.
- **A hold I could not detect in code:** Structured Problem Solving gave the hand off text but reported `closing` once, so the framework stayed at `closing` and the Chat More buttons were dropped. A hold at a stage with no branches can only be one of the client's lines (stop, another issue, misunderstood), so code cannot tell it from this.
- **`git checkout` on a file with uncommitted work wipes it.** I did this to `techniques.py` while undoing a mutation test, and restored it from a copy I had taken a moment before. Copy first, or mutate a temporary copy of the module.
- BSD `sed -i` on macOS needs `-i ''`.
- Adding a framework to a shared test registry fixture broke an unrelated membership test; give new tests their own fixture.
