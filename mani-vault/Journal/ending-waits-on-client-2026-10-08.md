---
type: journal
date: 2026-10-08
tags: [journal, ending, client, preferences]
---

# Feature 21 waits on the client: today's ending, audited

`/architect the ending follows the issue` stopped before any spec. muhammad rejected the flow recorded in scope feature 21 (the three after framework questions on a continuing issue), gave a newer one, then said the flow can still change and the client should be asked first.

## muhammad's thinking (2026-10-08, not final)

- No three after framework questions: the stages usually answer them already (feature 12, [[stage-ledger-design-2026-10-08]]).
- Issue not resolved when the framework finishes: keep chatting, then offer another framework that fits.
- Issue resolved: offer the body check. Yes, do it. No, stop with Chat More and Go to Library.

Lesson: twice now the ending's flow changed mid interview ([[body-ending-design-2026-10-08]]). For a flow the client owns, ask muhammad to state the flow, and whether the client has confirmed it, before generating options.

## Today's flow after a framework's own stages (seeded locally 2026-10-08)

1. `closing`: Mani asks how they feel now, never says it worked, never summarises.
2. `somatic_checkin`: reflects the answer and offers the body check whatever they said; sorry first if they feel bad; no push on a no.
3. `somatic_practice`: one step per reply from a fixed list, then asks how they feel; no breathing step with pain, trouble breathing or feeling faint.
4. The model's `ending`: `choice` retires with Chat More, Go to Library and an exercise card (a second small call); `keep_talking` retires with nothing; the cap retires after 12 of their messages; a crisis retires and locks; a concern pauses.
5. After: the three questions run only while a Chat More reply is in the 20 message window (`context._chat_more_offered`), so only on the feel okay path. The next offer waits for `cooldown_after_complete` 45 messages counted from their yes, about 12 exchanges after the end. The finished framework never returns in the thread.

## Conflicts to settle with the client

- Client ABCDE doc §0.8 rule 7, "No automatic somatic exercise", against a body check offered at every ending, even to someone who still feels bad.
- The 45 message cooldown against muhammad's "offer another framework" after an unresolved ending.
- No real model run has measured this ending; spec 0009 shipped on scripted tests.

Related: [[abcde-client-doc-2026-10-08]], [[body-ending-build-2026-10-08]]
