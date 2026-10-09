---
type: journal
date: 2026-10-08
tags: [journal, client, styles, offers, scope]
---

# Client feedback on Mani's replies, scoped as feature 22

The feedback, word for word: `docs/client-share-docs/mani-response-feedback-2026-10-08.md`. Scope feature 22.

- **Check which build the client ran before you treat their quote as today's behavior.** Their transcripts show the model's own line before the offer ("there are some questions we could go through together"). Today `orchestrator.py` replaces the whole reply with the seeded offer, so that can't happen any more. muhammad confirmed the client tested an older build, from before features 15 and 17.
- The client dropped the 2 to 4 exchange window before the offer. Mani should offer once it understands the issue, with no count. Feature 14's Done when now points to feature 22. Spec 0012 AC-11 still names the window.
- The transition problem is still open, in a new form: the seeded offer card arrives with no bridge from the conversation.
- muhammad again: fix this by cutting and replacing prompt rules, never by adding them.

Related: [[client-cadence-design-2026-10-08]], [[offer-late-root-cause-prompt-not-code-2026-10-08]]
