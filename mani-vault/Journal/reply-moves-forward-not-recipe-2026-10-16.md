---
type: journal
date: 2026-10-16
tags: [journal, prompts, voice, check, client, measured, lessons]
---

# A reply moves the conversation forward; it does not follow a recipe (2026-10-16)

The client reviewed one Directive chat (a coworker in a bad mood) point by point: Mani repeated her words,
announced "I want to understand", asked for effects she had already given, asked what she could control
before knowing her role, and ended on a five-sentence summary she called "the biggest failure". Her line:
"MANI is listening to the words, but it is not consistently using the meaning of those words."
Message: `docs/client/messages/2026-10-16-coworker-directive-feedback.md`. Requirement R16.

## Every failure was ours, not the model's

Each point traced to a line we wrote, most of them copied from her own sample of 2026-10-13:
- `how_you_talk` told every reply to say back their words, say what Mani wants to understand, and ask
  with options. Her sample did each of those *sometimes*, with something new beside it; as a recipe for
  every reply they became mechanical paraphrase.
- `identity` ("never explain people to themselves") and `boundaries` ("no advice… not even inside a
  question") forbade Mani's own reading, so restating was the only safe move left. Her better replies
  all contain a reading: "This goes beyond someone having a bad day."
- The check was four sentences joined by `repairs.check_text`, a case summary by construction.

This was R13 and R14 reached a fourth time. Each round encoded her latest example as a *form* (rules,
then an example to copy, then a recipe, then a code-ordered check), and each time the model reproduced
the form. The change this time is to what a reply is *for*: know what is new and the one thing missing,
say the first in one sentence of your own, ask the second.

## Measured, one run each way (Directive, `pinpoint_and_check`, 10 conversations)

Same conversations, same style; before = runtime files stashed and reseeded.

| | before | after |
|---|---|---|
| "announces understanding" | 29 of 76 replies | 0 of 68 |
| question asked again | 2 | 0 |
| asks for what they said | 2 | 0 |
| explains people | 1 | 0 |
| check length | 59 to 70 words | 20 to 30, one sentence |
| no check by message 5 | 5 | 5 |

One run each is noise for rates near the middle; 29 to 0 is not. Logs:
`scratchpad/before_directive.txt`, `after_directive.txt` (session 8aadac11).

## What did not move, read by eye

- **Saying back is down, not gone.** Held-out openers still restate ("One criticism from your boss has
  you questioning whether you're good at your job"). It cannot be counted: a word overlap flag missed
  her own example (2 of 7 words, because Mani paraphrases), so it was not built. It is a human read.
- **Readings appear, but rarely.** The good one: "the hard part is that your boss keeps finding
  something missing, so you can't tell what would count as enough." Most held-out replies are now a
  plain question. That suits Directive; Supportive and Reflective were not run and may lose warmth.
- **Role before control did not happen.** In her own chat the person said "I don't know" unprompted,
  which filled the control step, so the gate opened and Mani checked instead of giving the reading she
  wanted. Elsewhere the control question is still the prompt's own words ("What, if anything, can you
  influence or decide…").
- **Her chat copies the example.** It is now the example, so that conversation shows copying, not
  learning ("scolded" flagged as borrowed). Judge on the other nine.
- Pacing (R5) unchanged: 5 of 10 still have no check by message 5.

## The check became her reading, same day

The gaps left above (role not asked, a check instead of her point 4 reply, the offer a turn late) had one
cause: the check turn was a yes/no confirmation, and an unprompted "I don't know" opened it. muhammad kept
the gate ("still confirm context") but changed what confirming is: the check is Mani's reading plus a
question that moves forward, and answering that question counts as going along with it. No gate code
changed, only `Check.question`, `check_answer`, `[ctx]` and `the_check`.

Live, Directive, once: 5 of 5 checks were a reading plus a forward question, none asked for confirmation,
and her chat asked the role, then gave her point 4 reply and offered right after "no, I haven't". One
reading asked what the person had just proposed ("maybe i could ask him" → "Have you been able to ask
him?"). Log: `scratchpad/reading_directive.txt` (session 8aadac11).

Supportive and Reflective, once each: 11 of 11 checks were a reading plus a forward question. Supportive
kept its warmth ("I'm sorry it's been frustrating. What's been going on?"). Both still open "everything"
with a general line ("It can be hard to know where to start when it feels like everything"), and pacing
is unchanged (4 and 5 of 10 have no check by message 5). Logs: `scratchpad/reading_supportive.txt`,
`reading_reflective.txt`.

Gotcha: `scenario_check.py` answers every check with "Yes, that's right." unless the scenario sets
`check_answer`. Against a forward question that line is unnatural; give a scenario its own answer when
reading how the offer lands.

## Lessons

- When a client's example is copied as a recipe, the surface survives and the reason it worked is lost.
  Hand over what a reply is *for*, then show the example.
- A rule that forbids a move without naming a replacement leaves only the safest move, and here that
  was paraphrase. Same lesson as [[mani-forms-a-read-instead-of-mirroring-2026-10-13]].
- Test a metric on the case it exists for before trusting it. The say-back flag would have reported
  her chat as clean.

See [[client-sample-voice-and-confirmed-check-2026-10-13]] (superseded in part by this note).
