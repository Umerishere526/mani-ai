---
type: journal
date: 2026-10-04
tags: [journal, prompts, conversation, preferences]
---

# The prompt overfitted the model; Natural Mani is the direction

After the client meeting of 2026-10-02, muhammad set a new direction: Mani must sound natural, neutral,
humble and down to earth. His example of the target: "I'm in pain" gets "Can you tell me more about it?".
The scope rows are 32 to 35, 18 and 6 in `docs/scope/conversation.md` ("Natural Mani").

## Evidence that we overfitted

- The client's style document ("directive, reflective, supportive .docx") breaks our own rules in its
  examples: "It sounds like a lot is happening at once" (we ban "a lot"), "I'm here with you". We held the
  model to rules stricter than the client's own writing.
- ADR-008 forces a question into every reply before an offer, with up to two redrafts. That works directly
  against the client's complaint of too many questions.
- `mani_base.md` is about 500 lines and itself uses dashes as punctuation, which the model copies.
- The model is `google/gemini-3.1-flash-lite`, the lite tier, not Flash.

## What muhammad decided (2026-10-04)

- Rewrite the base instructions short and open, and **retire the code redrafts that enforce tone**
  (forced question, feeling word check, repeated question). Safety checks, offer vetoes and stage
  tracking stay. This supersedes parts of [[ADR-006-a-turn-may-be-redrafted-once]],
  [[ADR-008-every-reply-before-an-offer-asks-a-question]] and [[ADR-011-first-stage-by-its-own-test-and-one-draft-when-asked-to-pick]];
  the new ADR comes with row 33's spec. Until then, do not "fix" a reply back toward those ADRs.
- Inside a framework, any reply moves to the next stage, including "I don't know", "yes", "sure" or a
  question of their own. A stage is never asked twice. The next stage must cope with a missing answer.
- The offer says the framework's name and a short introduction, with the client's three buttons:
  "Yes, let's try it", "Tell me more", "I want to keep talking". The style document itself never names
  the framework, so this needs the client's written confirmation.
- Order: measure first (the style document's four conversations as a standing check), then rewrite,
  then choose the model on the same check. See [[measure-before-tuning-prompts]].
- Scope row 22 ("mirror then exactly one question" in the answer format) is dropped, and row 28 is folded into row 33.
- Model choice is open across the major providers and open models (Kimi, Qwen, MiniMax were named). Pick from
  what OpenRouter offers at the time, by a comparison run, not from memory.
