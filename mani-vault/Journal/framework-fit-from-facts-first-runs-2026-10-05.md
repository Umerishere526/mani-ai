---
type: journal
date: 2026-10-05
tags: [journal, frameworks, router, measurement]
---

# First real runs of "a framework is chosen from facts" (row 8, spec 0005)

`scripts/eval_replies.py --style supportive`, one run each, model `google/gemini-3.1-flash-lite`. muhammad said yes to both runs. Transcripts were kept only in the session scratchpad.

## Run 1: four chats

| Chat | AC-15 expects | Got |
|---|---|---|
| stress_nothing_named_yet | no offer by message 4, asks what happened | no offer; the last reply asked nothing |
| panic_attack_grounding | DBT STOP | DBT STOP at message 2 (panic wording); typed past, so Keep chatting |
| manager_embarrassed_me | ABCDE | ABCDE at message 3 |
| grief_dog_steering | an offer, never Behavioral Activation | ACT at message 3 |

**The model invented fact ids** in most replies: `emotional_stress`, `pressures`, `loss`, `living_situation`, `environment`, `good_memories`. The code dropped them, as designed, but it meant few real facts arrived. In the stress chat the model then offered ACT at message 4 twice; the second offer was removed with its words, leaving a reply with no question.

Cause: the ten ids were listed only in the parent `facts` description; the `fact` field said "one of those listed". Fix: the `fact` field names the ten ids itself, and the `facts` description says an empty list is common and means keep talking.

## Run 2: stress and grief again

- No invented ids in either chat. The fix worked.
- Grief: ACT at message 4, never Behavioral Activation.
- **Stress: ACT offered at message 3 as a clear fit.** The model marked `cannot_control` for "work pressure, parents pressure, society pressure" (ACT is the only framework that fits on that fact alone). The words check passed because the words are theirs; it proves the words exist, not the meaning. This is the risk the spec named.

## Run 3: `cannot_control` tightened, stress three times, grief once

The meaning now names a specific thing they said they cannot change, and the `facts` description says general pressure, stress or worry on its own is none of the facts.

- Stress, run 1: ACT offered as a clear fit at message 4 ("Those pressures seem outside your control").
- Stress, run 2: Structured Problem Solving offered as the closest fit at message 4.
- Stress, run 3: no offer by message 4, as AC-15 expects; the last reply asked no question.
- Grief: ACT at message 4, never Behavioral Activation.

So the stress chat meets AC-15 in 1 of 3 runs. Tightening a meaning moved the offer later, it did not stop it. Reading: at message 4 `[ctx]` says `closest_fit: due`, and the model marks facts loosely to justify the offer it feels pushed to make. The words check cannot catch that, because the words are theirs. Stopped here and asked muhammad rather than stacking prompt fixes.

Choices put to muhammad: accept Structured Problem Solving as the nearest fit for several named pressures (the client's own "several problems need separating"); stop owing the closest fit at message 4 at all, so offers come only when facts fully fit; or make the facts that fit on their own stricter in code (for example, require `cannot_control` and `practical_problem` to be quoted from a message that is not a list of general areas). Each changes ADR-014 before it is accepted.

## Run 4: AC-17, after full fits only (no nearest offer, no `[ctx]` push)

`--verbose` now prints the fact ids, pick, leading framework and redraft reasons per turn (never the person's words), which is what made this run readable.

- **Stress, 3 of 3 failed.** ACT offered at message 4, 3 and 4, each from the model's own draft after it kept `cannot_control` for "work pressure, parents pressure, society pressure". No redraft pushed it. All three also kept `overwhelmed_now` for "i feel emotionally stressed" at message 1 (the cooldown blocked an offer there).
- **Grief, no offer.** The checklist changed every turn: `low_mood` (Behavioral Activation, vetoed by "died"), `cannot_control` (ACT, too early at message 2), `event` and `meaning` (ABCDE, for "his presences in my day to day life"), `event`, `low_mood`. No fit held long enough to be offered.
- **Deadlines, wrong framework.** "do not know where to begin" was kept as `cannot_begin` with `low_mood`; at message 2 the model's draft offered something else and reason 3 redirected it to Behavioral Activation, because tie rule 3 puts `cannot_begin` over Structured Problem Solving. The code amplified a loose fact. The cross check had named this exact risk.

Reading: removing the push did not stop the loose marking, so the push was not the cause (the thin evidence noted in the spec held). Two problems sit under all of it: the model (`google/gemini-3.1-flash-lite`) marks facts by topic, not by the definitions, and it reports what it notices on this turn rather than what has been established, so the facts flip. The code does what spec 0005 says; its input is too noisy for the rules to be right. Stopped and took it to muhammad rather than tune further.

## Lessons

- A schema description is read field by field. A closed set must be named on the field the model fills, not on its parent.
- The plain meanings carry the semantics, but only so far. A loose meaning (`cannot_control` as "something they cannot change, control or settle") let general pressure through; tightening it moved the offer later and did not stop it, because the model still marks facts to fit the offer it is pushed toward. A meaning cannot outweigh a `due` in `[ctx]`.
- The eval runner does not print the facts log line, so which words a fact was kept on cannot be seen from a transcript. Worth adding to the runner's verbose output (ids are already logged; the words never are, by design).

Related: [[framework-fit-from-facts-design-2026-10-05]], [[measure-before-tuning-prompts]].
