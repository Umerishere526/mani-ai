---
type: journal
date: 2026-10-06
apps: [backend]
tags: [journal, frameworks, semantic-router, cadence]
---

# Framework overlap, closest-fit offers, and stage bypass: what the code does today

Measured before reviewing Lolly's transcripts, so the transcripts are read against real
behaviour rather than assumptions.

## Framework overlap is real, but the exemplars separate better than the frameworks do

Max exemplar-to-exemplar cosine between frameworks:

| pair | similarity |
|---|---|
| ABCDE ↔ Thought Reframe | **0.624** |
| Behavioral Activation ↔ Structured Problem-Solving | 0.530 |
| ACT Choice Point ↔ Thought Reframe | 0.496 |
| ACT ↔ Behavioral Activation | 0.464 |
| DBT STOP ↔ Thought Reframe | 0.452 |

ABCDE and Thought Reframe genuinely overlap: both are "an event made me believe something
bad about myself", and the specification separates them only by depth (whole sequence vs one
thought). That is a content problem, not a routing bug.

Routing still separates them in practice, because the *exemplars* are distinct even where the
frameworks are close:

| message | status | top | margin |
|---|---|---|---|
| "manager criticised me… now i think i'm bad at my job" | match | abcde | 0.355 |
| "friend hasn't replied, i'm sure she hates me" | match | thought_reframe | 0.503 |
| "made a mistake, everyone sees me as careless" | match | thought_reframe | 0.346 |
| "she was short with me, i decided i'm not good enough" | match | abcde | 0.246 |
| "i keep putting off this decision" | match | behavioral_activation | 0.214 |
| "report due monday and i can't get started" | **ambiguous** | sps | 0.000 |

## The closest fit is offered, but only at the end of the window

`offer.decide` offers the nearest candidate on AMBIGUOUS or WEAK_MATCH **only** when
`their_messages >= latest` (Direct 5, Supportive 9, Reflective 10). Before that it asks.

muhammad, 2026-10-06: a fit we are not fully sure of should be offered *the same way* a clear
one is, not held to the end of the window. The current gate makes an ambiguous-but-obvious
situation wait several turns for anything to happen.

## Stage skipping is clamped, which contradicts the bypass requirement

`Registry.clamp` rewrites any forward jump back to the immediate next stage
(`SKIPPED_PHASES` → `expected_next`). So when a person cannot answer what a stage needs,
Mani cannot move on toward the ending; it is pulled back into the same stage.

What exists instead: `context.build` emits a `stage_note` after the stage has been asked
twice (follow them) and three times (take what they gave and move on). That is prompt
guidance the clamp then partly undoes.

## Somatic is structurally compulsory

Every framework ends `… > closing > somatic_checkin > somatic_practice`. Confirmed in
`admin.frameworks.phases` for all six. So "somatic must kick in every time" holds by
construction - provided a bypassed stage still routes to the ending rather than stalling.

## Also found, unrelated to the above

- **Embedding calls are not cost-tracked.** The semantic router calls OpenRouter but writes
  no `admin.llm_calls` row; the `route` purpose and its migration were planned and never
  built. Small money, invisible spend, and the before/after measurement depends on it.
- **Static prompt is ~16.4k tokens** (mani_base 33k chars + response_format 20k + index 12k),
  up from ~10.8k, from the prompt rewrites rather than the router.
- **"Finding the fit" is still in the prompt** (~3k chars). It exists so the *model* picks a
  framework, which code now owns: a second, competing decider.

## Links

- [[persona-prompt-merge-2026-10-05]]
- [[ADR-015-a-question-is-asked-when-it-earns-its-place]]
