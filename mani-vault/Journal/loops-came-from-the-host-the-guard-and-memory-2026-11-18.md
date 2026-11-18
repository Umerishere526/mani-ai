---
type: journal
date: 2026-11-18
tags: [journal, routing, reasoning, offer, memory, eval]
summary: "Loopy chats and a skipped offer came from a host with no reasoning, a correction guard that refused an offer already written, and a test account's mixed memory, not from the build-up wording."
failed:
  - "Tried reasoning effort high without checking the host ran it; failed because 87 of 91 live calls landed on hosts that answer with no reasoning"
  - "Tried code refusing an offer on a turn that corrects Mani; failed because the lead-in was already written, so it reached them with no buttons and ABCDE then ran in text with no set"
  - "Tried judging Directive length and loops from the single-reply eval; failed because live chats carry notes, memory and a host the eval never checked"
---

# Loops came from the host, the guard and memory (2026-11-18)

After the Supportive and Reflective build-up change, muhammad found the chat loopy in every style and Directive
longer. He sent two Directive chats:

- **Chat 93559611:** 24 replies with no offer. Mani coached the talk with the manager instead, and asked the same
  question about five times.
- **Chat 026ac499:** the lead-in came with no buttons. "yeah" went straight to "A is for Activating Event." Mani then
  repeated a reply word for word and stayed on A.

## What was found

1. **A host that drops reasoning.**
   - Probed with a real turn at effort high, Inferact vLLM, Together and Nebius return 0 reasoning tokens.
     ModelRun, Fireworks and Makora return 394 to 807.
   - Since 16:00 UTC, 87 of 91 live chat calls had landed on Inferact.
   - Replayed at the same moment with memory and notes, Makora offered the set in 4 of 6 runs and Inferact in 0 of 6.
     At the repeat moment Inferact copied its last reply in 1 of 6 runs, and Makora moved to B every time.
   - The routing list had not changed since 11-17. OpenRouter was simply picking the fast host. Raising the effort to
     high did nothing on it, and nobody checked.
   - Fixed by routing only to `modelrun`, `fireworks` and `makora` (commit `6e57d70`). Of the calls that reasoned, 90%
     finished within 11 s.
2. **The correction guard (commit `a762a77`, the same morning).**
   - It refused an offer on a turn the model marked as a correction. The refusal came after the reply was written,
     so the lead-in reached the person with no buttons and no open offer.
   - Their "yeah" then had nothing to answer. The model began ABCDE in its own text, with no set state, no five
     steps, no Start and no stage facts, so it never moved past A.
   - This repeats the failure in [[flat-replies-were-the-model-2026-11-17]] (code refusing an offer the reply already
     made).
   - Removed (commit `cb48a27`). A rule the model cannot be told before the call breaks the one-call design.
3. **The test account's memory.**
   - user1's memory held every scenario muhammad had tested: promotion, coworker noise, photography, a partner's lies,
     work-life balance, a sick child. It went into every new chat.
   - The "proving your place" in a Supportive first reply came from there, not from the prompt (correcting
     [[highlight-came-before-the-build-up-2026-11-18]]).
   - Cleared on muhammad's word. The one unfolded chat was marked folded so it would not refill the memory.
   - The same day muhammad ruled that every chat stands alone, with only the safety check after a pause crossing
     over. The whole memory path was removed and its data dropped (migration `041`,
     `docs/superpowers/specs/2026-11-18-separate-chats-design.md`).

## Not the cause

Replayed at three points of chat 93559611 with no notes, the old prompt averaged 74 words a reply and the build-up
prompt 66. The offers were 13 of 24 runs against 9 of 24. Long Directive replies late in a chat happen on both
prompts. That is the deferred code check on sentence count, not the build-up.

## Lesson

The eval is one reply, with no memory and no notes, and it never checks which host answered or whether it reasoned.
"Directive unchanged" from the eval alone was overconfident. Before calling a prompt change safe, replay a real long
chat the way a live turn sees it, and check that live calls show reasoning tokens.
