---
type: journal
date: 2026-10-08
tags: [journal, frameworks, client, content]
---

# ABCDE from the client's ABCDE Framework doc

Source: `docs/client-share-docs/ABCDE Framework.docx`, transcribed as §0 of `backend/docs/specs/framework-abcde.md`. Scope feature 20.

What fit in content, and what did not:

- **Fit in the seven lines:** the letter names (A is for Activating Event, D is for Dispute, E is for Effective New Belief), the priority over Thought Reframe, and "never manufacture a new belief". The ledger from spec 0010 already skips stages the chat answered. The client's ask is that each skipped letter is still *named*, so the names sit in the Stages line words, and `framework_starting` says known stages back in a clause.
- **The Stages line cap bit.** With the client's wording it came to 396 characters, and `seed.py` capped it at 320. muhammad raised `MAX_STAGES_LINE` rather than shorten the client's words, to 420 once the ids were renamed.
- **The stage ids are the client's step names**: `activating_event`, `belief`, `consequences`, `dispute`, `effective_new_belief`. The first pass kept `examine` and `balanced` (from the older SIX FRAMEWORKS spec) to spare stored state and tests, and muhammad asked why. The model reads an id as the stage's name in the Stages line, `stage_ledger` and `framework_stages`, so an old id is old wording the person's conversation is steered by. Nothing in `backend/mani/` or the prompts names these ids, so the rename was the file, the tests and the docs. The one local thread left at `examine` no longer continues; start a new chat.
- **The button labels are matched ignoring case**, so the rename to Try It · Tell Me More · Keep Chatting also hit lowercase strings in the tests ("yes, let's TRY it", "I WANT TO KEEP TALKING"). A plain replace of the exact label missed them, and only the full suite found them.
- **Did not fit in content, enrolled for `/architect`:** the per style offer and the five step Tell Me More (feature 17), and the new ending flow (feature 21). The doc says no automatic body check, which contradicts spec 0009 (feature 7). muhammad's flow for all six: ask about the situation and feeling; if the issue continues, the three after framework questions; if they feel fine or it is resolved, the body check.

Not yet proven on the model: whether letter names in the Stages line are enough for the model to say "A is for Activating Event. …" for stages it skips. Only a real run shows it, and that needs muhammad's yes.

Related: [[client-lines-the-code-matches-exactly]], [[stage-ledger-design-2026-10-08]], [[offer-in-client-words-build-2026-10-08]]
