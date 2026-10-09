---
type: journal
date: 2026-10-09
tags: [journal, prompts, questions, direct, lessons]
---

# Direct questions have no target (2026-10-09)

muhammad's Direct chat (manager criticised them in front of the office, insulted them, threatened
to fire them; their real worry, said at message 5, was colleagues laughing at them). Mani asked
for what they had already told it ("What did your manager say?", "Had he threatened to fire you
before?" right after "this time it was way too much") and chased the event ("What happened after
he said it?"). Nearly every reply opened by restating them.

## Evidence

Replayed each turn live with the real history forced (turns before k return the recorded
replies, turn k calls the model with `AI_DEBUG_MODE=true` so `reasoning` comes back), three runs
each. The model's own reasoning cites the `[ctx]` steer: "Direct style calls for one concrete
question; whether this has happened before would clarify the situation." The `question_focus`
meaning for Direct is a fixed list (what happened, whether it has happened before, what they have
tried), sent every turn, beside their message, with nothing about what is already known. It
outranks every "never ask for what they already made clear" line in `mani_base`.

"Most replies are one plain line and a pointed question" is read as "Direct style calls for a
brief reflection and a pointed question": that is the restating on every reply.

## What did not work (12 questions per variant)

| Variant | Redundant or event-chasing | Generic ("what's on your mind") |
|---|---|---|
| Original checklist | 9 | 0 |
| "about what is bothering them, never the event" | 1 | 8 |
| "what is happening for them, never more detail, never general" | 6 | 3 |
| Same, plus "list what they told you in reasoning, then the one unknown" | 4 | 3 |

The list did get written (the mechanism works), but the chosen unknown was still generic or
the event. Rewording swings between two failures: a checklist the model executes, or no target
and it falls back on a check-in. **The questions before an offer have no defined target**, since
they may not aim at a set (decision of 2026-10-08), and "their concern is clear" is defined
nowhere. All edits were reverted; raised with muhammad as a design question. The planned
ABCDE-only reduction would give the target for free (what happened, what they made of it), so it
bears on when to do this.

## Decided and tried, same day

muhammad chose to define the target: what happened, what about it hurts or worries them now,
whether they want to feel better or act. It lives in the `understanding` meaning in `[ctx]`, and
Direct's checklist and "one plain line and a pointed question" are gone. Replays (12 questions):
re-asking or event-chasing 9 to 0, restating 8 to 2. `scenario_check.py`, all scenarios, before and
after: Direct replies opening on their words 5/22 to 1/23, but "two styles ask the same question"
6 to 16, because the targets are shared by all three styles. The third target became its own
template ("Would you rather talk through X or work out Y?"), asked twice in one conversation even
with "only once" in the line, and the model holds the offer until it is answered.

## Fixed: scenario_check hang

`scripts/scenario_check.py` gathers every scenario-and-style conversation at once: 4 scenarios x 3
styles = 12 concurrent turns against `MAX_POOL_SIZE = 10`. Each turn holds a pool connection while
`client.complete` records its cost row on another, so it should deadlock with no error. Not run
against `scenario_check.py` itself; seen with the same pattern in a replay script (12 at once, no
`llm_calls` row for ten minutes; 4 at a time ran fine). Now bounded by `AT_ONCE = 4`; all 15
conversations ran.

See [[measure-before-tuning-prompts]], [[prompt-restructure-2026-10-07]].

## What muhammad saw next, and what changed (2026-10-10)

His next Direct chat (left out of meetings, wondering if his role is changing) read as "a questioning
jerk": a menu at message 1 ("Would you rather work out whether your role is changing, or focus on what
you could do next?"), then facts ("What else has changed?", "Has anyone explained why?"), no warmth. A
replay with reasoning tied each to a change of mine: the third target produced the menu, "the pointed
question alone" removed every human word, and with nothing left to aim at Direct audited the event.
His first message already held A and B of ABCDE, so the fit was there at once.

Decided by muhammad, not measured by model runs at his request: the third target is gone; questions
find the fit like a specialist (short, one thing, no menus), Direct is warm and never interrogative
(Lolly's own words), and a framework is offered as soon as it fits, from the first message, with no
`earliest_offer_message` and no router wait. The lesson: removing a bad behaviour by prohibition
("never restate", "question alone") swings to the opposite failure; say what to do instead.

## "How is it for them" made the questions abstract (later on 2026-10-09)

muhammad's Direct chat: left out of meetings, "I might be getting fired", "no shelter and food for
me". Mani restated him every turn ("Being left out has you questioning...") and asked "What is that
possibility like for you?", then "What would being fired mean for you?", which walked him into the
worst case. Replayed three times with reasoning: every reply cited "Direct style calls for a brief
reflection and one focused question" (the `_MEANING` recipe "a few words of your own that show you
understood"), and the questions came straight from my rule "ask how that part is for them, or what
it is like". A feeling question with nothing concrete in it becomes a hypothetical.

Fixed by saying what to ask instead: something real and present (what made them think it, what they
noticed, how they are with it today), never a hypothetical, and a fear of what may happen gets "what
has made you think so". Direct opens with the question. Basics (food, shelter, safety) get kind words
and "is this happening now". Replays: 3 of 3 asked concrete questions, none restated. scenario_check:
flags 10, 9, then 6 across three versions; "same question across styles" rose to 7 when all three asked
"what made you think it", fell to 1 once each style had its own target (Direct what made them think
it, Supportive how they are with it today, Reflective why it matters).

## Phrase lists removed (muhammad, 2026-10-09)

Removed: `classify_reply` and its four phrase lists (vague, unsure, correction, heard), the
`their_last` line and meanings, `FEELING_WORDS` with its stemming and misspelling helpers,
`introduced_feelings` and `without_feeling_sentences`, `SELF_JUDGMENTS` and the button length limit,
and `_PAIN`. Their rules moved into `response_format.md` as one reasoning step. "Only wants to be
heard" is now the draft's own shape (`NO_QUESTION_SHAPES`), so a no-question reply is not redrafted.

Cost to expect, not measured: nothing enforces "never name a feeling they did not" in code any more;
that is the client's rule, enforced only by the prompt, and `scenario_check.py` showed the model slips
now and then ("frustrating") even with the list. Kept on purpose: crisis screen, script and
internal-word stripping, `[ctx]` injection guard, imminent-action phrases, body route words, vetoes.
Check live before trusting: a vent message ("I just need to get it out") should still get no
question, and "I already told you" should still be taken at its word.

## Asked again what they had just said (2026-10-09, muhammad's meetings chat)

"I have been left out of a few important meetings, I am starting to wonder if my role is changing."
Mani: "What about being left out makes you think your role may be changing?" The meetings are the
reason; the question asked for the reason. My own Direct target ("what made them think it") caused
it: in a message that says X happened, so I wonder Y, X is already the answer to "what made you
wonder". Fixed generally, not for meetings: before asking, split the message into what happened, what
they conclude, what is still unsaid, and ask only for the last; Direct now asks what they have noticed
since. `scenario_check.py` has the scenario (`left_out_of_meetings`) and a flag, "asks what they
already said", for a question made almost wholly of words already said (measurement only, nothing at
runtime). 3 runs x 3 styles: 0 flags, none asked why.
Still seen: a Supportive turn 3 asked "How has the thought of being fired affected you today?", the
banned shape, so that rule only holds some of the time.

Correction (muhammad, same day): "how is the thought of being fired affecting you" is not a banned
shape. I had banned "how a fear or a thought is affecting them" as a hypothetical, but it asks about
something they said. The only problem is the word "fear" (or "worry") when they did not use it; the
same idea can be asked in their words. The rule now bans only "what would it mean / be like if" and
the feeling word, and allows "how is X affecting you". Lesson: I turned a feeling-word rule into a
ban on a whole question shape.
