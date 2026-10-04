---
type: decision
status: accepted
date: 2026-10-04
apps: [backend]
tags: [decision, ai, prompts, conversation]
---

# ADR-012: Mani speaks plainly, and tone is the instructions' job, not the code's

**Status:** accepted, 2026-10-04 (muhammad). The reads are done and AC-9 is not met; it is recorded below, and scope row 6 and a later ADR address it.
Supersedes [[ADR-008-every-reply-before-an-offer-asks-a-question]]. Amends [[ADR-006-a-turn-may-be-redrafted-once]]
(the feeling word redraft and the sentence trim go) and [[ADR-011-first-stage-by-its-own-test-and-one-draft-when-asked-to-pick]]
(the repeated question redraft goes; its prompt rules stay). Spec: `docs/specs/0002-mani-speaks-naturally/`.
**Affects:** backend (`context.py`, `redraft.py`, `orchestrator.py`, `repairs.py`, prompts, `scripts/eval_client_style.py`)

## Context

The client finds Mani robotic, too full of questions and repeating "I hear you". The base instructions had grown to 499
lines, and code redrafted any reply that skipped a question (ADR-008), named a feeling the person had not (ADR-006)
or repeated a question (ADR-011), which pushed every reply into one shape. The client's own examples break some of
those rules. The numbers behind this are in [[natural-mani-build-2026-10-04]].

## Decision

- The base instructions are about 100 lines: who Mani is, how Mani talks, the three styles in what they do, compressed
  mechanics for offers, stages and endings. No example conversations, no dashes.
- A normal reply is one or two short sentences. One question at most, and a reply that asks none is fine.
- The redrafts for a repeated question and for no question, and the sentence trim in `repairs.apply`, are retired. The
  redraft keeps its offer reasons (too early, not allowed yet, ruled out, a due closest fit that is missing) and
  keeps one tone reason: a feeling word or a size phrase (`repairs.FEELING_WORDS`, `repairs.SIZE_PHRASES`) the person
  never used. Its notes never tell the model to ask a question, and a second draft that still fails is left as
  drafted, not trimmed. A turn with none of these is one chat model call. (muhammad chose this on 2026-10-04 after the
  prompt alone left 2 feelings in 36 conversations on two of three checks.)
- A message of three raw words or fewer is `their_last: short`, with `answering: "<Mani's last question>"` when there
  was one, so "yes", "no" and "I don't know" are read as answers. The fixed phrase list and `question_focus` are gone.
- Kept in code: the safety screen, offer vetoes, stage tracking, button checks, the name limit, the one time
  "Do I have this right?" guard.
- Tone is checked by `scripts/eval_client_style.py` and by a reader, not at runtime. The reads were done blind by a
  fresh model, with muhammad checking the flagged cases (his choice, a departure from the spec).
- The instructions name "It sounds like" and "It seems like" with "I hear you" as phrases never to use, say that while
  still understanding Mani does not say their words back as a statement but asks a plain question, and say what each
  style does (Direct leads, Supportive accompanies, Reflective explores). No redraft enforces any of this; muhammad
  accepted the rate that remains.

## Consequences

- Replies stop being forced into one shape. Measured against the baseline (36 conversations, three runs): questions in
  Mani's own words 0.59 to 0.48 per reply, stock phrases per conversation to about 0, long replies 1 to 0, dashes 2 to 0,
  offers 36 of 36 with 35 at exchange 2 to 4.
- Prompt alone left feelings never used at 0, 2 and 2 across three checks (baseline 0). With the feeling and size
  redraft restored it is 0 of 36. What it cannot catch is a meaning stated as fact ("stuck in a loop"), and "a lot"
  still reached 5 of 90 replies in the stress conversation, a phrase the client's own lines use. Asking the client
  whether it may stay is the open follow-up in the spec.
- Final check (three runs, 36 conversations): own questions 0.54 per reply, offers 36 of 36 at exchange 2 to 4, dashes 0,
  feelings and size phrases never used 0, "It sounds like" or "It seems like" 14 (baseline 49; 9 to 15 on the last
  checks, never zero). Restating 42% of eligible replies against 88% before the rule, and meaning stated as fact 0
  against 5, both read blind.
- Not met: the styles read as their own style 10 times in 18 (bar 15), after the two rounds the spec allows. Every
  offer says its questions are ones "you could go through together", so offers read Supportive in all styles; row 6
  rewrites that wording. The 0.3 stock phrase bar and the zero for the two new phrases are also missed.
- The instructions are short enough to read, so rows 6 and 18 start from something understood. Sections for offers and
  stages are rewritten again by them.
- One short prompt tuned on the lite model may not carry to the model row 35 picks; the check is re run there.
- Reversal: restore `redraft.reasons`' retired branches and the prompt from the commit before this change, re-seed.

## Links

- Related: [[natural-mani-build-2026-10-04]], [[client-style-check-baseline-2026-10-04]], [[overfit-prompt-and-natural-mani-direction]]
