---
type: journal
date: 2026-10-12
tags: [journal, prompts, offers, design, lessons]
---
> Superseded 2026-10-13 (the slot test fit rule and `due` checking understanding: the fit line now comes from the client's cheat sheet and the check gates the offer) — see [[client-sample-voice-and-confirmed-check-2026-10-13]]
> Superseded 2026-10-13 ("Finding the fit" and `to_find_out`: removed, one question rule instead) — see [[running-understanding-and-one-question-rule-2026-10-13]]

# General judgment over case patches (2026-10-12)

muhammad's objection, after a second fix for the coworker offer: "we will have thousands of use cases;
we cannot add them all to the model; it must tell issue, feeling and situation apart itself." The
architecture reviewer agreed about the runtime, though not about `scenarios.json`, which never reaches
the model (only `scripts/scenario_check.py` reads it).

## What the review found

- About 1,000 of the roughly 6,000 static prompt tokens were case patches, duplicates or contradictions.
  ABCDE's fit rule was written in three places that disagreed. `mani_base.md` banned the word
  "examine" while the client's Reflective offer uses it. Rules for paused frameworks (practical
  options, the lost wallet case) were still in the prompt.
- Two cues pushed the model to offer. `[ctx]` said `offer_window: open` every turn from message 3
  (18 of 18 offers landed exactly there, see [[offer-window-owned-by-code-2026-10-12]]). At message 5,
  `due` forced "the nearest", which is always ABCDE because it is the only active framework.
- Dead code paths built from test lines: 17 imminent action phrases and a grief veto list, both
  pointing at paused frameworks.
- My own fix that day ("what they keep doing is not enough") was another case patch
  ([[open-window-read-as-offer-now-2026-10-12]]).

## What changed (scope feature 15)

- One home for the fit rule. Each framework's `central_indication` uses a slot test: it fits once its
  offer's `<what they are going through>` can be filled from their own words without adding a feeling
  or belief.
- Cut from the prompts:
  - the word lists
  - the offer slot's worked examples
  - the paused framework rules
  - the reasoning step 1 duplicates
  - "nearest"
  - "never ask what is at stake"
  - the crisis field's quoted examples
- "Finding the fit" now says listen for these, not ask for them from the first message.
- `[ctx]` no longer sends `open`. `due` says to offer if a set fits, and otherwise to check
  understanding.
- Deleted `eligibility.py`, `reply_checks.ruled_out` and `Registry.activations`, the `candidate`
  block in `[ctx]`, and the grief phrase list. Behavioral Activation keeps grief as a principle in
  `to_find_out`.
- `scenarios.json` is grouped by behavior, with `offer_from` and `offer_by` that
  `scenario_check.timing_flags` checks. Before this, the check only saw offers before message 3.

No baseline run was made (muhammad's call). The run after the change is still owed.

## Lessons

- Before adding a prompt line for a bug, look for the line that caused it. Here every cause was a
  line already in the prompt.
- One copy of each rule. A rule written in two places drifts, and the model gets the disagreement.
- An eval that can't express the expectation can't catch the bug. Put the expectation in data the
  checker reads, not in a `source` sentence.
- Code still owns the floor (message 3), cooldowns, the client's fixed wording and safety. Meaning
  belongs to the model. Feature 16 moves the remaining text parsing (offer line, body place, decline)
  into reply fields.
