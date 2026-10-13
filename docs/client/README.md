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
