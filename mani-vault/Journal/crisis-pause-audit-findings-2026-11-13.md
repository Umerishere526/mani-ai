---
type: journal
date: 2026-11-13
apps: [backend, chat-tester]
tags: [journal, safety, crisis, pause, audit, lessons]
---
> Superseded 2026-11-13 — see [[crisis-pause-fires-on-refusal-2026-11-13]] (the turn loading only its own pause first, and a doubt in a chest chat pausing)

# The crisis pause, and what the audit before it found (2026-11-13)

2026-11-13. History, not rules. The rule in force is the safety entry of Decisions in force in `backend/PORT-STATUS.md`;
the design is `docs/superpowers/specs/2026-11-13-crisis-pause-and-first-message-threads-design.md`.

## The danger instruction never reached the model

- A turn's safety instruction in [ctx] was picked from the state *before* the model judged. So the first reply that
  judged danger was written under the unsure instruction ("do not tell them to call anyone while you do not know") or
  under the chat's note, and the "danger" instruction was sent to no turn at all. The turn after it was told
  `danger_said`, "you already told them what would make them safe", whether or not that had been said.
- It mattered more once the pause depended on it: the pause rule assumes Mani's previous reply already said what would
  make them safe.
- The fix is one text, `context.DANGER_DIRECTION`, sent with every turn that can judge danger: the clear line in
  [ctx], the unsure instruction, the chat's note (`converse`) and a new conversation's return check (`returning_new`).
  `danger_said` comes only when the thread was already in danger, so the previous reply carried the direction.
- The same hole was found three times: by the audit, by Task 5's review (framework, stage, offer and check turns that
  start clear got no direction) and by Task 8's review (`returning_new` had none). Each fix covered only the paths its
  report named. Lesson: when an instruction must reach "every turn that can judge X", list the turn kinds from the
  code (`context.build`, `converse`, each `_MEANING["safety"]` entry) and test each one.
- Left as is: the paused conversation's own return check (`returning`) carries no direction. If that turn judges
  danger, the next turn's `danger_said` says "in your last reply", though the direction came earlier, in the pause
  text. Judged harmless in review.

## One switch, three defaults

- `CRISIS_BLOCKS_CHAT` defaulted to off in `config.py`, was `true` in muhammad's local `backend/.env` (see
  [[edit-follows-the-send-lock-2026-11-10]]), and `crisis_blocks_chat` defaulted to `True` on the API models and on
  `orchestrator.Turn`. The refused-help turn never set the field, so it went out as `True`, and the chat-tester showed
  manasa "This conversation is paused after a crisis flag. Start a new conversation to continue.": a new chat offered
  as the way round help, which R87 forbids.
- Lesson: a setting's default lives in one place, and a response field that echoes a setting has no default of its
  own.
- The setting, its fields and the tester's banner are removed. muhammad's `.env` still has the line, ignored now
  (`extra="ignore"`), and can be deleted. Production has the variable set
  ([[deploy-check-of-the-safety-branch-2026-11-11]]) and still runs code that reads it; it is ignored once this branch
  deploys, and can be deleted then.

## A later pause hid an earlier conversation's question (Task 8)

- Conversation X pauses and its pause runs out; then conversation Y pauses and its pause runs out; then they write in
  X. The turn loaded the person's latest pause, Y's, so X owed no return check, and X, still in danger, paused again at
  once with no question.
- The fix: a turn loads its own conversation's latest finished pause first, else the person's latest
  (`threads.load_turn_context`). `test_a_later_pause_in_another_conversation_never_hides_the_paused_ones_question`.
- The test helper `_end_pauses` had ended pauses a minute in the past, which made every new conversation look
  "started after the pause", and the first failing run showed `new_thread` instead of the bug. A helper that moves the
  clock can hide the very ordering under test; it now ends a pause at `now()`.
- "Finished" is read by the database's clock (`ends_at <= now()` in the same query), the clock the gate uses. With the
  app's clock a second behind, the first message back would take the ordinary danger path and pause without asking.

## Also found

- The end check after a framework's last stage keyed on `crisis_detected`, which a phrase judged only unsure also
  sets: "I want to die", explained as a horrible day, still got the safety question at the end. It keys on
  `understanding.danger_reached` now. Conversations from before have no such key and get no end check: a backfill
  needs muhammad's yes.
- `recent_crisis` counted its 30 days from the flagged thread's last message, not from the crisis; `threads.crisis_at`
  (migration 037) holds when it happened.
- Every kind of danger can pause, so a chest chat that doubts it ("could it be stress?") while the symptom is still
  judged happening now, with nothing in place, pauses at that message. To measure in the live chest replays
  (PORT-STATUS, Open decisions for muhammad).
- Migration 037 grants `authenticated` SELECT on all of `chat_pauses`, so a person can read their own pause's reason
  through the Data API with their token. The backend never loads it outside the paused conversation. Raised for the
  whole-branch review.

Related: [[safety-is-the-models-judgment-2026-11-10]], [[audit-of-the-safety-branch-2026-11-11]],
[[safety-is-a-state-2026-11-06]], [[threads-only-from-the-first-message-2026-11-13]].
