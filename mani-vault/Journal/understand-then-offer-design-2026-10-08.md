---
type: journal
date: 2026-10-08
tags: [journal, offers, prompts, client, design]
---

# Designing spec 0016: Mani understands the issue, then offers naturally

Spec: `docs/specs/0016-understand-issue-then-offer-naturally/`. Scope feature 22. From [[client-response-feedback-2026-10-08]].

## muhammad's choices (2026-10-08)

- Seven prompt lines replaced one for one (E1 to E7): mirroring only to check understanding, ask what the issue is first, offer once the issue, what makes it hard and (for a choice) what pulls each way are known, no say back on a yes.
- The model's own line goes before every seeded offer. No code check on it (spec 0006).
- Floor `clear_offer_after: 2` kept as a guardrail; no other count.
- Proof: a new `client_job_decision` scenario, one real run per style, after his yes.

## Things I would have got wrong without checking

- **The offer turn discards the model's reply.** The client's "abrupt" complaint, in today's build, is that their last message gets no answer at all, not the recap they quoted (that build predates features 15 and 17).
- **Line 54's answer has never reached anyone.** "Asked what it involves, answer in two sentences" runs on the re-offer path, and the code replaced it with the seeded card. `test_asking_about_an_offer_leaves_it_open` locked that in. Caught by the cross check, not by me.
- **A "general" offer rule can already be satisfied by the message you want it to wait past.** The client's message 2 states the decision and the fear, so "what makes it hard" alone would still offer there. Test a rule against the actual script before writing it into an AC.
- **YAML list items cannot hold a colon followed by a space.** A drafted prompt line ("keep it short: answer…") would have become a mapping. Parse drafts with the venv's `yaml` before showing them as final.
- **A stale cap passes anything.** The 3616 word cap was spec 0012's; the files were at 3391. Pin the exact count after the edits.

Related: [[prompt-changes-cut-not-add]], [[offer-per-style-design-2026-10-08]], [[measure-before-tuning-prompts]]

## Round 2 design (2026-10-08, after round 1's runs failed)

Round 1 results: [[understand-then-offer-build-2026-10-08]].

- **Redefining a move does not reach a reply the model files under another move.** E1 changed `mirroring`, but "That sounds frustrating" is care to the model, so `warmth lead`, `rules` line 18 and the style lines kept producing it. When a behavior survives a rule change, look for every line that could license it, not only the one with its name.
- **"Never name a feeling they have not named" permits naming one they did.** A prohibition with an exception reads as permission for the exception.
- **"No offer of your own" was too abstract.** The model did not recognize "I can help you sort through the choice" as an offer. Saying concretely what the seeded text already covers is the round 2 fix (E6).
- **The client's examples are the spec.** Their better replies open with care about the situation, not about the person. E9 to E11 say that in positive form.
- **The eval deletes its users, so per reply data is gone after a run.** Round 2 prints shape (from `thread_response_styles`) and reasoning (`AI_DEBUG_MODE`) during the run, so a second failure names its line.

muhammad's choices: update 0016 in place, all four restating lines including Supportive, E6 concrete, three runs per style passing on 2 of 3, restating = a feeling handed back in any form or a retelling sentence, say back after Try It measured only.
