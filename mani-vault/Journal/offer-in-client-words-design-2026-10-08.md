---
type: journal
date: 2026-10-08
tags: [journal, offers, client, design, replies]
---

# Designing spec 0013: the offer in the client's words

Spec: `docs/specs/0013-offer-in-client-words/`. Scope feature 15; Tell me more's real wording is feature 17.

## muhammad's choices (2026-10-08)

- The code writes the offer from seeded rows; the model only decides when and which, through its technique button. The model's text on that turn is dropped.
- One lead for all six: "We'll go through a few focused questions. By the end, you will have turned a problem that feels unclear or overwhelming into a practical next step. Would it help to work through it together?" I flagged that it is Structured Problem Solving's own description (shown twice on that offer) and promises a next step the other five do not give. He kept it. Easy to change later: it is one seeded line.
- The client's exact names and descriptions (ABCDE Framework, STOP Framework, Structured Problem Solving, "This framework…"), lowercase "framework" in all six.
- Tell me more shows the name and description, no model call, until the client sends wording. He rejected the client's panic scenario Tell me more lines: they fit panic, not the normal flow.
- The text field is hidden while an offer is open. The client reads the buttons (a `technique` button on the newest message); no API change.
- Typed text past an offer: one rule, any surviving technique button gets the full offer. No same offer special case.

## Things I would have got wrong without checking

- **Where the scope's frame came from.** "We'll go through a few focused questions" was not in either client document; it was `structured_problem_solving.md`'s `summary`. The `summary` fields were the client descriptions with "This framework" rewritten to "These questions", because `offers` line 1 banned the word.
- **YAML `yes` key.** The buttons are `accept`, `more` and `decline`, never `yes` and `no`: [[prompt-word-budget-and-yaml-yes-key-2026-10-07]].
- **Code only button keys exist already.** The greeting's `style` key is stored in `prompt_options` and never in the model's schema (`chosen_style`). Tell me more's `more` key follows it.

## Caught by the cross check, not by me

- `test_prompt_contract.py` requires every `SmartPrompt` field named in the `prompts` line, so cutting the decline clause would have failed it.
- `asked_about_it` needs a "?" and the model re-carrying the button. Cutting "Keep both buttons" made the typed question path nearly dead, which led to the one rule.
- The empty text check runs before the reply is stored; the offer must replace the text before it, or an offer turn with empty model text fails.
- The model's `style` would be recorded for text the person never saw.
- `eval_replies.py` would flag every code written offer: `says_framework` on "Framework: <name>", and "overwhelming" in the lead is in the feelings vocabulary.
- `ScriptedModel` counts calls across the whole test and repeats its last reply, so "zero calls" is the wrong assertion for a no model turn.

Related: [[client-cadence-design-2026-10-08]], [[offer-late-root-cause-prompt-not-code-2026-10-08]], [[client-lines-the-code-matches-exactly]]
