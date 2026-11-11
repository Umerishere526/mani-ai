---
type: journal
date: 2026-11-10
tags: [journal, safety, state, client-test]
---

> Superseded 2026-11-10 — see [[safety-is-the-models-judgment-2026-11-10]] (the signs and their rules)

# Safety keeps the signs that opened it (2026-11-10)

Lolly's chat and muhammad's own test: chest tightness, fear of the doctor. Mani said "move away from anything you
could use to hurt yourself" in every reply, apologised for it and repeated it in the same reply, and did not let go
after "I am safe" until he typed STOP.

What was wrong was the shape from [[safety-is-a-state-2026-11-06]], not a line:

1. **The state forgot why it opened.** clear, open, unsafe. A medical emergency was a danger sign, so it reached
   `unsafe`, whose one text was written for suicide risk and said "in every reply".
2. **A sign reported again raised the state again.** The model reads "with the whole conversation", so it reported
   the same sign each turn, and `signals & DANGER` was tested before the safe answer. Nothing could settle it.
3. **Nothing defined "settled" for a symptom.** "I'm safe" answers nothing about chest pain.

Now the thread keeps the signs, code picks Mani's sentences from them, and what settles a concern depends on the
sign: a step for danger now, a plain "I'm safe" for the rest. Spec `docs/specs/0007-safety-follows-what-they-said/`.

Lessons:

- The model knew the self-harm line was wrong (it said so) and repeated it, because the instruction said every reply.
  A sentence the model must not say is left out by code, not forbidden in the prompt.
- My first draft of the replacement text dropped "never say you will stop asking or drop it" and added "shorter and
  softer", which is what Mani did on 11-06. The `architecture-reviewer` caught it. When replacing a text, carry its
  guard across word for word.
- The reviewer also stopped the indirect phrases leaving the screen: a screen hit answers someone at their message
  limit and gives the fallback when the model fails, which detection by the model alone does not.
- Research (clinical guidance, other apps): nobody publishes a rule for when a concern is settled, or for not
  repeating. The settling rule is ours; the client has not approved it yet.
- Not solved: the thread does not store which steps they have taken, so "never ask for a step taken" rests on the
  model. Measure it in the live check before believing it.

Found on the way, not fixed: the suite reads the local `backend/.env`. With `CRISIS_BLOCKS_CHAT=true` and
`REASONING_EFFORT=low` there, four safety turn tests and two `test_chain.py` tests fail on `main` as well. Run with
`CRISIS_BLOCKS_CHAT=false REASONING_EFFORT=high`, or make the tests' settings ignore the file.

Same day, muhammad's local test: "i think i want to die", then "no i am fine", "i dont need anyone", and Mani asked
him to contact someone in every reply with two or three questions each. The screen mapped "want to die" to intent, and
I had made "reach a person" the step that settles intent. A step that can only be refused is not a step: it traps
the person exactly as the chest chat did, from the other side. Now only dangers with a concrete step (means, plan,
acted, harm to others, a symptom now) need one; "I'm fine" or "I want to chat" settles the rest, reaching someone is
offered once, and one question per reply. muhammad: chatting is itself what keeps them from acting.

Third local test the same day: settled once help was called, then reopened on "no i want to remove the feeling of
being not enough" with the chest and the wish to die from earlier, and stuck. The second fix to the same class
(signs re-read from history); the first fixed it only while a concern was open. Not fixed with a prompt line
("only this message") because every safety failure so far was a prompt-only rule: each sign now quotes its words,
and code checks they are in the message. The rule of thumb from 2026-10-22 again: what must hold is held by code.

Related: [[failure-classes-from-later-branches-2026-10-21]].
