---
type: journal
date: 2026-10-21
tags: [journal, thought-reframe, content, client, lessons]
---

# Thought Reframe was the old spec plus one example, not the client's five steps (2026-10-21)

muhammad pasted the client's Thought Reframe text and said the phases and what they represent were wrong. The
client's document was already in `docs/client/docs/Thought_Reframe_Framework.md`; the content file had been moved out
of `paused/` on 2026-10-21 without being checked against it.

## What was wrong

- Six stages (thought, significance, facts, alternative, reframe, closing) from the older six-frameworks spec; the
  client has five steps and ends with one acknowledging sentence, then the somatic check-in.
- Titles that were not the client's step names, and a "facts" stage (supports, does not, unknown) where the client's
  step 3 is why the thought feels convincing and whether anything complicates it. "Facts" also nudged the model to
  debate evidence, which the client's step 3 warns against.
- Asks and replies written about one friend's silence ("The silence allows more than one interpretation"), which read
  wrongly for any other thought. A test now fails if one situation's words come back.
- The last step required "more balanced and hopeful" (muhammad, earlier the same day); the client says it does not
  have to be positive, only believable. muhammad chose the client text. See
  [[the-walk-never-skips-2026-10-21]], whose "more hopeful" part is superseded.

## What changed

Five stages (`thought`, `painful`, `feels_true`, `alternative`, `replacement`) titled with the client's step names; no
`closing` (code sends one short sentence after the last content stage, then the body check-in, as for ABCDE); step 3
asks what makes it convincing first and whether anything complicates it second, using the gap mechanism built for
ABCDE's D ([[dispute-halves-tracked-in-code-2026-10-21]]); selection rule from the client's note added to the
ABCDE-or-Reframe distinction. No code changed.

## Lessons

- A framework moved out of `paused/` needs the same read against the client's document that ABCDE got, not only
  `missing_for_activation`, which checks fields exist, not that they say the right thing.
- Example-bound content passes every structural test. Check generic content for the example's own words.

To watch in the first live run (needs muhammad's yes): step 3 asked as two separate questions, the replacement
accepted when it is cautious or partial, and ABCDE not chosen over Reframe only for voicing a troubling thought.
