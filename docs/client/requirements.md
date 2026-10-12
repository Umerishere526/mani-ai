# Client requirements from messages

The living list of what the client's messages require. Each row links to the message it came from.
Update a row's status as work lands; never delete a row — mark it done or superseded and link the
message that changed it. Rules for this folder are in [README.md](README.md).

## Deadlines

| Date | What the client expects | Source |
| ---- | ----------------------- | ------ |
| 2026-10-12, before 3:00 PM ET | Improvements implemented and testable before the call; tell the client what changed | [urgency letter](messages/2026-10-12-urgency-and-wednesday-deadline.md) |
| 2026-10-12, 3:00 PM ET call | Review working improvements and a clear plan; focus on solutions, not revisiting known problems | [urgency letter](messages/2026-10-12-urgency-and-wednesday-deadline.md) |
| 2026-10-14 (Wed) morning, at the latest | Everything outstanding resolved; complete conversational experience working in all three styles (R9) | [urgency letter](messages/2026-10-12-urgency-and-wednesday-deadline.md) |
| Week of 2026-10-12 | Improved Chat shared with beta users | [urgency letter](messages/2026-10-12-urgency-and-wednesday-deadline.md) |
| 2026-10-19 (Mon) | Beta testing done; move on to the remaining development priorities | [urgency letter](messages/2026-10-12-urgency-and-wednesday-deadline.md) |
| About 2026-10-26 ("in two weeks") | Investor meetings demonstrating an improved MANI MVP approaching launch readiness | [urgency letter](messages/2026-10-12-urgency-and-wednesday-deadline.md) |

## Requirements

| ID | Requirement (client's terms) | Source | Status | Notes |
| -- | ---------------------------- | ------ | ------ | ----- |
| R1 | MANI listens, understands what the person is experiencing, and lets a natural conversation develop before deciding whether a framework is appropriate. No framework offer after the first user message. | [first message](messages/2026-10-12-framework-after-first-message.md), [urgency letter](messages/2026-10-12-urgency-and-wednesday-deadline.md) | in-progress | Reproduced in the screenshot: Direct style, ABCDE offered on turn 1. Client blocked from testing until fixed. Also asked: what causes it and when it will be corrected. Cause: our Decision in force of 2026-10-10 allowed an offer from the first message (see Conflicts). Fix: the first offer opens at the person's third message and is due at their fifth, in every style ([scope feature 12](../scope/scope.md)). Built 2026-10-12; live check (her message plus workplace_boundaries, 3 runs x 3 styles, 18 conversations): every first offer came at the person's third message, none earlier. Owed: `/check verify`, `/test`, and a deployment so she can test it (R10). |
| R2 | No excessive latency. | [urgency letter](messages/2026-10-12-urgency-and-wednesday-deadline.md) | open | |
| R3 | No repetitive or unnecessary language. | [urgency letter](messages/2026-10-12-urgency-and-wednesday-deadline.md) | open | |
| R4 | MANI understands the user's actual issue. | [urgency letter](messages/2026-10-12-urgency-and-wednesday-deadline.md) | open | |
| R5 | No excessive questioning. | [urgency letter](messages/2026-10-12-urgency-and-wednesday-deadline.md) | open | |
| R6 | MANI retains context across the conversation. | [urgency letter](messages/2026-10-12-urgency-and-wednesday-deadline.md) | open | |
| R7 | Transitions feel natural. | [urgency letter](messages/2026-10-12-urgency-and-wednesday-deadline.md) | open | |
| R8 | MANI follows the established conversational cadence. | [urgency letter](messages/2026-10-12-urgency-and-wednesday-deadline.md) | open | The cadence is defined in [conversational-styles.md](../../backend/docs/specs/conversational-styles.md). |
| R9 | The complete experience works in Direct, Supportive and Reflective: natural conversation, then framework completion, then an appropriate close-out. | [urgency letter](messages/2026-10-12-urgency-and-wednesday-deadline.md) | open | Due 2026-10-14 morning. |
| R10 | Corrections reach the client as they are made, so they can test each one, instead of waiting for one full deployment. | [urgency letter](messages/2026-10-12-urgency-and-wednesday-deadline.md) | open | Process requirement. Also: changes must not reproduce old issues or introduce new ones. |

## Missing source material

- The urgency letter refers to the client's earlier **testing feedback emails**, which document R2 to R8 in detail. They are not in the repo yet; paste them into `messages/` to fill in specifics.

## Conflicts with specs or Decisions in force

A newer client message beats an older spec or a Decision in force (see [README.md](README.md)). List
each conflict here with the message, the spec section or decision it overrides, and whether the spec
or decision has been updated yet.

| Message | Overrides | Updated? |
| ------- | --------- | -------- |
| [first message](messages/2026-10-12-framework-after-first-message.md) (R1) | The Decision in force "A framework is offered as soon as it fits, from the person's first message" (muhammad, 2026-10-10), and the timing in [framework-abcde.md §23](../../backend/docs/specs/framework-abcde.md), whose example offers straight after the first message. | Yes, 2026-10-12: the decision now reads "The first offer waits for the person's third message"; §23 carries a note. |
| [first message](messages/2026-10-12-framework-after-first-message.md) (R1), with [conversational-styles.md](../../backend/docs/specs/conversational-styles.md) "Same cadence" | Our per style offer windows (nearest fit due by the fourth message in Direct, the sixth in Supportive and Reflective). | Yes, 2026-10-12: one window for every style. |
