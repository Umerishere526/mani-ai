---
type: journal
date: 2026-11-18
tags: [journal, framework, client, offer, eval, lessons]
summary: "The framework follows the client's sequence document: a lead-in, her five steps verbatim, and one reply per letter."
---

# The framework runs the way the client's sequence document shows

2026-11-18. The client sent "Framework Sequences - Example Conversations" (recorded in
`docs/client/messages/2026-11-18-framework-sequences.md`): one scenario, three styles, the ABCDE delivery she intends.
muhammad scoped it to the framework part only and kept the letter lines and our closing buttons.

What changed: the offer is a lead-in (Not sure / Show me how / Give me a tool), then her five steps word for word, then
Start ABCDE / I need an example / Talk more first; every letter is its own reply (code no longer lets the starting turn
reach B); E ends on the new belief, then how they feel (Stronger / More focused / Still a bit tired), then the close;
Directive is short; suggestion buttons in the chat. Talk more first lapses rather than declines, and a typed answer to
the lead-in gets the reply plus the steps (muhammad's answers to the builder check).

Lessons:

- A prompt line can contradict the client's own example and lose the gate for it: "leave options empty when the
  question is open-ended" stopped suggestions for "what's causing the pressure?", the client's very example. The rule
  case caught it; the fix was to describe the kind of question, with her example.
- A builder check before planning paid off: four of its questions changed what was built (typed lead-in answers, the
  gate for short Directive, E's path, what Talk more first means).
- The eval crashed twice on OpenRouter's in-flight budget (402) and once on a dropped connection; each lost a whole run.
  It now waits, caps the judge's output, runs four at a time and records a failure instead of crashing.
- A "Not sure" button on a stage was removed on 2026-10-09 because its taps skipped stages
  ([[stages-are-skipped-not-confirmed-2026-10-09]]). The client's "Not sure" sits only under the lead-in, where a tap
  shows the steps and cannot skip a stage.
- Five chat-tester tests (copy button, nickname, password reset) failed with "OSError: could not get source code"
  from Streamlit's AppTest whenever local Supabase was up. The cause was not our code: their cached bytecode
  (`__pycache__`, gitignored) had been compiled on 2026-11-04 by a sandboxed session that mounted the repo at
  `/sessions/.../mnt/...`, and pytest kept reusing it because the sources had not changed, so `inspect` looked for the
  test file at that path. Sixty such caches were deleted; all 55 tests pass. If `inspect` or AppTest ever reports
  source it cannot find, check `code.co_filename` in the `.pyc` before anything else.

Supersedes the path part of [[framework-progression-and-plan-next-step-2026-11-06]]. See
[[flat-replies-were-the-model-2026-11-17]].
