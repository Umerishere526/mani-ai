---
type: journal
date: 2026-11-05
tags: [journal, tests, prompts, broken-windows]
---

# 12 tests fail on `main`, left behind by the prompt rewrites (2026-11-05)

Found while running the full suite for the latency branch (`feat/latency-2026-11-05`). The same 12 fail on `main`
at `b9b5015` with the local database freshly seeded, so they predate that branch. Not fixed there: making them pass
means deciding whether the prompts or the decisions those tests hold are right, which is muhammad's call.

- **Prompt wording tests (7):** `tests/unit/test_converse.py` (5) and `test_composer.py::test_questions_follow_their_
  answers_...` assert lines that `voice.md` and `conversation.md` no longer hold ("Run the conversation the way a good
  therapist runs a session", "1. What does this person need from you right now?", "# Finding the core", "acknowledge,
  open the window, give your insight, then ask", "turns to suggestions soonest"). Most likely cause: `8e87871`,
  `114285b`, `5dfa952` rewrote those prompts without the tests. Several of these tests are the ones "Decisions in
  force" cites as holding a decision (the barometer, the five principles, the core), so either the decision changed
  and PORT-STATUS needs it, or the prompt drifted from a decision.
- **Integration (5):** four in `test_turn.py` (a comforting reply logged "no shape" beside "asks no question"; the
  style test's prompt no longer starts with the Reflective line; a declined framework's reply schemas differ; a yes to
  a real situation now gets the offer's buttons; one `KeyError` on a thread id) and
  `test_account_lifecycle.py`. The last has two causes: its model fake returns a `Reply` whatever schema the turn asks
  for (the chat asks for `ConversationReply` since 2026-10-26, so `converse.replied` reads a missing `.window`), and
  after fixing that it asserts one model call where a chat turn now makes two (the reply, then the reading after it,
  2026-11-03).

Related: [[latency-where-the-wait-goes-2026-11-05]].

## Resolved for the unit tests, 2026-11-06

In P2 muhammad chose to align them: each of the six (`test_converse.py` five, `test_composer.py` one) keeps the
decision it protects and checks it against the current prompts; wording that earlier rewrites removed is dropped, and
"acknowledge, open the window, give your insight, then ask" is now asserted absent (it was the formula every reply
took). The five integration tests in `test_turn.py` are untouched and still fail as described above.
