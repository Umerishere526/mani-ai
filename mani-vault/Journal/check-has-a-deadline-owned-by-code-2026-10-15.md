---
type: journal
date: 2026-10-15
tags: [journal, check, understanding, offer, dialog-management]
---

# The check has a deadline owned by code

muhammad's Directive chat (thread 8f03e7bf: "I'm a failure and I'll never amount to anything") ran about
twenty of their messages and 47 stored ones with no core issue, no control question and no check, so no offer
could come. The decision, the numbers and the departures from `mani_base.md` are in `backend/PORT-STATUS.md`
(Decisions in force) and spec 0006 AC-11. This note is about what was learned.

## Cause

The gate for the check was a field the model had to volunteer (`core_issue`, then control), and nothing in
code bounded the wait. The `core_issue` guidance said "a feeling, such as not being enough, is not yet the core
issue", so a chat whose every answer was feeling level ("shameful", "both", "not sure") kept digging one level
deeper and `issue` drifted. This is the lesson of [[client-sample-voice-and-confirmed-check-2026-10-13]] again:
state that waits on a model report can stick, state that expires by construction cannot. The spec's own
invariant "no state can leave a thread unable to check again" was false for it.

## What the Opus 5.5 review caught in my first plan

Each of these would have left the chat looping, and each was visible in the code:
- `check_written` was decided from the person's own `understanding_update`, so relaxing `may_check` alone
  never stored the check, and `merge_check` would still drop control for the step order.
- A relaxed `may_check` still left `check` nullable, `understanding_next` and `once_control_is_answered`
  telling the model to ask and leave check empty, and nothing logged after message 5.
- The message count ran from the start of the thread, so after a declined offer or a finished framework the
  deadline would have been permanently open.
- A check that also asks about control reads as a no (anything but a clear yes is a no) and stalls the offer.
- A due check's guesses were stored as the person's own words before they answered.

Lesson: a plan that "opens a gate" must trace the whole path of the thing it opens, not only the gate.

## Left for later

- A required `check` replaces the reply's text, so a direct question asked at exactly that turn gets a check
  instead of an answer. Watch for it in the live run (`feeling_level_only` in `scripts/scenarios.json`).
- Existing tests that ran a dozen replies with no check now sit in the declined state, where no deadline
  applies; they test the transcript window, not the check.
