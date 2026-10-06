---
type: journal
date: 2026-10-06
tags: [journal, frameworks, prompts, lessons]
---

# A yes to the stuck check was dropped, and the say back had gone

muhammad's chat on 6 October: "i feel pain", "emotional", then "i don't know", "i'm not sure" twice, Mani asked "Are you feeling stuck?", they said "yes", and Mani answered only "It can be hard to put things into words right now." No offer, no question.

## Why the offer vanished

- The yes turn made two calls, so a redraft ran; the input grew by about 200 tokens, which is the stuck offer lines reaching `[ctx]`.
- The words check in `router.kept_facts` drops any quote under two words. On the yes turn the obvious quote for `stuck` is "yes". Dropped, so `fit.pick` was None, the redraft was told "offer nothing", and what was left was the offer's lead line.
- The integration test for this route scripted the quote "dont know cant think", so it passed. **A scripted fact should be what a real model would quote, not what makes the check pass.** The test now runs with "yes" too, and failed on the old code.
- The facts were not stored anywhere I could read, and the server log was in muhammad's terminal. They are now kept on the call row (`admin.llm_calls.facts`, ids and notes only). Next time, query that first.

## The say back

The base prompt said "do not say their words back as a statement" while understanding. The model obeyed by asking bare questions, which lost what the client's "Good, Acceptable, Bad Conversations" document calls the Mani Standard: one short line in fresh words that adds (two things they said put together, or what is still going on), then one question. The line now asks for that in general terms. No sentence from the document went into the prompt, on purpose: muhammad said not to overfit, and [[measure-before-tuning-prompts]] found that a prompt's own example sentences come back near verbatim.

Still to check on a real run: whether the line turns into generic validation ("That is hard"), which the document marks as weak.

Related: [[ADR-018-a-stuck-person-is-offered-abcde]], [[questions-easy-to-answer-old-mani-chat-2026-10-05]], [[overfit-prompt-and-natural-mani-direction]].
