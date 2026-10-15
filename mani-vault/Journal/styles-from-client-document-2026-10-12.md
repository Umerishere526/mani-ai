---
type: journal
date: 2026-10-12
tags: [journal, prompts, styles, directive, supportive, reflective, lessons]
---
> Superseded 2026-10-13 (the two client example conversations per style file: removed, the voice now comes from `mani_base.md` `sounds_like`) — see [[client-sample-voice-and-confirmed-check-2026-10-13]]
> Superseded 2026-10-12 — see [[restating-is-not-reflecting-2026-10-12]] (keeping "never ask about something that has not happened yet": the client now asks "What would making the wrong choice mean to you?")

# Styles from the client's document (2026-10-12)

The client sent a Word document restating Directive, Supportive and Reflective, with four scenarios
in every style (record: `docs/client/messages/2026-10-12-styles-document.md`). Read against our
prompts, the styles had drifted from it, and the cause was not one rule.

## Root cause

We never sent the client's own behavior lists to the model. In their place we wrote our own recipe
for each style five times (`mani_base.md` `styles`, `context.py` `_MEANING["conversation_style"]`,
`_QUESTION_FOCUS`, `_IN_STYLE`, and a line in `response_format.md`). Under those recipes, the rules
shared by every style contradicted the client's examples: "Direct, not directive, never tell them
what to do"; never ask what made them think it; never ask them to rank; "pressing" banned, though
the client's Directive asks "What feels most pressing right now?"; Reflective never hands their
words back, though the client's Reflective opens "Your chest feels tight and your thoughts are
racing." Splitting the recipes into files alone would only have moved the contradictions.

## What was built

- One prompt row per style (`style_directive`, `style_supportive`, `style_reflective`): the client's
  behavior and heading, their within-framework list, the consent line, two of their conversations.
  Only the thread's style is composed, after `mani_base` and `response_format`.
- The Framework Index prints only that style's offer and Keep chatting wording.
- Cut: the style recipes in `[ctx]`, `question_focus`, `_IN_STYLE`, the question targets in
  `before_an_offer` and the `understanding` meaning, "about ten words", "rank", "pressing",
  "no interpretations" (the client's do-not-label rule already says it).
- `direct` renamed `directive` everywhere (migration 019 rewrites stored styles and any greeting
  still waiting with the old button).
- `scenario_check.py` no longer flags "opens on their words" or "two styles ask the same question":
  both punished the client's own examples. The four client scenarios are in `scenarios.json`.

Kept on purpose, though the plan cut its whole line: "never ask about something that has not
happened yet" (what would it mean, what would it be like if). The client never asks one, and it is
what stopped the worst case walks in [[direct-questions-have-no-target-2026-10-09]].

## To watch in the first live run

- Copied phrases from the examples, such as "I'm sorry you're feeling this way" on every turn (R3).
- "It sounds like a lot is happening at once" is in the client's Supportive example, while
  `mani_base` still bans "a lot" unless they said it. Not resolved; see what the model does.
- A Supportive question shaped like "Would it help to work through...?" matches the offer patterns
  in `repairs.py` and could be stripped as an offer. The chosen examples avoid it; the client's
  overthinking and stress examples use it.

See [[prompt-restructure-2026-10-07]], [[measure-before-tuning-prompts]].
