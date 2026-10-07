---
type: journal
date: 2026-10-04
tags: [journal, evals, conversation, baseline]
---

# The client style check and its baseline

Scope row 32 of `docs/scope/conversation.md`. How to run it and what it counts: `.claude/BACKEND.md` and
`backend/PORT-STATUS.md`. The numbers from the first run are under "Latest measurements" there. This note holds what
the build taught us. Follows [[measure-before-tuning-prompts]] and [[overfit-prompt-and-natural-mani-direction]].

## What we learned building it

- The model writes "I am here with you", not "I'm here with you". A phrase list matched on the client's spelling
  missed it in the first smoke run. Text is normalised before matching now.
- The style keys in the yaml are the app's (`direct`), not the client's word ("Directive").
- The client's "Yes." lines answer the client's own Mani questions. A real model asks something else, so some
  "Yes." turns are non sequiturs. The noise is the same in every run, so before and after still compare, but read
  those transcripts knowing it.
- Each reply carried exactly one "?" in the baseline, including the first reply inside a framework. That is
  ADR-008's shape showing up in the data, so "fewer questions" will appear as replies with no "?".
- One run is noise: panic Reflective offered at message 6, 4 and 2 on the same script. Compare means of three.

## Open

- The baseline lives in the gitignored `backend/.eval/client_style/baseline/` until muhammad decides where a
  committed copy goes.
- The check stops one reply after the offer is accepted. Replies inside a framework are not measured; the client's
  document gives no person lines for that part.
