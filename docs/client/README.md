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
| 2026-09-01 (document date; recorded 2026-11-24) | client | [Behavioral framework: no repetition, the forbidden words, flow, grammar, validation](messages/2026-09-01-behavioral-framework.md) |
| 2026-09-01 (document date; recorded 2026-11-24) | client | [Pacing rules: one question, validation first, no repetition, anchored follow-ups](messages/2026-09-01-pacing-rules.md) |
| 2026-09-01 (document date; recorded 2026-11-24) | client | [Risk classification: HIGH, MEDIUM and LOW, and what each does](messages/2026-09-01-risk-classification.md) |
| 2026-09-01 (document date; recorded 2026-11-24) | client | [Safety guardrails: crisis handling, no diagnosis, no dependency phrases, transparency](messages/2026-09-01-safety-guardrails.md) |
| 2026-09-01 (document date; recorded 2026-11-24) | client | [The communication engine: X then Y rules, the vague-reply pivot, style and exercise rules](messages/2026-09-01-communication-engine.md) |
| 2026-10-06 (document date; recorded 2026-11-24) | client | [Somatic/grounding framework sequence: the body check-in after E, in each style](messages/2026-10-06-somatic-grounding-sequence.md) |
| 2026-10-12 | Lolly | [MANI offered ABCDE after the first message](messages/2026-10-12-framework-after-first-message.md) |
| 2026-10-12 | Lolly | [Urgency, unresolved issues and the Wednesday deadline](messages/2026-10-12-urgency-and-wednesday-deadline.md) |
| 2026-10-12 | client | [Directive, Supportive, Reflective: the styles document](messages/2026-10-12-styles-document.md) |
| 2026-10-12 | Lolly | [Job decision: testing feedback in all three styles](messages/2026-10-12-job-decision-testing-feedback.md) |
| 2026-10-13 | Lolly | [Two chat versions, testing confusion, and ABCDE still not explained](messages/2026-10-13-two-versions-confusion.md) |
| 2026-10-13 | client | [MANI's way of communication: language and tone](messages/2026-10-13-way-of-communication.md) |
| 2026-10-13 | client (meeting) | [The conversation flow agreed in the meeting](messages/2026-10-13-meeting-flow.md) |
| 2026-10-13 | Lolly | [Framework Selection Cheat Sheet](messages/2026-10-13-framework-cheat-sheet.md) |
| 2026-10-18 | Lolly | [Directive review: speaking up at work](messages/2026-10-18-directive-speak-up-at-work-review.md) |
| 2026-10-18 | Lolly | [Directive review: the sister who keeps borrowing](messages/2026-10-18-directive-sister-loans-review.md) |
| 2026-10-26 | Lolly | [Two conversations with ChatGPT: the voice MANI should have](messages/2026-10-26-chatgpt-boss-and-friendship.md) |
| 2026-10-27 | beta tester, via muhammad | [Chat testing review: heard, but not helped](messages/2026-10-27-chat-testing-review.md) |
| 2026-10-29 | Lolly, manasa, muhammad (meeting) | [The session's cadence, and three role plays](messages/2026-10-29-meeting-cadence-and-role-plays.md) |
| 2026-10-30 | manasa | [Reflective, anxiety without a clear cause: repeated confirmations in ABCDE, and somatic when already better](messages/2026-10-30-reflective-anxiety-test-feedback.md) |
| 2026-11-03 | Lolly | [Four Directive chats: one great, one inconsistent, two cut off by a timeout](messages/2026-11-03-four-directive-chats.md) |
| 2026-11-03 | muhammad (review pasted by him) | [Review of the friendship chat, and the earlier requirements set aside](messages/2026-11-03-friendship-review-and-requirements-reset.md) |
| 2026-11-04 | muhammad | [Plain talk, stage endings, and an E question people understand](messages/2026-11-04-plain-talk-stage-endings-and-e.md) |
| 2026-11-04 | muhammad | [Review of the Reflective friend chat](messages/2026-11-04-friend-chat-review.md) |
| 2026-11-05 | Lolly, manasa, muhammad (meeting) | [Stay with them, don't placate, the framework still breaks, and Monday](messages/2026-11-05-meeting-stay-with-them-and-safety.md) |
| 2026-11-05 and 2026-11-06 | Lolly | [Lolly's four test scenarios, and her three Directive chats with them](messages/2026-11-06-lolly-scenario-chats.md) |
| 2026-11-06 | manasa | [Four Reflective test chats: repetitive, no help preparing, and safety that gives way](messages/2026-11-06-four-reflective-tests.md) |
| 2026-11-07 | manasa | [The four Reflective tests, response by response](messages/2026-11-07-reflective-tests-line-by-line.md) |
| 2026-11-10 | Lolly, and muhammad's own test | [Chest tightness: safety that scares, repeats, brings up self-harm, and does not let go](messages/2026-11-10-chest-tightness-safety.md) |
| 2026-11-12 | manasa | [Three Reflective tests: chest tightness, suicidal thoughts with help, a crisis that refuses help](messages/2026-11-12-reflective-safety-tests.md) |
| 2026-11-16 | Lolly | [Directive test, the boss who yells: moving through steps instead of a meaningful conversation](messages/2026-11-16-directive-boss-abcde-test.md) |
| 2026-11-16 | Lolly | [Directive safety test: confusing safety procedures with caring for a person](messages/2026-11-16-directive-safety-test.md) |
| 2026-11-16 | manasa | [Reflective, a boss who yells: endless exploration, then a mechanical ABCDE](messages/2026-11-16-reflective-boss-yelling-test.md) |
| 2026-11-16 | manasa | [Reflective, too much work: ABCDE offered again after it was finished, and no ending](messages/2026-11-16-reflective-workload-test.md) |
| 2026-11-16 | manasa | [Reflective, growing apart: a declined framework offered again, and no ending when she was done](messages/2026-11-16-reflective-relationship-test.md) |
| 2026-11-16 | manasa | [Crisis test and the blocker: paused on a refusal, then agreed to keep talking before safety was established](messages/2026-11-16-crisis-blocker-test.md) |
| 2026-11-16 | manasa | [The Library's topic and exercise descriptions, and audio times to the nearest 30 seconds](messages/2026-11-16-library-exercise-descriptions.md) |
| 2026-11-17 | Lolly | [Directive, a gossiping coworker: the wrong framework for a belief that needed no changing, beside ChatGPT](messages/2026-11-17-gossiping-coworker-chatgpt-comparison.md) |
| 2026-11-17 | Lolly | [Directive, a year-end boss: MANI 3/10, ChatGPT 7/10](messages/2026-11-17-year-end-boss-chatgpt-comparison.md) |
| 2026-11-17 | manasa | [Two Reflective workplace tests: better recovery and practical help, still no closing](messages/2026-11-17-reflective-workplace-tests.md) |
| 2026-11-18 | Lolly | [Directive, a team that blames its leader: still mirroring, too quick to agree, ABCDE still a quiz](messages/2026-11-18-team-blame-workplace-test.md) |
| 2026-11-18 | Lolly | [Crisis test: a second lockout on "I am fine", and a pause for someone who has no one](messages/2026-11-18-crisis-second-lockout.md) |
| 2026-11-18 | client | [Framework sequences: the ABCDE original intended delivery, in three example conversations](messages/2026-11-18-framework-sequences.md) |
| 2026-11-18 | client | [The client's review of a Directive chat: passed over for promotion, through ABCDE](messages/2026-11-18-promotion-chat-feedback.md) |
| 2026-11-18 | client, relayed by muhammad | [Supportive and Reflective: build up to the highlight](messages/2026-11-18-supportive-reflective-build-up.md) |
| 2026-11-19 | manasa | [Three reviews: summary and "yes, yes, yes" in ABCDE, foxholes, and analysis after she asked for practice](messages/2026-11-19-three-reviews.md) |
| 2026-11-20 | Lolly (answering muhammad) | [Hearing them, meeting them, moving them forward: the three buttons, practical help, the natural end](messages/2026-11-20-hears-meets-moves-answers.md) |
| 2026-11-20 | Lolly | [Directive, a controlling boss: "WOW! 7/10", and validating feelings is not validating reasoning](messages/2026-11-20-workplace-test-wow-7-of-10.md) |
| 2026-11-20 | Lolly | [The Library mock-up is not the direction they had in mind](messages/2026-11-20-library-mockup.md) |
| 2026-11-20 | Lolly | [Thanksgiving alone: MANI paused a lonely, crying person who was in no danger](messages/2026-11-20-thanksgiving-lockout.md) |
| 2026-11-23 | Lolly | ["Where are these from?": the feelings-check buttons after E](messages/2026-11-23-capsule-buttons-curious.md) |
| 2026-11-23 | Lolly | [Directive, Thanksgiving alone: an enjoyable ABCDE inside a conversation that did not listen, track or remember](messages/2026-11-23-thanksgiving-directive-test.md) |
| 2026-11-23 | Lolly | [Directive, workload and a boss who breaks promises: 3/10](messages/2026-11-23-workload-and-boss-test.md) |
| 2026-11-23 | Lolly | [Directive, overworked and underappreciated: 0/10](messages/2026-11-23-overworked-underappreciated-test.md) |
| 2026-11-23 | manasa | [Lolly writes the standard conversations: five Directive ones by November 30, and every build says what is ready](messages/2026-11-23-directive-examples-and-build-notes.md) |
| 2026-11-25 | Lolly | [Directive chat: a new conversation opened with a question about a pause she never had](messages/2026-11-25-directive-chat-return-check.md) |
