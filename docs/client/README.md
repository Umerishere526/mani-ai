# Client communication

Every message the client (Lolly) sends muhammad about MANI, kept verbatim, plus the requirements
drawn from them. This is how muhammad and Claude keep the client's asks in context across sessions.

## Authority

Client messages are requirements, with the same rank as the transcribed specs in
[`backend/docs/specs/`](../../backend/docs/specs/README.md). When a message conflicts with an older
spec or with a "Decision in force" in `backend/PORT-STATUS.md`, the newer message wins. Record the
conflict under "Conflicts" in [requirements.md](requirements.md) and update the spec or decision.

## Layout

- `messages/` — one file per message, named `YYYY-MM-DD-<topic>.md`: sender, date received, the
  text verbatim, and links to the requirements it produced.
- `attachments/` — screenshots and files the client sent, named after the message they belong to.
  Transcribe screenshots into the message file so the text is searchable.
- [requirements.md](requirements.md) — the living list of deadlines and requirements, each linked
  to its source message, with a status.

## Adding a message

1. Create the message file in `messages/` with the text exactly as sent.
2. Save any attachment in `attachments/` and transcribe it in the message file.
3. Add new rows to `requirements.md`, or update the status and notes of existing ones the message
   touches. Record any conflict with a spec or Decision in force.
4. Add the message to the index below.

## Index

| Received | From | Topic |
| -------- | ---- | ----- |
| 2026-10-12 | Lolly | [MANI offered ABCDE after the first message](messages/2026-10-12-framework-after-first-message.md) |
| 2026-10-12 | Lolly | [Urgency, unresolved issues and the Wednesday deadline](messages/2026-10-12-urgency-and-wednesday-deadline.md) |
| 2026-10-12 | client | [Directive, Supportive, Reflective: the styles document](messages/2026-10-12-styles-document.md) |
| 2026-10-12 | Lolly | [Job decision: testing feedback in all three styles](messages/2026-10-12-job-decision-testing-feedback.md) |
| 2026-10-13 | Lolly | [Two chat versions, testing confusion, and ABCDE still not explained](messages/2026-10-13-two-versions-confusion.md) |
| 2026-10-13 | client | [MANI's way of communication: language and tone](messages/2026-10-13-way-of-communication.md) |
| 2026-10-13 | client (meeting) | [The conversation flow agreed in the meeting](messages/2026-10-13-meeting-flow.md) |
| 2026-10-18 | Lolly | [Directive review: speaking up at work](messages/2026-10-18-directive-speak-up-at-work-review.md) |
| 2026-10-18 | Lolly | [Directive review: the sister who keeps borrowing](messages/2026-10-18-directive-sister-loans-review.md) |
| 2026-10-13 | Lolly | [Framework Selection Cheat Sheet](messages/2026-10-13-framework-cheat-sheet.md) |
| 2026-10-26 | Lolly | [Two conversations with ChatGPT: the voice MANI should have](messages/2026-10-26-chatgpt-boss-and-friendship.md) |
| 2026-10-27 | beta tester, via muhammad | [Chat testing review: heard, but not helped](messages/2026-10-27-chat-testing-review.md) |
