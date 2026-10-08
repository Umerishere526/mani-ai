# Specifications

The product specifications for Mani's conversational layer, transcribed from the source PDFs so
they live in version control rather than as chat attachments. **These are provenance.** The
implementation source of truth is the code, and `backend/PORT-STATUS.md` records the decisions in force. The content files in `backend/content/frameworks/` are checked
against these specs, but where a spec's tone lines carry scenario text ("her silence", "send it") the
content uses each stage's primary question instead: `tests/evals/test_negative_set.py` rejects an ask that
names someone or hands over a feeling word.

| File | Source | What it carries |
|---|---|---|
| `conversational-styles.md` | *Direct. Supportive. Reflective.* | The three styles, the full conversation cadence, the greeting and style-selection flow, the somatic check-in wording, per-style behaviour inside a framework, worked scenarios across all three styles |
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

- **"What MANI may hear"** → each framework's Starts when, Sounds like and Skip when lines, which the
  model reads; the one phrase list in code is the grief veto, `never_offer_when_said`, seeded into
  `admin.frameworks.activation`.
- **"Important Framework Distinctions"** and each file's §9 → the Skip when lines, which the model reads.
- **Stage sections (§§11–18)** → `admin.frameworks.stages` jsonb, one entry per phase, with the
  three tone variants at the `ask` leaf only.
- **"Responses MANI Must Avoid"** → `tests/evals/` negative assertions, which run with no model
  call.
- **Worked examples (§23)** and the styles doc's scenarios → the routing and
  style-differentiation eval sets.
- **Rules repeated across all six** → `content/prompts/mani_base.md` (conversation rules and tone) and, for the body check after a framework, its `ending` section, with `scripts/seed.py` appending the two ending phases to every framework (spec 0009 replaced the fixed check in and practices with rules the model follows).

## Not in these documents

The specs repeatedly reference **"MANI's approved safety protocol"** and **"the approved safety
clarification"**. Neither text is included here, and neither is the helpline list. They define
precisely *when* safety fires and what MANI must and must not do — not what MANI says.
`mani/chat/crisis.py::RESOURCES` stays empty until those arrive.
