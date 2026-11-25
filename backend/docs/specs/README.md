# Specifications

The product specifications for Mani's conversational layer, transcribed from the source PDFs so
they live in version control rather than as chat attachments. **These are provenance.** The
implementation source of truth is the code, `backend/PORT-STATUS.md` ("Decisions in force") and the ADR index in
[`mani-vault/Decisions/_Index.md`](../../../mani-vault/Decisions/_Index.md). The content files in
`backend/content/frameworks/` are written from these specs, but where a spec's tone lines carry scenario text
("her silence", "send it") the content uses each stage's primary question instead.

Requirements the client sent after these specs, and the messages they came from, are in
[`docs/client/`](../../../docs/client/README.md). A newer client message beats an older spec.

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

- **When a framework fits and when not to offer it** → each active framework file's `activation`
  (`central_indication`, `contraindications`), seeded into `admin.frameworks.activation`. The model chooses the
  framework from the guide built out of them (`facts.system_prompt`); there is no phrase router.
- **Stage sections (§§11–18)** → `admin.frameworks.stages` jsonb, one entry per phase: each stage's `intro`,
  `purpose` and `ready_when`, and the offering's five steps per style.
- **"Responses MANI Must Avoid"** and the rules repeated across all six → `content/prompts/mani.md`, the one chat
  prompt, and the rule checks of `backend/evals/` (`reply_rules.py`, `cases.json`).
- Active today: ABCDE, Thought Reframe and Structured Problem Solving; the other three are in
  `content/frameworks/paused/`. The body check-in was deleted on 2026-11-17.

## Not in these documents

The specs repeatedly reference **"MANI's approved safety protocol"** and **"the approved safety
clarification"**. Neither text is included here, and neither is the helpline list. They define
precisely *when* safety fires and what MANI must and must not do — not what MANI says.
`mani/chat/crisis.py::RESOURCES` holds three US reference numbers and the Find A Helpline directory until those arrive (see
`backend/PORT-STATUS.md`, "Before it takes real traffic").
