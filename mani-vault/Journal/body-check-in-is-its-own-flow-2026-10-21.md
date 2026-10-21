---
type: journal
date: 2026-10-21
tags: [journal, somatic, body, misread, lessons]
---

# The body question belongs at the end of a framework, not in the middle of a chat (2026-10-21)

muhammad asked for the body check-in to ask about a place when a feeling usually sits there ("we talked about anxious,
that is usually felt in the chest, is that still the case?", Yes and No, Yes starts the chest exercise, No leaves the
flow as it was). I built it to fire on any typed feeling word, in chat and inside a framework, and moved the whole
check-in's state onto the thread to make that possible (migration 026, about 20 files). His first run showed the
question about the chest in the middle of understanding, one message after "feel embarrassed and anxious", and he said it
should only happen after the end of the framework.

## What went wrong

His message said "when the framework cadence and chat cadence". I read that as "in both" and asked him about the
cadence of the question, never whether it should be only at the end. Two follow-up questions were about the state design
and the wording of the check, which treated the reading as settled. The reading justified a redesign the feature does not
need: with the question only at the end of a framework, the check-in could stay on the framework run.

## What changed (same day)

- The mid-conversation trigger, its replay on No and the thread migration were removed completely, by reversing each of
  my own edits (the files also held muhammad's earlier uncommitted changes, so `git checkout` was not an option), the
  local database restored by SQL, and the suite brought back to its earlier count before anything new was added.
- The personal question is a step of the check-in itself: phase `somatic_check`, before `somatic_body`. After a
  framework's last stage, if the feelings Mani found before the framework hold a word from `somatic_check.places`, Step 1
  is the client's introduction and the personal question with Yes and No; otherwise Step 1 as before. Yes is the exercise
  for that place, No the general question with its five buttons. A test pins that a feeling word in chat or inside a stage
  never produces it.

## Lessons

- When a request names two contexts ("framework cadence and chat cadence"), confirm which one before choosing a design,
  especially when the answer changes where state has to live.
- A redesign approved on a premise has to be reconsidered when the premise is corrected; muhammad chose to undo it. The
  undo is as costly as the build, so the premise is worth one direct question first.
- A new trigger word fires inside old tests: one test typed "feeling anxious" and was asked about its chest. That was a
  sign the trigger was in the wrong place, not only a test to reword.

To watch in the first live run (needs muhammad's yes): the personal question only after the last stage, Yes then the
chest exercise, No then the five buttons, and nothing of the kind during chat or a framework.
