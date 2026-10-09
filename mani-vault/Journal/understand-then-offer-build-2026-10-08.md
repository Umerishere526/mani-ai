---
type: journal
date: 2026-10-08
tags: [journal, offers, prompts, client, build, measurement]
---

# Building spec 0016: understand the issue, then offer

Spec: `docs/specs/0016-understand-issue-then-offer-naturally/`. Scope feature 22. Design: [[understand-then-offer-design-2026-10-08]].

## What landed

- `orchestrator.send` joins the model's checked `text`, a blank line, then the seeded offer; a blank line falls back to the seeded offer alone. One rule for every kept offer, including the re-offer after a typed question, whose answer used to be thrown away.
- E1 to E7 swapped one line each. Counts: `mani_base.md` 74 and `response_format.md` 71 lines before and after; 3391 words before, 3418 after, exactly as AC-6 pins.
- pytest 684 passed, 4 skipped (the JWKS auth tests), before and after the reseed; integration 147 passed, none skipped. The build adds and removes no tests.
- `client_job_decision` added to `eval_conversations.yaml`.

## The three runs (AC-8), recorded as measured, not rerun

`conversation_style` confirmed stored for each thread (direct, supportive, reflective) by a scratchpad wrapper around `_open_chat`, since the eval deletes its users at the end.

| Bullet | Direct | Supportive | Reflective |
|---|---|---|---|
| No restating before the offer | fail ("That sounds frustrating…") | fail (msg 1 and 2) | fail (msg 1 and 2) |
| First reply asks what the decision is | pass | pass | pass |
| Offer at message 3 or later | pass (3) | pass (3) | pass (3) |
| Bridge answers, no question, no recap | fail (an offer of its own) | pass | fail (recap, then an offer of its own) |
| After Try It asks nothing told | pass, but says their reasons back | pass, but says their reasons back | pass |

All three runs fail on bullet 1. Credit 18.50 dollars before the runs.

## What I learned

- **E1 to E4 did not stop the opening say back.** The model still leads with the person's feeling in a new word ("frustrated" became "frustrating"), then their words. The validator's `labelling` finding catches the feeling half. Lines still pushing that way, untouched by this spec: `mani_base.md` `Use their words` (line 18), `acknowledgment: receive what they said`, and the Supportive and Reflective style lines. That is my hypothesis for where to look next, not a measured result.
- **The timing half worked.** The first question asks what the decision is, and the offer waits until both sides are heard, in all three styles.
- **The bridge line drifts toward offering.** Two of three wrote "I can help you sort through…" or "We could sort through…" before the seeded offer, which already says the same. "No offer of your own" in E6 is not holding.
- **The seeded Structured Problem Solving offer says "practical next step" twice**, and with Direct's bridge, three times. Known from spec 0013 (in Open decisions), but it reads worse now that a bridge line sits in front of it.
- **The eval deletes its users, so verify per thread state during the run.** Wrapping `ev._open_chat` from a scratchpad script did it without touching the repo.

## Round 2 (E6 rewritten, E8 to E11), recorded as measured, not rerun

Counts 74 and 71 lines, 3424 words, exactly as AC-6 pins; the diff since round 1 touches only the five lines. pytest 684 passed, 4 skipped (JWKS), integration 147 none skipped. Credit 18.49 dollars before, 18.46 after the twelve runs.

The wrapper lives in the session scratchpad (`round2_run.py`): it swaps `orchestrator.get_settings` for a copy with `ai_debug_mode=True` (the composer keeps its own, so the system prompt stays production), wraps `orchestrator.send` to count `thread_response_styles` rows on the turn's own connection (the row is not committed until the block closes, so another connection would not see it), and wraps `ev._open_chat` to print `conversation_style`. Every thread had its style stored.

| Bullet, out of 3 | Direct | Supportive | Reflective |
|---|---|---|---|
| No restating before the offer | 0 | 0 | 2 |
| First reply asks what the decision is | 3 | 3 | 3 |
| Offer at message 3 or later | 3 | 2 | 1 |
| Bridge answers, no question, no recap | 0 | 0 | 0 |
| After the yes asks nothing told | 2 | 3 | 3 |

AC-8 fails. Restating replies, with shape and reasoning:
- Direct 1, msg 2, `gentle follow`: "the fear of getting it wrong is part of what's making it hard" (afraid → fear).
- Direct 2, msg 1, `warmth lead`: "That back and forth sounds frustrating." Reasoning: "They need to be heard".
- Direct 3, msg 1, `warmth lead`: "That sounds frustrating, especially when you think you've decided…" Reasoning: "room to explain the decision without being judged".
- Supportive 1 and 3, msg 1, `warmth lead`: "That sounds frustrating, especially when…" Reasoning: "a kind acknowledgment", "a little acknowledgment".
- Supportive 2, msg 1, `warmth lead`: "That back and forth sounds frustrating". Reasoning: "to feel heard".
- Reflective 1, msg 2, `mirror and ask`: "the fear of getting it wrong keeps the decision unsettled".

Lines that passed show what the client asked for: Reflective 2 "It's hard to feel you've reached an answer, only to find yourself questioning it again." and Reflective 3 "The hard part seems to be that choosing once doesn't quiet the question for long."

## What I learned in round 2

- **E9 changed the `warmth lead` line but not what comes out under it.** The shape is still chosen, and its first words are still "That sounds frustrating". The reasoning names a need to be heard or acknowledged every time. Lines still saying that, untouched by both rounds: `purpose` line 15 "Help them feel heard", `moves.acknowledgment` "receive what they said", and E3's "to be understood". Hypothesis, not measured.
- **The bridge got worse, not better.** Round 1 Supportive passed; round 2 is 0 of 9, every one ending "Would you like…?". The reasoning says "Offer it now" or "Offer it in a supportive way": the model thinks its text is the offer. E6 says the offer's words follow, but `response_format.md`'s `conversation_phase` ("then offer as offers says") and reasoning step ("Then offer or not") still frame the reply itself as the offer, and the model never sees the seeded text it is meant to sit in front of. Hypothesis, not measured.
- **One run per style hid the timing spread.** Round 1 offered at message 3 in all three; with three runs, Supportive and Reflective offered at message 2 in three of six, after "good reasons for both", before hearing what pulls each way. E5 did not change between rounds.
- **The regression scenario read warm enough but leans on meta lines** ("I won't assume what you mean", "I won't try to steer you"), and Reflective still retells. No offer in any style, which is right there.

Related: [[prompt-changes-cut-not-add]], [[client-response-feedback-2026-10-08]], [[measure-before-tuning-prompts]]
