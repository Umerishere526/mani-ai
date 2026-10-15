---
type: journal
date: 2026-10-14
tags: [journal, prompts, questions, working-read, measured]
---

# Questions that join the feeling to the situation (2026-10-14)

muhammad's Supportive chat: frustrated -> everything -> client keeps changing requirements ->
"How is this affecting you?" -> "i told you that" -> "Would you rather I listen, or help?" on the
third real reply.

## Two causes, both reproduced by replaying the transcript (reasoning and read printed per turn)

- Supportive's `question_focus` was "how it sits with them", so with a feeling already named the
  question came out as the generic "how is this affecting you", which "frustrated" had answered.
- `support_check` fired on `situation and (impact or response)`. The model filled `response` with
  "They make the changes", a fact of the situation, so heard-or-help was asked with nothing explored.
  Gate is now `situation and impact`.

## Fix and result

A `before_an_offer` rule: put the feeling to the part of the situation known least, looking across
the whole read; never a general how-is-this-affecting-you. Same line in the reasoning step.
Replayed with realistic answers: questions went to how long, what they do when it happens, what it
costs their week, and heard-or-help came only after they described working late.

## Watch

- The model can still fill `impact` with an echo ("Going back and forth with the teams"), which
  opens the check early. Not guarded in code.
- A colon-space inside a prompt bullet turns it into a YAML mapping; `test_composer` catches it.
- The provider stalled twice in one hour (83s call, then a 60s cut by the new total timeout).

## Question memory ablation (same day)

12 scripted conversations, Supportive, OpenAI direct, flags from `scenario_check`: no question memory 9 flags
(7 repeated questions), questions only 2, questions with their replies 3. So it is required, and the answer
beside each question is unproven either way. A structural guard for echoed `impact` was tried and dropped: the real
echo shares ~20% of its words with the situation line, so word overlap cannot catch it. See [[mani-forms-a-read-instead-of-mirroring-2026-10-13]].
