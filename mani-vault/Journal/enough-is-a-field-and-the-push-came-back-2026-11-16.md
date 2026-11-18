---
type: journal
date: 2026-11-16
apps: [backend]
tags: [journal, offers, cadence, design, lessons]
---
> Superseded 2026-11-17 (code pressing the move to a framework: the model decides when to offer) — see [[flat-replies-were-the-model-2026-11-17]]
2026-11-16

# "Enough" is a field the reply writes, and the push to the framework came back

Same day as [[offer-floor-and-coverage-removed-2026-11-16]], which took out the floor, the areas and both pushes.
muhammad then tested locally in Directive: the person's third message held what they tell themselves, the reply
judged "exploring" for thirteen replies, the move was then allowed on eight replies in a row and never made, and he
typed "framework?" at his 23rd message. The live pass of the `moves` set agreed: a first offer in 5 of 17
conversations, at their 9th message in the middle.

## What it showed

- **A hold and a push are separate things.** The floor and the areas held the offer back and deserved to go. The due
  naming and the due move pushed it forward, and they went in the same change because they were wired to the areas.
  With no push the model keeps asking: the form makes "ask one more question" the easy way out of every reply.
  This is failure class 8 again ([[failure-classes-from-later-branches-2026-10-21]]), the "then too late" half, and it
  had been seen on 2026-10-16 and on 2026-11-11 already ([[audit-of-the-safety-branch-2026-11-11]], the stall fix).
- **The 2026-11-11 push did not fail as a push.** It failed on what fed it: the map from the reading that lands a
  median 18.8 s after the reply, and a due move with no way to wait when the person was frustrated.

## What was built

- `known` in the chat reply (what happened, what they tell themselves, what it does to them), kept once known. All
  three and no core said back: the next reply is told to say it. A core said back that stands: the reply is told to
  move.
- Code never sends an offer in a reply that reports `frustrated`. That field had no reader until now.
- From the architecture review the same hour: a reply that reports the core named without its words has not said
  it; the "say it back" line never quotes what is known, because a rejected belief would be pushed back at them; a
  step that is due is not sent beside "Explore next" or "Worth exploring"; what their message did (`asked_for_help`,
  `frustrated`) is written before the reply is planned, not after its text.

## Lessons

- **Port a redesign with its measurement, not ahead of it.** I brought the 0008 work over whole on the strength of
  its tests. Its own review named this row as the riskiest, and no live run had been made after the removal.
- **Read the traces before the transcript.** `heart`, `may_move` and `checking` per turn answered "why no
  framework" in one query.
- **Two reviewers disagreed on one field.** The advisor asked for a closed-set reason on a reply that does not move;
  the architecture reviewer said it is an escape hatch that silences the count. The run's own traces decide it.

## Open

- A real situation with nothing they tell themselves about it: nothing becomes due.
- The reply after a first reply that already named the core can offer, which is their second message. The prompt
  tells the first reply not to name it; no code holds it.

## Later the same evening: what the runs after the fix showed

Three live passes of the `moves` set in Directive (one run each, so each is a reason to look, not a verdict):

| | first offer in | at their message |
|---|---|---|
| before the fix | 5 of 17 | 9th in the middle |
| with `known` and the two pushes | 13 of 18 | 8th in the middle, 4th at the earliest |
| after the review's changes | 10 of 18 | 8th in the middle |
| final state: short note, asking for help not kept as a state | 11 of 17 | 8th in the middle, 5th at the earliest |

The three lost between the last two were not the loop the architecture reviewer predicted (a reason to wait on every
turn). They were a state I had kept alive that afternoon: "they asked what to do" was stored on the record and said in
every later note, so once someone asked, every reply was a "practical" one, the same suggestion came back to "yes"
and to a belief said outright, and the move never came. Suggestions-when-asked had been widened to every style the
same day, which is what turned an old line into a trap.

- **A judgment about one message must not become a state.** `asked_for_help` is about their last message. Stored and
  repeated, it described every message after it.
- **Read the transcript of the conversations that changed, not only the counts.** The count said "3 fewer offers";
  the transcript said why in two minutes.
- **The note was the other half.** Rebuilt for his chat, it carried a 3,167-character picture, the question the last
  reply had planned, and areas named both explored and worth exploring. The plan line, the explore lines, the funnel
  and the long picture are cut; the note now carries the core, what they want, insights given and what recent replies
  added.

The final pass: 11 of 17 (one conversation stopped on a failed call). The six without an offer are the four safety
conversations, the goodbye, and the one where the person is frustrated with Mani to the end. No due step was missed,
no offer answered a correction or frustration, and "the same question asked again" read 0 of 126 (3% before). Still
true in that pass: 85 of 150 chat replies chose `acknowledge`, and the reply gives a median 31 words before its
question, so the listening turns are as thin as they were.
