---
type: journal
date: 2026-10-13
tags: [journal, frameworks, stages, memory, client]
---

# Version B remembered by doing more model work, not by storing anything

Lolly tested two chats on 2026-10-12 ([message](../../docs/client/messages/2026-10-13-two-versions-confusion.md)):
ours ("A", natural) and the colleague's `feat/abcde-framework-revamp` ("B", better at remembering).
B had already been merged into our history as PR #33 (`70ca423`). We then changed it in five
commits.

The architecture review found that B stored nothing more than A. In both, the model rebuilds
`stages_known` from the last 20 messages every turn, and the ledger is thrown away after the reply.
`TechniqueState` holds only `phase`. B felt like it remembered because of three things we cut on
purpose:

- a second call when the ledger and the step disagreed (`redraft.py`), cut for R2
- effort `high`, cut for R2
- "build the question from their words, never send it bare", cut for R3

Lesson: when one build "feels better" at something, check what it pays per turn before copying it.
Memory that only lives inside one model reply is bought again every turn, in latency or in tokens.
The fix that keeps one call at low effort is to store the ledger and let code own it
([scope feature 18](../../docs/scope/scope.md)).

Also found: `with_ledger_step` sets `state.step` from the ledger without touching the text, so the
stored step can name a stage the person was never asked. Feature 18 removes it.

muhammad's calls the same day: the offer shows the client's short list of the five steps, while
Tell me more keeps the longer text (feature 17). Each stage is named by its letter as the client's
ABCDE document shows (feature 18). That reverses "the chat never names a stage" from
[[stages-are-skipped-not-confirmed-2026-10-09]].
