---
type: journal
date: 2026-11-10
tags: [journal, safety, design, client-test]
---

# Safety is the model's judgment, held by code (2026-11-10)

In one day the sign-based design ([[safety-keeps-the-signs-that-opened-it-2026-11-10]]) needed five fixes, each in a
new place: a medical sign on the suicide script, "want to die" read as intent, a sign re-read from history, a step
that could only be refused, and a step taken but never reported done. Two more chats showed the pattern:

- "I can't spend another day under this roof", then "I mean my workplace": Mani wrote "thanks for clarifying, I
  misunderstood" and asked about hurting himself again, because the state said open.
- "I might hurt him", then "he isn't near me, my friend is with me and stops me": Mani wrote "I'm glad your friend is
  helping" eight times and kept the concern open for twelve turns, inventing new checks.

The model understood both conversations. The rules around it overrode that understanding. muhammad: "you are an LLM,
you can read the chat and access what the user is trying to say" (said of Mani's call, not of Claude).

So the model now answers one question each turn from the whole conversation: is anyone in danger now (none, unsure,
now). Code keeps only what the model cannot be trusted with: a refusal never settles a concern (the 11-06 failure),
and the phrase screen holds a turn while the model judges it (fallback, limits). The re-read-from-history class goes
away because the question is about now, not about which words this message contains.

Also learned:

- My "ask the one thing still missing" line put a safety question in every reply while a concern was open (5 of 5
  in the roof chat; main asked 3 of 5). main's "listening more than asking" is back.
- I told muhammad main was not like this. A like-for-like run showed main opened on the same idiom and never left
  the bullying crisis in 14 turns. Run the comparison before saying what main does.
- When the same area needs a third fix, stop and change the design. I reached five before saying so.

Not yet known: how consistent the judgment is between runs. The live runs of the four chats and the scenario groups
are the test.

Related: [[safety-is-a-state-2026-11-06]], [[failure-classes-from-later-branches-2026-10-21]].

## Same day, afterwards: three more things the chats showed

- **The model judged "unsure" on Mani's own unanswered question.** After "I mean my workplace" it stayed unsure for two
  more turns, its reason "they have not answered whether they might hurt themselves". The description of unsure counted
  a question of Mani's as a sign. Now unsure needs their own words to speak of danger ("never a hunch"), and the voice
  prompt says the same. Eight live chats after: idioms and low mood raise nothing, real hints and explicit statements
  still do.
- **Replies that ask nothing stall a chat.** manasa's "mainly driven by questions" (2026-11-05) removed the question
  check and added shapes "with no question"; muhammad's father chat ended on "We can stay with the shock for now". The
  explored-areas fix (areas accumulate) had removed the false nudge that used to force a question on main every turn,
  which exposed it. Now every chat reply carries a `forward` question, held to a trailing question mark by the provider
  as it is generated; pydantic does not check it (a ValidationError costs a second call and can lose the message).
- **The ledger vanished while a concern was open inside a framework**, because it was built only from the stage walk.

Lesson: a rule that exists only as a sentence in the prompt fails in the chats that matter. Each of these moved into the
reply's own structure or into code that checks evidence.

## Review findings worth keeping (Opus, 2026-11-10)

- **A migration can pass on every empty database and fail on the first real one.** 036 updated rows to the new states
  before dropping the check that refused them; every database I ran it on had no `open` or `unsafe` rows. It is now
  proven on a scratch database at migration 035 with old rows and old rewind snapshots planted. A migration that moves
  data needs rows to move.
- **A refusal must hold the rank, not only block a clear.** `declined` stopped danger going to clear but let it step
  down to unsure, which drops the emergency instruction. A judgment code does not know, or that is missing, is no
  judgment: it never clears a concern.
- **Two live-only defects a unit test could not see:** the model asked the same question in its text and again as the
  question after it (a third of replies), and the framework gate was told what was unexplored but nothing made the
  question carry it. Both found by replaying real chats, not by the suite.
