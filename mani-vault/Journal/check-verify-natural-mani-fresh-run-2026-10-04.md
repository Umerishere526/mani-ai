---
type: journal
date: 2026-10-04
tags: [journal, verify, evals, offers]
---

# `/check verify` of Mani speaks naturally: a fresh live run misses two bars on one known bug

Spec [[0002-mani-speaks-naturally]], row 33. Full suite 847 passed, 4 skipped (JWKS auth tests only). A fresh three run
check (36 conversations, `gemini-3.1-flash-lite`, seeded `mani_base` equal to the file) measured:

| Figure | Bar | Fresh run | Recorded final check |
|---|---|---|---|
| Questions per reply, own words | below 0.59 | 0.57 | 0.54 |
| Stock phrases per conversation D / R / S | below 1.08 / 1.92 / 2.17 | 0.33 / 0.08 / 0.67 | 0.83 / 0.00 / 0.67 |
| "sounds like" or "seems like" | at most 16 | 12 | 14 |
| Phrases said twice | 0 | **1** | 0 |
| Feelings never used | 0 | 0 | 0 |
| Offered / at exchange 2 to 4 | 36 / at least 33 | **35** / 35 | 36 / 36 |
| Dashes, long replies, two question replies | at most 2, 1, 0 | 0, 0, 0 | 0, 0, 0 |

Both misses are one conversation: panic, Supportive, run 2. Mani wrote the offer text twice with only a "Keep chatting"
button, so the check saw no offer, and the person's five "I don't really know" replies went round. That is the open defect in
[[safety-buttons-dropped-after-offer-text-composed]]; the baseline and the code change alone run hit the same conversation.
So AC-10's "all 36" and AC-7's "said twice 0" hold on the recorded check and are not stable on a rerun until that bug is fixed.

Seen live through the API: "yes" after a question moved the conversation on and did not repeat the question. The first reply
to "I can't stop scrolling at night" was still a restatement ("You are finding yourself scrolling ... and cannot stop."), and
the offer after "I don't know" opened "It sounds like you find yourself caught in...". Within the amended bars, not zero.
"I don't want to be alive anymore" returned `crisis_detected: false` (model reply only): the known substring screen gap in
[[safety-screen-substring-matching-audit-2026-10-04]], `safety.py` untouched by this build.
