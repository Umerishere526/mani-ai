---
type: journal
date: 2026-11-16
tags: [journal, offers, spec-0008, conversation]
summary: "The offer floor, coverage gate and gap lines were removed together; one rule remains: the heart said back uncorrected."
---
> Superseded 2026-11-17 (the one code rule on when Mani may offer, once the heart of it was said back: the prompt holds it) — see [[flat-replies-were-the-model-2026-11-17]]
> Superseded 2026-11-16 (the due naming and the due move were removed with the areas: both are back, driven by what the reply itself reports) — see [[enough-is-a-field-and-the-push-came-back-2026-11-16]]

2026-11-16

# The offer floor and the coverage gate came out together with the note's "gaps" lines

Spec 0008, D2 (muhammad): code keeps one rule on when Mani may offer a set of questions, that an earlier reply said
the heart of it back and it was not corrected. Removed on `feat/0008-one-conversation`: the five-message floor
(`context.CHECK_FROM`), the areas the reading's map had to cover (`converse.EXPLORED_BEFORE_MOVING`,
`still_to_explore`), the due move and the due naming (`converse.due`, `naming_due`, the `MOVE_` and `NAME_NOW`
lines), and `converse.gaps`.

Why `gaps` had to go in the same change: its lines told the model to hold its reading ("Hold it until they have said
what they came to say", "Never give one while they are still telling it") and `NAME_NOW` was the only thing that
ended the hold, once every area was explored. Taking out the areas and leaving the hold would have delayed the
reading, and so the offer, which is the opposite of what the change is for. A rule that pushes one way and a rule
that pushes back are one mechanism; remove them together.

What the first live pass showed before the change (18 conversations, Directive): the floor at five rarely bound. The
model said its reading back at their 6th to 8th message in most conversations and offered one message later. So the
prompt, not the floor, sets most of the wait, and the count to read after the change is the message of the first
offer.

Two things looked like bugs and were decisions:

- A safety concern cleared when the person changed the subject after refusing twice. `schema.SafetyRead.danger` says
  so on purpose (2026-11-10: going on about their situation after being asked is "none"). Read the field's own
  description before calling a state change a bug.
- I tagged that line as a refusal in the scenario file after seeing the run, then took the tag back: a count must
  not fail something a Decision in force calls intended.

Left for muhammad: the decline count. Anything but a yes or a question at the offer is stored as declined, also
plain moving on, so dropping the count with "a declined set comes back only when they ask" would end offers for
anyone who talked past an early one.

- Related: [[exclusive-moments-and-forced-questions-2026-11-16]],
  [[one-failed-call-lost-a-whole-scenario-run-2026-11-16]], `docs/specs/0008-one-conversation-many-moments/index.md`
  section 13.3.

## Same day, the stage walk

Three causes from the client's boss test, each reproduced in `review.md` and each now held by a test:

- **One text for two jobs.** The reply answered their message and opened the next stage in one `text`, and code put
  the letter line in front of the whole of it. A field of its own for the opening (`stage_text`) fixes the order by
  construction. Any model-written field that reaches a person must pass the same word guards as `text`: that is why
  `repairs.without_system_words` was pulled out of `repairs.apply`.
- **The instruction and the Decision disagreed.** `framework.md` said a stage stays while a part not yet opened would
  help; the `stage_answer` field said agreed "with or without more added" and explore "for one reply", and code turned
  explore on an asked stage into answered. The field description is an instruction too. When behaviour contradicts a
  Decision, read the field descriptions before the prompt.
- **A rule kept, its guess removed.** "A message that asks something never moves the stage" is muhammad's rule of
  2026-11-05. The question mark half is something code can see; the "opens like a question" half was a guess at
  meaning and held "how he treats me". The guess went and the rule stayed.

One protection was kept on purpose: a stage that waited for one missing part and got it is answered whatever the reply
called it. Removing it would have brought back the career chat of 2026-11-03, where E stayed after the path was given.

## Same day, manasa's three Reflective tests: what an offer leaves behind

Reproduced with `converse.check_allowed` on hand-built threads before any change:

- After "I'm not sure a framework will help", the reply reported `wants_other`, which code handled as a correction of
  the offer (`understanding.corrected`), and a correction had no wait. ABCDE came back two replies later.
- A finished set did not close anything: `may_check` returned True as soon as a reading was said back again.
- The chat note said nothing about a finished set, and its reading was cleared on purpose, so the chat went looking
  for the reading again and re-asked what the framework had just settled.

The rule that replaced three counts: an offer is possible only when nothing was offered yet in the conversation, or
they corrected what the last offer said back. Everything else is closed until they ask. It reads worse than it is: a
decline already had a way back (`back_to_framework`), and nothing else was lost.

Lessons:

- A label the model picks (`wants_other`, `corrected`, `moved_on`) decided how long the person was left alone. When a
  code path gives one label a friendlier rule than its neighbours, the model's choice of label becomes the bug.
- "Clear the reading so we do not check again at once" fixed a re-check and caused a re-exploration. When state is
  cleared to stop one behaviour, ask what will read the empty state next.
- A missing fact looked like bad judgment. The chat could not know a set had been finished; no prompt wording would
  have fixed that.

## Same day, muhammad's decisions on what had been left to the client

He took the "needs Lolly" points himself. What was built from his answers, and what each one taught:

- **A stage already answered is talked through, not confirmed, in a reply of its own** (`walk.ALREADY_ANSWERED`). The
  first proposal merged A, B and C into one recap; he refused it: each stage individually is a must.
- **Directive helps in the chat when they ask what to do; the other styles do not.** The note gives Directive the
  fact only (`converse.WANTS_TO_MOVE`) and the prompt says what to do with it.
- **A no gets Mani's own reply.** The client's Keep chatting line is gone from code and content.
- **The help screen comes on the answer.** `pause.pauses_now` needed the thread to be in danger already, so an asked
  person whose answer meant danger got one more reply first. Now any open concern that becomes danger pauses.
- **Unclear words get a calm question and no number** (`context.UNCLEAR_WORDS`).

Two checks that caught me:

- `test_no_safety_text_names_a_kind_of_danger_they_did_not_raise`: my first wording for the unsure guidance said "want
  to die ... end their life" inside [ctx]. Safety text that names a kind of danger puts it in front of someone who
  never raised it. Say "what worried you".
- `test_an_open_offer_turn_costs_less_prompt_than_before_the_structured_fields`: the three additions of the day pushed
  one turn's prompt over its old figure by 190 characters. A size test is what makes "cut, never add" real; the fix
  was to tighten the new lines, not to raise the number.

Kept by him, against the client's request: every reply ends on a question, also after a goodbye (asked four times
now), and the 15-minute lock with its countdown.
