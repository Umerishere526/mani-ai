---
type: journal
date: 2026-09-24
tags: [journal, frameworks, evals, lessons]
---

# Framework endings and ignored offers

Lessons from the rehearsal against the client's second doc, 2026-09-24. Follows
[[measure-before-tuning-prompts]].

## Decide the ending from the reply's words, not its stage

The client's ending takes two replies: the body question, then "What would you like to do next?"
with Chat More / Go to Library. The model attached the two buttons to the body question in most
runs, and code added them again on the next reply. That put the choice on screen twice, and the
first after-framework question was asked twice.

Stripping them from the `somatic` stage by stage id was wrong. When the person answers the closing
question with their body ("a bit lighter in my chest"), the model rightly skips the body question
and asks what next in the `somatic` reply. Now the buttons go on whichever reply asks the client's
what-next question, once.

## Typing past an offer is Keep chatting

muhammad decided this. The schema used to say "null, so the offer stays open", and the model took
that literally. It repeated "Would you like to try it?" reply after reply, in 7 of 22 scenarios.
Only a question about the offer keeps it open now, and code strips any offer from a reply that
takes a no.

## Scripted journeys drift from the model's pacing

Fixed user lines can't follow a model that takes one more or one fewer turn in a stage. "Chat
More" arrives before the button exists, and stage answers land in the wrong stage. Journey findings
labelled `script:` or `journey: stopped at` are mostly the harness. Read the transcript before you
count them. The end-to-end check that matters is a live run in the chat-tester.

## A prompt example becomes the template

`mani_base.md` gave three offer examples, and all three began "I have a sequence of questions
that could help you…". That was 24 of 26 offers in the rehearsal, word for word. Examples that
vary, plus "word it fresh every time", brought it down to 10 of 28. Before blaming the model for
sounding templated, check whether the examples all share a template.

Per-style offer timing had the same cause. Both files said "two to four exchanges" for every style.
Once the files said Direct offers fast, Direct offered at the second message in 8 of 9 cases.
