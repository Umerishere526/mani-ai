# One picture for the chat and the framework (2026-10-27)

The tester's review of 2026-10-27 and muhammad's 28 points come down to: Mani understands but does not know what to
do with it. The first root cause muhammad named: the chat's understanding (feelings, heart, case) stopped at the
framework's door, and the framework's step store (`stages_known`) held only each step's words. A new belief at D, a
feeling named before the offer, a coworker's behaviour that is real and not a thought: none of it reached the other
side.

Phase 1 of the plan (branch `feat/understand-then-help`): one picture, updated on every reply in both paths, stored
in `threads.understanding.picture`. Beliefs are marked `thought` or `happening`, so later phases can keep a real
situation out of reframing. `shift` and `quiet` are recorded now for the turning point in phase 3. Steps already
passed are synced from the picture; steps ahead stay "judged when reached" (2026-10-13 rule), now from the whole
picture.

Not yet: framework turns still use `mani_base.md` and `[ctx]` (phase 2 moves them to the chat engine), and the one
short line saying an earlier step changed comes with that move. Related: [[heart-of-it-replaces-the-three-steps-2026-10-26]],
[[story-before-guess-2026-10-26]], [[abcde-walk-owned-by-code-2026-10-13]].

## Phase 2, same day: the framework speaks in the chat's voice

The prompt is now three rows: `voice` (who Mani is, how a reply sounds, the three styles, Lolly's two chats),
`conversation` (how the chat moves, the heart of it, the check) and `framework` (how a stage turn goes as a
conversation). Stage turns no longer read `mani_base.md`, `response_format.md` or a style file. The `not_yet` line
in `walk.next_line` no longer asks for "two or three possibilities" every time the walk stays, which was the
options-every-turn pattern the reviews called a questionnaire.

Changed behaviour to watch: asking for a framework they stepped out of now offers it again with Try it rather than
starting it in the same turn. The chat path would otherwise have to judge stage A itself.

## Phase 3, same day: understanding turns into helping

`helping` on the understanding record is the turning point; `converse.turned` sets it from the reply's
`asked_for_help` and `frustrated` flags, the picture's `quiet`, three short answers in a row, or a yes to a check
about a real situation. Two short answers in a row was tried first and fired on "yes" then "I don't know", which are
ordinary answers; three is the floor. The help move is code's (`HELP_MOVES`, kind of problem x style), the words the
model's. A real situation never gets ABCDE or Thought Reframe: the check's yes turns to help in the chat. To watch
live: whether the model reports `problem_type` early enough for the move to be right, and whether Supportive's
check-in ("keep talking or look at what might help?") comes too often.

## Phase 4, same day: stepping out, and asking before the body

A framework that stops helping now says so and offers to step out. The reply reports `framework_fit`, and code
counts stalls on the stage in force; the subtle part was what counts as a stall. Comparing only the picture's
`shift` missed turns where their words for the stage changed, so `walk.after_turn` compares the stage's words with
the state before the turn as well. Talking something new through is never a stall.

The body check-in now asks first (`somatic_ask`). It slots in as the first somatic stage, so the walk leaving the
last stage lands on it with no special case; `body.entry` became `body.ask` plus `_opening`, which the yes reaches
with the place their feeling points to. One integration test still expected the old Reflective wording from before
phase 3's voice rewrite and was fixed along the way. To watch live: whether Not right now feels abrupt going straight
to "did our conversation help", since the client's script has no line for declining.

