---
type: decision
status: accepted
date: 2026-10-01
apps: [backend]
tags: [decision, ai, prompts, conversation]
---

# ADR-008: Every reply before an offer asks a question

**Status:** accepted by muhammad, 2026-10-01. Amends [[ADR-006-a-turn-may-be-redrafted-once]]: a missing question gets up to two
redrafts, not one.
**Affects:** backend

## Context

muhammad's own chat of 2026-10-01 (a colleague questioned two recommendations in front of the team)
had Supportive replies that only comforted: "It's okay to feel that way, and I'm here to listen." The
person had to push the conversation on themselves, which must never happen.

Measured on the same chat, three runs, all styles: 8 of 47 replies before an offer carried no
question (Supportive 4 of 15). Across saved runs of other scenarios it was 18 of 88 in Supportive.
Two causes:

1. **The prompt allowed it.** Its table of reply shapes listed "Mirror and hold: no question",
   "Presence only: no question" and "Honor and follow: may need no question", with nothing limiting
   them to after a framework.
2. **Nothing in code checked.** The only check was an eval validator.

The same chat exposed a bug in [[ADR-006-a-turn-may-be-redrafted-once]]'s feeling word check: the person
typed "emberessed" and "embarrased", and Mani's correct spelling was redrafted and trimmed as a feeling
they had not named.

## Options considered

### Option A — Prompt only
- Pros: no code, no extra calls.
- Cons: the prompt already said every reply ends in a question while understanding, and Supportive
  broke it one reply in five. Prose alone did not hold.

### Option B — Redraft a draft with no question, up to twice
- Pros: the person never reads a reply that asks nothing. The same mechanism as ADR-006.
- Cons: a second and sometimes third call on those turns.

### Option C — Append a fixed question in code
- Pros: no extra call.
- Cons: a generic question breaks "no generic check-ins" and cannot follow what they said.

## Decision

Option B. Before an offer, a draft with no question mark is redrafted, told to end with one question
that follows what they said and moves toward which set fits. A second redraft is allowed for this
reason only. The question is not required:

- while a framework's questions are running (each stage asks its own),
- on a safety concern,
- in a reply that offers (the offer carries its own permission question),
- when the person has asked only to be listened to (`their_last: heard`: "I just need to get it out",
  "please don't ask me anything"), where reflecting without a question is the right reply.

The prompt's shapes table now confines the question free shapes to after the questions or to `heard`.
The feeling word check treats a misspelling of their word as their word: a similarity test and a
consonant skeleton test, long words only, so one feeling is never taken for another.

## Consequences

- Measured after: 1 of 39 replies without a question in the same chat (Supportive 0 of 7, Reflective
  0 of 18); the other 4 across other scenarios were the `heard` exception working. "embarrassed" was
  flagged 0 times, from 10.
- Cost: redrafts were 19% of replies in this chat (feeling words, missing question, early offers), the
  hardest case measured; other scenarios were 7%. ADR-006's watch line of about 10% applies to real
  traffic, not to this chat.
- The `heard` list is a handful of phrases. A person who asks to be left alone in other words gets a
  question; the list grows from real transcripts.
- Reversing it: drop the `needs_question` argument in `orchestrator.py`; the prompt rule still stands.

## Links

- Amends: [[ADR-006-a-turn-may-be-redrafted-once]]
- Related: [[ADR-007-offers-follow-confidence-and-the-closest-fit-is-owed]], [[framework-files-what-the-model-actually-reads]]
