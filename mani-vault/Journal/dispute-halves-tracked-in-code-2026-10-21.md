---
type: journal
date: 2026-10-21
tags: [journal, abcde, dispute, feeling, stages, lessons]
---

# D's two halves are remembered by code, and the feeling underneath stays in every stage (2026-10-21)

muhammad's Supportive run, the sister who keeps asking to borrow money. Two things went wrong after A.

## The feeling dropped out after A

The check confirmed guilt about refusing, plus worry she would struggle or feel let down. A said it back with the
situation. B confirmed only "you feel you should help because she's your sister", and the person had to say the guilt
again. D's six turns were each built on the last sentence, which was about family loyalty.

Cause: only A's `reach` told the model to say the feeling underneath. Every other stage said "about their_case", a
string where the feeling is one field, and `walk.CONFIRM_ASK` forbade another stage's part unless the stage's reach named
it. The old PORT-STATUS line that stage questions are not made about feeling had "reason unknown, muhammad to confirm";
muhammad reversed it. The rule went into the three shared strings (`walk.reach_line`, `walk.CONFIRM_ASK`,
`context._MEANING["their_case"]`) instead of one line per stage; A's own line was the first fix of this class, so if the
feeling drops again the next step is the `architecture-reviewer`, not a fourth place.

## D asked one half, three times, and never the other

D is one stage with one status. The `challenge` gap was read only when D was reached and `walk.merge` popped it on the
next update, so later D turns were the model's choice alone. It asked a loaded challenge first ("is there anything that
suggests being a caring sister doesn't always have to mean lending money?", which leans on a conclusion), got support
back, then asked "do you have enough information" three times in different words.

What changed: a partial stage keeps the part still to ask until it is known (`StageUpdate.gap`, ids from the stage's
`if_unclear`: `challenge`, `information`), `[ctx]` shows it, and D's boundaries say each question asks one part,
never says what it is for and never leads. The model words the question; the client's lines stay the fallback. Code
sending the client's line (which has no feeling) was rejected, for the reason in
[[stage-questions-from-the-conversation-2026-10-14]]. Related: [[the-walk-never-skips-2026-10-21]].

## Watch for in the first live run (needs muhammad's yes)

- The model reporting the wrong gap, or none, so D falls back to its own choice.
- B to E mirrors that recite the feeling each time instead of framing the question with it.

## Noticed, not fixed

E's possibility "decide to keep helping as your family always has" endorses the belief D had just examined. Check it
against E's "never as advice" boundary.
