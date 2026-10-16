export const meta = {
  name: 'review-chat-change',
  description: 'Review a backend chat change: code review of the diff, live off-script conversations, then verify each finding',
  whenToUse: 'After a change to backend/ chat behaviour (prompts, walk, body route, orchestrator), before telling muhammad it is done',
  phases: [
    { title: 'Review', detail: 'one code reviewer on the diff' },
    { title: 'Edge hunt', detail: 'off-script conversations run live through scenario_check' },
    { title: 'Verify', detail: 'one skeptic per finding, defaults to refuted' },
  ],
}

// args: { range?: 'BASE..HEAD' (uncommitted changes when omitted), about?: what changed and why }
const range = args?.range
const about = args?.about ?? 'Read the diff and infer what changed.'
const diffCmd = range ? `git diff --stat ${range} && git diff ${range}` : 'git diff --stat && git diff && git status --short'
const MAX_VERIFIED = 7

const FINDINGS = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          severity: { type: 'string', enum: ['critical', 'important', 'minor'] },
          file: { type: 'string' },
          line: { type: 'integer' },
          summary: { type: 'string' },
          evidence: { type: 'string', description: 'code quote, or the transcript lines that show it' },
        },
        required: ['severity', 'file', 'summary', 'evidence'],
      },
    },
  },
  required: ['findings'],
}

const VERDICT = {
  type: 'object',
  properties: {
    refuted: { type: 'boolean' },
    reason: { type: 'string' },
  },
  required: ['refuted', 'reason'],
}

const READ_ONLY = 'Do not edit, stage or commit anything in the repo, and never touch backend/.env.hosted.'

const review = () => agent(
  `You are a senior code reviewer for MANI's FastAPI backend (backend/). Review this change.

What changed: ${about}

Get the diff from the repo root: ${diffCmd}
Read backend/PORT-STATUS.md "Decisions in force" and .claude/BACKEND.md first.

Judge against how this codebase works: one model call per turn; code acts on closed-set labels the model
reports (stage_answer, body, check_answer, offer_answer), never on phrase lists over the conversation;
client text in content/ is sent word for word; every content/ edit needs scripts/seed.py.

Look for: bugs and unhandled edge cases (what turn sequence breaks it?), a stage or route that can hold a
person for ever, state that can strand a thread, tests that only test mocks, orphans left behind, and
breaks of CLAUDE.md's rules. Run \`cd backend && source .venv/bin/activate && pytest -q\` and report any
failure as a finding. For behaviour the plan is silent on, judge by what a person chatting would expect.
${READ_ONLY} Do not spawn subagents. Return only real problems, each with file, line and evidence.`,
  { label: 'code review', phase: 'Review', schema: FINDINGS },
)

const hunt = () => agent(
  `You hunt edge cases in MANI's chat by running real conversations against the local model.

What changed: ${about}
Diff, from the repo root: ${diffCmd}

1. Read the diff, backend/scripts/scenarios.json (the format) and the off_script_after_e group.
2. Write 3 to 6 new conversations that go off script exactly where this change acts: questions instead of
   answers, push-back, a new problem mid-way, one-word replies, a sensation or feeling named early, stopping.
   Put them in a temporary file outside the repo (mktemp), in the scenarios.json format.
3. Run each style: cd backend && source .venv/bin/activate && python scripts/seed.py &&
   python scripts/scenario_check.py --scenarios <file> --style <style> --full
   (styles: directive, supportive, reflective). Scripted lines do not follow the walk, so read where each
   line really landed before judging.
4. Report what a person would find wrong: Mani held on one question, a question ignored, client text
   reworded, a stage skipped or repeated, the wrong fixed text, buttons missing or wrong. Quote the
   transcript lines and point at the code that causes it when you can.
${READ_ONLY} Delete your temporary file when done.`,
  { label: 'edge hunt', phase: 'Edge hunt', schema: FINDINGS },
)

const verify = (finding, source) => agent(
  `Try to refute this ${source} finding about MANI's backend. Default to refuted=true unless you can
reproduce it from the code (trace the exact turn) or the quoted transcript shows it beyond doubt.

${finding.severity}: ${finding.summary}
At: ${finding.file}${finding.line ? `:${finding.line}` : ''}
Evidence: ${finding.evidence}

Change under review: ${about}
Diff: ${diffCmd}
${READ_ONLY}`,
  { label: `verify ${finding.file}`, phase: 'Verify', schema: VERDICT },
).then(v => (v && !v.refuted ? { ...finding, source, why: v.reason } : null))

let budgetLeft = MAX_VERIFIED
const results = await pipeline(
  [{ run: review, source: 'review' }, { run: hunt, source: 'edge hunt' }],
  item => item.run(),
  (found, item) => {
    const all = found?.findings ?? []
    const taken = all.slice(0, Math.max(0, budgetLeft))
    budgetLeft -= taken.length
    if (taken.length < all.length) log(`${item.source}: verified ${taken.length} of ${all.length}; the rest are unverified below`)
    return parallel(taken.map(f => () => verify(f, item.source)))
      .then(v => ({ confirmed: v.filter(Boolean), unverified: all.slice(taken.length) }))
  },
)

const order = { critical: 0, important: 1, minor: 2 }
const confirmed = results.filter(Boolean).flatMap(r => r.confirmed).sort((a, b) => order[a.severity] - order[b.severity])
const unverified = results.filter(Boolean).flatMap(r => r.unverified)
return { confirmed, unverified }
