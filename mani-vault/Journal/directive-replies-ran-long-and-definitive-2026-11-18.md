---
type: journal
date: 2026-11-18
tags: [journal, prompt, directive, eval, client-feedback]
summary: "Directive replies ran long, definitive and argued before D because the prompt asked for it and the eval rewarded it."
failed:
  - "Tried 'three or four short sentences' for Directive alone; failed because other lines asked for 2-3 moves and 120-220 words"
  - "Tried judging Directive with length set aside; failed because the gate passed replies the client rejected as coaching"
---

# Directive replies ran long, definitive, and argued before D (2026-11-18)

The client reviewed muhammad's Directive chat (passed over for promotion, through ABCDE to "Stronger") reply by reply:
[[2026-11-18-promotion-chat-feedback]] in `docs/client/messages/`. Every complaint traced to our own text, not the model:

- **Long and stacked.** "Three or four short sentences at most" was added the same morning and broken in every reply
  (75 to 180 words). Other lines said the opposite: "most replies do two or three of these" over a menu of nine moves,
  "usually 120 to 220 words", "usually 60 to 120 words" inside the set, and long examples. A rule added beside its
  contradictions loses to them.
- **Definitive.** The "How you listen" first-reply bullet taught "This isn't really about the dishes. You're sharing a
  home with...", and the model turned that shape into every reply ("It is not really about whether you work hard. It
  is about..."). It contradicted the first-reply paragraph added in the consistency work, which says a reading is a
  question. The earlier change added the new rule and left the old one in place.
- **Arguing before D.** "A fair perspective" and "Pushing back on self-judgment" are per-reply moves, and nothing kept
  them off the belief the set would examine. By D, Mani had disputed it four times and D had nothing new.
- **Blame.** "How two things connect" invited "That silence probably reinforced the feeling", a causal claim the
  person never made that put the problem on them.
- **The eval could not see it.** The judge rewards "adds something they did not say" and sets length aside for
  Directive, so the gate scored the stacked, definitive replies well.

Several points were objections the client had raised before (R83, R94, R105), which muhammad overruled on 2026-11-17
without her being told. The second round is the signal: muhammad now upholds them where she pointed (Directive; after
a set).

Lessons:

- When a prompt rule is ignored, look for the lines that contradict it before adding emphasis. Adding a line beside
  its contradiction is a patch.
- When replacing a prompt rule, delete the old one in the same change.
- An eval criterion like "adds something" pulls against "say less". Give the client's complaints their own rule
  cases, checked by code where code can (`max_sentences`).

If the Directive length still fails the eval once credits are back, the next step is code counting sentences and
asking once more (option 2 in `docs/superpowers/specs/2026-11-18-promotion-chat-feedback-design.md`), not another line.
