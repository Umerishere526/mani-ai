# The body route is asked once, and held in code

2026-10-02. muhammad's panic chat: the body question came back after "yes", and "idk" ended the chat on Chat More with no practice.

## What was wrong

- `orchestrator` stapled the fixed check-in question onto every reply while the phase was `somatic_checkin`. The stage only ever moved on when the model said so, so "yes" got the same question again. Reproduced against the real model: three turns in a row in Supportive and Reflective.
- `somatic_practice` is the last phase, so the turn after any reply in it retired the framework and forced Chat More / Go to Library. The "where" question lived in that stage, so the answer to it ended the chat.
- A person who described their body before the check-in went straight to the two choices with no practice. The old test `test_a_body_they_already_described_ends_on_the_two_choices_once` asserted that; it encoded the earlier client flow and was rewritten.

## What holds it now

`_body_route_step` in `mani/chat/orchestrator.py`, from the thread history, not from the prompt (the prompt already said "must not ask more than once" and was ignored). `_awaiting_place` stops the retirement while the where question is unanswered. A practice the model gives itself stands; one it rewords is replaced by the client's text.

## Lessons

- A scripted eval that starts at message 1 diverges before it reaches the stage under test. Use `start_in` for stage level scenarios.
- Per style client wording is `reply` as a map by style in `somatic.md`; `repairs.reply_for` resolves it everywhere it is read.

See [[panic-and-already-answered-stages]].
