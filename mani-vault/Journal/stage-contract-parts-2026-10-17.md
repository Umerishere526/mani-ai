---
type: journal
date: 2026-10-17
tags: [journal, walk, abcde, parts, contract, lessons]
---

# A stage is made of parts, and code steps it from the parts (2026-10-17)

Lolly's review of 2026-10-16 (R17) and muhammad's follow-ups asked for ABCDE as a conversation: stay on a
letter until they agree, say Mani's reading of that letter only, help on "I don't know" with what we already
have, keep the letter on screen, follow a change of situation or feeling anywhere, and write nothing that
would make the next framework a rewrite.

## Why the earlier rounds kept failing

Rounds R12, R13, R14, R16 and the first R17 pass each encoded her latest example as a form or a rule. The gate
stayed the same: the model labelled a stage known, partial or missing with one gap id, and code moved on a
label. Code never knew what a stage was made of, so "is a reading due" and "is this a new reading" were the
model's call every turn, and "I don't know" had nothing to hold on to. Every new framework would have needed
new code for its own letters.

## What changed

- Content declares `parts` per stage (`id`, `is`, `enough`, `required`, `from`, `ask`, `stop_pushing`), plus
  `intro`, `reflect`, `when_stuck`, `confirm`. Code reads only those keys, never a stage name; the seed refuses
  a framework the walk cannot read.
- The reply reports parts, not statuses. Code steps the stage: collecting, a reading once every required part is
  in, their yes, a question about what they take from it, done. A new reading only when a part differs from the
  one last read back.
- "I don't know" is sent `stage_have`, `stage_missing` and `stage_last_question`; the stage holds. A part's
  `stop_pushing` is how it stops pushing.
- Parts bound to the understanding (`from`) are filled once per value as inferences to confirm, so what was said
  in the open chat reaches the stage without a store ahead of the walk. This is not the 2026-10-13 design that
  failed ([[transcript-is-the-memory-2026-10-13]]): that seeded every stage at the yes from a 20-message window;
  parts are judged when the stage is reached, from the whole thread.
- A change is `refine` or `shift` and holds the walk in code while it awaits their answer.

## Gotchas

- The integration tests read the framework from the database, so every content edit needs the reseed before they
  mean anything. A passing unit suite on stale seeded content said nothing.
- Eight unit and about twenty integration tests were stale from the somatic rollout (old strings, `Chat More`,
  `somatic_practice` as final). `CHAT_MORE_LABEL` was still read by `_offered_handoff` and the after-framework
  question, so after the new cadence neither recognised the closing choices. Fixed with the label.
- A YAML bullet with a colon in it becomes a mapping; `test_every_rule_in_a_prompt_file_is_a_sentence_not_a_yaml_mapping`
  caught two in the new prompt text.

## Open

- The live run in three styles with Lolly's conversation (`anxious_long_day`) is owed; whether the model produces
  the "aha" the readings and reflections are there for is only visible live.
- A stage already done is not re-read when a later feeling change touches one of its parts.
- Michaela's review of the ABCDE parts (clinical wording of `is`, `enough`, `stop_pushing`) is content only.

See [[reach-judged-in-its-own-field-2026-10-14]], [[abcde-walk-owned-by-code-2026-10-13]] (both superseded in part).

## First live read, the same day (muhammad's Directive coworker chat, thread 24cfa044)

Tuned in content, prompts and field descriptions only; the flow was left as it is (muhammad: "don't affect the
functional properties of flow").

- The letter line on every reply read as scripted: it now opens a stage only.
- "I just want to get rid of the feeling of being fearful around him" was taken as a yes to A's reading of the
  team's morale. A goal or a new focus is now said to be a correction, and A's `enough` says the situation is the
  person's to choose.
- "Fearful" was never stored as their feeling, so C asked for it and got "I told you the consequence". The feeling
  description now covers a feeling named inside the framework and one they want to be rid of; `next_stage` says a
  part already given is never asked.
- B took "he will target me" as the belief to dispute. For a junior person facing a senior, that may be a real
  risk; B's `enough` now keeps a prediction of real harm by someone with more power as a risk and asks what it
  means for them instead.
- B's reflection ("now that you've said it out loud, what do you notice") was abstract and wrong about who said
  it; the reflections are now concrete (how true it feels; what it costs them; what stands out).
- The check re-offered "someone with more authority" right after "not directly"; the check now never re-offers a
  step they said is out of reach.
- Lesson: the prompt budget test (`test_an_open_offer_turn_costs_less_prompt…`) caps an open-offer turn; every
  sentence of guidance added there had to be paid for by trimming A's own lines.
