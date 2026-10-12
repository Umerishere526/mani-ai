---
type: journal
date: 2026-10-12
tags: [journal, offers, abcde, prompts, lessons]
---
> Superseded 2026-10-12 — see [[general-judgment-over-case-patches-2026-10-12]] (the fit wording and the scenario: replaced by the slot test and the behavior groups)

# An open window was read as "offer now" (2026-10-12)

muhammad's chat-tester run (thread `b8abce1f`, Directive) typed Lolly's coworker issue as three short
messages: "always asking me for help", "I usually say yes", "I end up doing most of their work". ABCDE was
offered on the third, before any feeling or belief was said. That is R1 again.

## Root cause

Code did not choose ABCDE. `context.offer_window` opened at the person's third message, as designed in
[[offer-window-owned-by-code-2026-10-12]]. That note had already measured 18 of 18 offers landing exactly at
message 3, so the model treats `open` as "offer now". After that, whether ABCDE fit was left to the
prompt, and the prompt said yes to almost anything:

- `central_indication` matched a situation **or** a belief **or** an effect on what they do. "Doing most of
  their work" matched "what they do".
- `mani_base.md` said "offered whenever one is appropriate", "most situations have a practical side, and
  that alone is no reason to hold it back", and "offer once offer_window allows it". These were left over
  from the 2026-10-09 decision to offer from the first message. R1 replaced that decision, but these lines
  were never cut.
- The one line that should have held it back ("learned the first two things on its line", in
  `response_format.md`) is a rule that no code checks.

## What changed

The lines above were cut. ABCDE now fits only once they have said how it is for them, meaning a feeling or
what they tell themselves. The event stays optional, because the client's ABCDE document allows an
offer before it ("Situation 3: the activating event has not been established"). The first plan was to cut
"does not wait for the event" too. The client document vetoed that. Scenario `coworker_in_fragments`
reproduces the run. It has not been run live yet.

## Lessons

- When a decision is replaced, search the prompts for lines that argued for the old one. A count gate
  does not help if the prompt still says everything fits.
- Do not gate on a label the drafting model sets for itself ([[offer-window-owned-by-code-2026-10-12]]).
  That is why the fix is a narrower fit, not a "belief known" field.
- A rule in a prompt file containing `: ` parses as a YAML mapping.
  `test_every_rule_in_a_prompt_file_is_a_sentence_not_a_yaml_mapping` catches it.

## Still open

- `response_format.md` still says "learned the first two things on its line", which are the event and
  the belief. That conflicts with the event being optional. It was left alone; it leans toward waiting,
  which is the direction we want.
- If the live run still offers at message 3 on behaviour alone, the next step is a separate judging
  call, not more prompt lines (it costs latency, against R2).
