# Specifications

The product specifications for Mani's conversational layer, transcribed from the source PDFs so
they live in version control rather than as chat attachments. **These are provenance.** The
implementation source of truth is `mani/Programme/conversational-architecture.md`, which
reconciles the contradictions between them.

| File | Source | What it carries |
|---|---|---|
| `conversational-styles.md` | *Directive. Supportive. Reflective.* | The three styles, the full conversation cadence, the greeting and style-selection flow, the somatic check-in wording, per-style behaviour inside a framework, worked scenarios across all three styles |
| `six-frameworks-overview.md` | *Six Frameworks for App* §§1–7 | The comparison table, the selection table, the pairwise distinctions, the safety exception, and the rules and failure modes shared by all six |
| `framework-abcde.md` | Framework 1 | |
| `framework-thought-reframe.md` | Framework 2 | |
| `framework-behavioral-activation.md` | Framework 3 | |
| `framework-structured-problem-solving.md` | Framework 4 | |
| `framework-act-choice-point.md` | Framework 5 | |
| `framework-dbt-stop.md` | Framework 6 | |

Each framework file follows the source's own numbering: therapeutic purpose, governing rules,
mirror cadence, tone by style, when appropriate, **what MANI may hear**, what must be understood
before offering, when not to use, differences from similar frameworks, how it is offered, then
the stage-by-stage requirements — purpose, primary question, listening cues, mirror examples,
tone variations, readiness criteria, unclear-answer handling, boundaries, progression,
completion, completion question, somatic transition, a full worked example, and **responses MANI
must avoid**.

## How the code uses these

- **"What MANI may hear"** → the rule-based router's phrase patterns, seeded into
  `admin.frameworks.activation`. Free: no API call.
- **"Important Framework Distinctions"** and each file's §9 → the router's tie-breakers.
- **Stage sections (§§11–18)** → `admin.frameworks.stages` jsonb, one entry per phase, with the
  three tone variants at the `ask` leaf only.
- **"Responses MANI Must Avoid"** → `tests/evals/` negative assertions, which run with no model
  call.
- **Worked examples (§23)** and the styles doc's scenarios → the routing and
  style-differentiation eval sets.
- **Rules repeated across all six** → the shared `post_framework` prompt layer, written once.

## Not in these documents

The specs repeatedly reference **"MANI's approved safety protocol"** and **"the approved safety
clarification"**. Neither text is included here, and neither is the helpline list. They define
precisely *when* safety fires and what MANI must and must not do — not what MANI says.
`mani/chat/crisis.py::RESOURCES` stays empty until those arrive.
