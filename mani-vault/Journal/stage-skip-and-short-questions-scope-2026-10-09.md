---
type: journal
date: 2026-10-09
tags: [journal, frameworks, stages, ledger, questions, prompts]
---

# A stage answered out of order was asked again, and questions ran long

From a live Directive ABCDE chat (thread `cbc5c13d`, "left out of meetings"), scoped as feature 12's amendment and feature 23 in `docs/scope/scope.md`.

## The code was not the cause

`Registry.stage_from_ledger` already takes the first stage not `known` or `passed`, in any order: A, B, D known gives C, then E once C is known. Whether a stage told out of order is skipped rests entirely on the model reporting it `known`.

## Why D was asked again

Before the offer the person had given both sides of D: the meetings (seems true) and "nope, no one has said a word" (questions it). The prompt kept D open: `mani_base.md` `in_a_framework` says the stages after the `|` count only "in their own words … never from your words or a guess", and the second side answered Mani's own question. Mani asked D fresh; the person said "i already mentioned that".

muhammad reversed the work stage rule (2026-10-09): any stage the model clearly understands is skipped with no question, and the person's own words are not needed. The `|` split loses its only meaning, so it and its seed check go.

## Why the questions were mouthfuls

Three prompt phrases ask for it:

- "in your style and their words, about their situation, never bare" (`in_a_framework`)
- "built from what they have told you, in their words, … never bare" (`response_format.md` `stage_lines`)
- "say what you now understand, name what is still missing in fresh words" (`in_a_framework`), which puts a restatement before every question

Two part Stages descriptions ("felt or did") plus "never ask the same thing the same way twice" give double questions joined by "or". The client's questions are 7 to 17 words; Mani's reached 22. muhammad will judge the fix by eye, with no word limit.

## Can't be proven after the fact

No per turn ledger is stored. `admin.llm_calls` keeps no reply text, and the final row showed all five stages `known` with `turns` 0. What the model reported each turn is inferred, not seen. Feature 12's amendment logs the reported statuses (ids only) and shows the ledger in the chat tester so the next run can be read.

## Seen in the same chat, already on the scope

- C asked four times: the stall cap (spec 0010 task 2) is not built, so `turns` stays 0.
- No letter names ("C is for Consequences"): feature 20, waiting on verify.
- At E Mani handed them the new belief ("Would it fit to say …"), which the client doc §0.8.5 rules out.

## Designed

Spec 0010 amended the same day: the `|` sentence, its seed check and the `|` in all six Stages lines go; `known` means "the conversation makes clear what it asks". Each chat call's `admin.llm_calls` row gets `reported_stages` and `stage`, written by `link_call`, and the chat tester shows them, so the next run can be read turn by turn. Feature 23 stays its own spec; the sentences each one owns are listed in 0010's *Not in this spec*.

Related: [[stage-ledger-design-2026-10-08]], [[stage-ledger-tracer-build-2026-10-08]], [[understand-then-offer-design-2026-10-08]]
