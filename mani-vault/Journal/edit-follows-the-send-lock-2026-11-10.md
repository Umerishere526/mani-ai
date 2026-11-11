---
type: journal
date: 2026-11-10
tags: [journal, backend, chat, edit, safety]
---

# An edit is refused in a crisis thread only where a message is

2026-11-10. muhammad: "why can't we edit the previous chat more than 3 times?" The tester showed
`403: This conversation is paused, so its messages cannot be edited.`

## What it was

Not a count. `rewind.undo_last_turn` refused every edit once `threads.crisis_detected` was set, and nothing clears
that flag. The rule was written on 2026-11-03, when a crisis locked the chat. On 2026-11-06 the lock went off
(`crisis_blocks_chat = False`), so the thread kept taking messages while every edit said "paused". The third edit
was only the turn after a `medical_now` reading from the chest-tightness testing
([[safety-keeps-the-signs-that-opened-it-2026-11-10]]).

## What changed

muhammad chose "same as sending". The edit has no crisis rule of its own: the send that runs the new text refuses
under `crisis_blocks_chat`, and the transaction rolls the undo back with it. One rule in one place, so the two
cannot drift again. The crisis record in `admin.crisis_events` stays when the message that raised it is edited
away. Test: `test_a_message_in_a_crisis_thread_is_edited_wherever_one_can_still_be_sent`.

## Lesson

A rule copied next to the thing it mirrors goes stale when the original changes. When a second path must obey the
same condition, let it run through the first one.

## Found on the way, not fixed

- `backend/.env` on muhammad's machine has `CRISIS_BLOCKS_CHAT=true` and `REASONING_EFFORT=low` (file dated
  2026-10-27). The running dev server only has the lock off because its shell exports `CRISIS_BLOCKS_CHAT=false`.
  A server started from a plain shell locks flagged threads.
- The suite reads that `.env`: with it, nine safety tests in `test_turn.py` and two in `test_chain.py` fail on this
  machine. `tests/conftest.py` only sets fallbacks, so a developer's `.env` decides what the tests assert against.
- `ruff check tests/integration/test_turn.py` fails on the committed file (two unsorted import blocks, one unused
  `pool` import), which makes the edit hook report an error on every change to it.
- `test_account_lifecycle` fails against the throwaway DB on 55432 (sign-up lands in the dev stack's GoTrue).
