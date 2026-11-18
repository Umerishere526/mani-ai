# The same opening gets the same kind of conversation every time

Approved approach: A (muhammad, 2026-11-18). Short design, on `feat/one-call-turn`; muhammad tests on the branch and
merges himself.

## Intent

muhammad ran one Directive opening twice ("tired of always being the understanding friend") with the same prompt. The
second run was what he wants: it reflected, explored, let the belief come out of the person's own answers, and offered
on their 3rd message. The first declared a core belief in its first reply in dramatic words ("you can never stop
performing to be loved"), offered on their 2nd message right after they corrected it, and then mixed a stage into the
offer's steps. Good quality that comes only some of the time is the problem: it must be consistent.

## Why it varies

The model samples each reply at temperature 0.7, so one input gives different replies; and the moments that matter
most (how soon a reading is offered, how strong it is, never offering after a correction) live only in the prompt,
which MiniMax follows most of the time, not every time.

## Goals

1. No offer before the person's 3rd message, guaranteed by code.
2. No offer on a turn whose message corrects Mani, guaranteed by code.
3. The first reply reflects and asks; it never names a core belief or a deep reading of them. At most one gentle
   possibility, put as a question ("I wonder if there's something deeper behind that guilt. Do you feel selfish
   because you expect the same effort back, or because saying you need something feels uncomfortable?").
4. Less run-to-run variation: the chat runs at temperature 0.3.
5. The gate catches inconsistency: rule cases for these moments run five times each, and every run must pass.

## Non-goals and anti-goals

- No change to the framework sequence, the safety rules or the style rules.
- Anti-goal: a floor so long the person waits for help they asked for. Three messages is what the good run did.
- Anti-goal: lower randomness bringing back repeated stock wording; the gate counts the phrases.

## Approaches

- **A (chosen):** guarantee the moments in code, lower the randomness, measure consistency.
- B: prompt and temperature only; the offer timing stays a matter of chance, which is what broke the first chat.
- C: a stronger model; several times the cost per reply, already turned down.

## The design

1. **The offer floor (`decide`).** An offer before the person's 3rd message (the style tap does not count) is refused,
   and the facts say so before the call (`facts.NO_OFFER`), as for every other refusal. A refused offer is traced; its
   text goes out as written, with no buttons. The floor of 2026-11-16 was removed because it rarely bound on the
   earlier model (it waited until their 6th to 8th message anyway); on MiniMax it would have stopped the first chat.
2. **The correction guard.** The reply gains `corrected`: true when their latest message corrects something Mani said
   or understood. Code refuses an offer on such a turn. The prompt's rule (never offer when their latest message
   corrects you) stays; code makes it hold.
3. **The first reply (`mani.md`).** "How a reply looks" and the first-reply example: the first reply reflects what they
   said in their own terms and asks; any reading is one gentle possibility put as a question, never a statement about
   what they believe or fear, and never in heavy words ("performing to be loved", "attachment", "wound"). This takes
   back, for the first reply, muhammad's overrule of R73 (2026-11-17), recorded in `requirements.md`.
4. **Temperature 0.3** in `mani.md`'s frontmatter (`model_parameters.temperature`), seeded with the row.
5. **The gate.** New rule cases, five runs each: the first reply to this opening names no core belief (judged); the
   reply to the correction ("I don't think it's that I'm afraid they won't love me...") is not an offer and reports
   `corrected` (code); an offer on the 2nd message is checked by code anyway. The stock-phrase count is reported.
   Before and after run one after the other: the committed prompt at 0.7, then the new one at 0.3.

## Verification

- Unit: the floor refuses an offer on the 1st and 2nd message and allows it on the 3rd; `corrected` refuses an offer;
  the facts carry `NO_OFFER` before the 3rd message.
- Integration: a scripted offer on the 2nd message shows no buttons and opens nothing.
- The gate as above, then `check_suite.py`.

## Left to the builder

How the person's message count is read (the history or the thread's count), the field's exact description, the
eval's sample count per case, and the wording of the prompt lines.

## Known and left as is

When the offer is at its lead-in and the model starts a stage anyway, code still adds the five steps (the first chat's
last message). The facts tell it not to; with the floor and the correction guard the path is much rarer. Revisit if
it shows up again.
