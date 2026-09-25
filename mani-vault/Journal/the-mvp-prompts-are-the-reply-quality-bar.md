---
type: journal
date: 2026-09-24
apps: [backend]
tags: [journal, prompts, evals, mvp]
---

# The MVP's prompts are the reply-quality bar

## What happened

The client said Mani's replies are worse than the MVP they had: robotic, loopy, cold, and Direct
not direct. muhammad asked for the prompts to be rebuilt file by file with that MVP as the bar.

## Insight

- The MVP's final prompts are in `~/Desktop/Mani Repos/mani-app /apps/backend/prompts/` (the folder
  name ends in a space) at commit `e7776ed`, 2026-01-30. That commit **deleted** the three style
  files, so the MVP the client remembers ran one presence-first voice with two named techniques,
  not three styles.
- Both prompt stacks are about the same size, 34–38K characters a turn. The difference is what the
  words are spent on: the MVP is a goal, five moves and whole annotated conversations; ours was
  mostly prohibitions.
- The generic line the client objects to, "How are you holding up with it all?", was in our own
  prompt examples four times. Same lesson as [[framework-endings-and-ignored-offers]]: an example
  becomes the template.
- Reading chat transcripts from the local database is blocked by the permission system as
  health-data PII. Ask muhammad to paste examples instead.

## Links

- Design: `docs/superpowers/specs/2026-09-24-mani-reply-quality-design.md`
- [[measure-before-tuning-prompts]]

## Decisions on the `mani_base.md` rebuild (muhammad, 2026-09-24)

- **Section 1, who Mani is and the goal:** confirmed as proposed. Mani is a warm, experienced
  companion, never clinical. The goal is to help them feel heard and leave a little better, holding on to
  the issue they came with.
- **Section 2, how Mani responds:** the five moves stay. **Mirroring is there but never forced**:
  when the chat is ordinary, Mani just talks. The five named mirroring voices go. Presence may be
  said in any style. A sensed feeling may be named only as a question that checks it.
- **Code follows the prompt before it is measured:** the repair that deletes "I'm here" outside
  Supportive goes, and the schema stops asking for a mirroring voice each turn. Otherwise the
  old code fights the new prompt and the comparison misleads.
- **Section 3, the three styles:** confirmed as proposed. Each style is written as intent, not rules.
  Direct is warm and heads for a way through: direct, not directive, and it offers soonest.
  Supportive puts feelings first, then turns to what would help now. Reflective explores the
  feeling and checks a sensed one as a question.
- **Section 4, how a conversation moves:** Mani is given the whole route: understand, check once,
  offer, go through it, close, carry on. The client's one-time clarification ("Do I have this
  right?" / "What would you like us to focus on today?") is asked at most once.
  - **Offer timing:** not fixed, usually 4–8 exchanges in Supportive and Reflective, and sooner
    in Direct.
  - **Questions:** most replies before an offer ask one question, but not every one has to;
    some moments are only received. This replaces "every reply ends with a question", which
    read as interrogating.
- **Section 5, offering the questions:** the client's description of the chosen framework is
  **shown word for word in every offer, added by the backend**, so it can't be paraphrased or
  dropped. muhammad: it should give the person the sense that they're about to get a way through
  what they feel. Mani writes only the part showing it understood, plus a fresh lead-in; the
  backend adds the description and the client's permission question for the style. The four
  example offer sentences are gone, because they had become the template.
- **Section 6, going through the questions and ending:** the issue they came with stays at the
  centre of every question. The client's mid-framework replies are kept word for word. The body
  check-in is asked exactly as written, and only once. The practice is given only when its stage
  arrives (Task 7), and never when they mention pain or trouble breathing.
- **Section 7, three conversations:** one whole journey per style, each with a different scenario
  and framework, none taken from the eval scenarios, in the MVP's annotated format. The parts
  the backend adds (the description, the permission question, the practice, the choices) are
  shown as annotations, never as text to copy.
- **Section 8, what never happens:** only the rules an example can't carry: no clinical words, no
  repeated question or loop, no generic check-ins, no announcing plans, no added size or weight.
  The anti-injection rules move to the end, shorter, with every protection kept.
