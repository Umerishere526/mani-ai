# Scope: Mani

Mani is a mental health companion. This scope started with the body check at the end of a framework, built to match the client's wording and flow for the Direct, Supportive and Reflective styles. It now also covers what the October 2026 backend audit and framework review found must change before real people use Mani: safety, privacy, reliability, and frameworks that follow the client's document. Since the client meeting in October 2026 it also covers making Mani sound natural, neutral and down to earth, which means loosening rules that had overfitted the model.

**Build approach:** Tracer Bullet (get one style through the whole flow end to end, then repeat for the others).
**Workflow:** Beta (check verify, then test). The reply text is health content the client signed off on, so it needs a real conversation run, not only unit tests. Every safety and privacy feature carries `· GA` (adds a fresh model review and docs).

_These are recommendations to keep your build orderly, not requirements. Skip anything that does not fit._

## Epics

- [Conversation](conversation.md): natural replies, the body check, framework offers and framework questions. 23 features: 5 done, 16 planned, 2 dropped (row 30 is GA).
- [Safety and privacy](safety.md): danger detection, crisis help, safety mode, private data, permissions. 10 features: 1 done, 9 planned, all GA.
- [Production readiness](production.md): staying up, limits, monitoring, fallback, automatic checks. 5 features planned, 10 deferred.

## At a glance

| #   | Feature                                                                        | Phase   | Status  |
| --- | ------------------------------------------------------------------------------ | ------- | ------- |
| 1   | Somatic check asked once, then moves on                                        | Slice 1 | done    |
| 2   | Where in the body, with buttons, then the exercise                             | Slice 1 | done    |
| 3   | Per style wording from the client                                              | Slice 2 | done    |
| 4   | Returns in waves, then the library offer                                       | Slice 2 | done    |
| 5   | ABCDE is offered when an event and a belief about it are named                 | Slice 3 | done    |
| 6   | The offer names the framework, introduces it, and gives three choices          | Natural Mani | planned |
| 7   | The manager chat is a standing real conversation check                         | Slice 4 | planned |
| 8   | Mani picks the best framework from the person's situation and steers toward it | Slice 5 | in-progress |
| 9   | Crisis help a person can use                                                   | Slice 6 | planned |
| 10  | Danger detection catches real phrasing                                         | Slice 6 | planned |
| 11  | Safety mode follows the person                                                 | Slice 6 | planned |
| 12  | Mani stays up when many people chat                                            | Slice 7 | planned |
| 13  | Private conversations stay private                                             | Slice 7 | planned |
| 14  | Database permissions match what users should do                                | Slice 7 | planned |
| 15  | Usage and request limits                                                       | Slice 7 | planned |
| 16  | Monitoring and alerts                                                          | Slice 7 | planned |
| 17  | Guide questions match the client's wording                                     | Slice 8 | planned |
| 18  | A framework stage moves on after one answer                                    | Natural Mani | in-progress |
| 19  | Body check in follows every framework                                          | Slice 8 | in-progress |
| 20  | A framework stops when the person asks                                         | Slice 8 | planned |
| 21  | Hard safety rules enforced in code                                             | Slice 9 | planned |
| 22  | Reply shape built into Mani's answer format                                    | Slice 9 | dropped |
| 23  | Backup AI provider and no lost messages                                        | Slice 9 | planned |
| 24  | Memory and notes kept apart from instructions                                  | Slice 9 | planned |
| 25  | Admin access guarded and recorded                                              | Slice 9 | planned |
| 26  | Automatic checks on every change                                               | Slice 9 | planned |
| 27  | Client rules the app never reads                                               | Slice 8 | planned |
| 28  | Shared Mani rules agree with the client's document                             | Slice 8 | dropped |
| 29  | Our additions to the frameworks get client sign off                            | Slice 8 | planned |
| 30  | DBT STOP follows the client's cadence and never delays help                    | Slice 8 | planned |
| 31  | Every framework's worked example is a standing check                           | Slice 8 | planned |
| 32  | The client's style conversations are a standing check                          | Natural Mani | in-progress |
| 33  | Mani speaks naturally: short, neutral, humble instructions                     | Natural Mani | done |
| 34  | No dashes in any reply                                                         | Natural Mani | planned |
| 35  | The model is chosen on real conversations                                      | Natural Mani | in-progress |
| 36  | A short answer to Mani's safety question is checked                            | Slice 6 | planned |
| 37  | The model's safety flag does not stall DBT STOP                                | Slice 6 | done |
| 38  | A request to hear a question again also reads "whats that mean"                | Natural Mani | in-progress |
| 39  | Stage questions flagged in the 2026-10-05 chats                                | Natural Mani | planned |

Natural Mani (rows 32, 33, 34, 18, 38, 6, 35, in that order) is the current focus and comes before every slice below it. It overrides parts of ADRs 006, 007, 008, 010 and 011, and row 33's spec records which. Slices 6 and 7 are what has to be true before a limited beta. Slice 9 is what has to be true before an open launch. Slice 8 can run alongside either, as client answers arrive.

## Open questions for the client

- The style document's offers say "I have a structured approach..." and never name the framework. We plan to say its name and a short introduction (row 6). Please confirm in writing.
- Inside a framework, Mani will move to the next step after any answer, including "I don't know" (row 18). Some later steps then have less to work with, for example ABCDE's dispute step when no belief was named. Is that the trade you want?
- The client's example ends "How do you feel now?" and then goes straight to the "comes back" reply. What should happen when the person answers "better" or "still tense"? The current buttons "I tried it / Still tense / Feeling better" are not in the new flow.
- Panic conversation: the earlier framework asks about the body once already ("What are you noticing in your body right now compared with when we started?"). Does that count as the one body question, so the somatic check should go straight to "where"?
- Safety (rows 9 to 11): the exact question Mani asks when it is unsure whether someone is in danger; the reply for each kind of risk; checked crisis services for each launch country; when a crisis counts as resolved and who decides; who on our side is told about a crisis; about 300 example messages labelled by a clinician.
- Which countries and languages come first? This decides the crisis services and the languages detection must handle.
- After a crisis, should the chat lock (as today) or should the person move into a safety mode where Mani keeps talking only in approved wording?
- When someone cannot think of an action, may Mani suggest one, or up to three? The document says one in Behavioral Activation but shows three in its intro example (row 18).
- When someone asks Mani to choose ("tell me what to do"), may Mani offer a suggestion they can accept or change (row 18)?
- Should the body check in always follow a framework, even when the person has just named what they will do next (row 19)? muhammad decided yes on 2026-10-05; the client has not been told yet.
- If abuse comes up during ABCDE or Thought Reframe, should Mani end the framework or carry on without reinterpreting it (row 17)?
- Should crisis records be kept after someone deletes their account? This needs legal advice.
- The team added rules the document does not have (grief, fatigue, "too light for I am a failure", ACT's "to ease a feeling" check, DBT STOP's breathing anchor, ending ABCDE on abuse, waiting rules before an offer). Which should stay (row 29)?
- May DBT STOP be offered on the first message when someone is about to act, or only after the usual conversation and style choice (row 30)?

## Legend

**The decision box.** Every feature carries one sub task ending in `(spec)`. Skills find it by that suffix.

- **Next step** is the first unticked box.
- **needs a decision** means run `/architect` first. The tag drops once the spec is captured.
- **Status** goes `planned`, `in-progress`, `done`.
- **GA** beside a heading means that feature runs check verify, test, a fresh model review, then docs, above the project's Beta default.
