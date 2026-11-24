---
type: journal
date: 2026-11-24
apps: [backend, chat-tester]
tags: [journal, directive, questions, prompt]
summary: "Branch fixing-directive-in-chat, cut from main: each open-chat question now has a job chosen before the words, code keeps a ledger of the questions and their jobs and cuts any extra question or a question after frustration, and Directive is two or three short, human sentences."
---

2026-11-24. muhammad asked for a shorter Directive that leads forward, and a "question engine" that knows what it asked, why, and whether a question fits where it is.

What was built, on main's one-call turn (not on the saved `mani-chat-improvement` work, his choice):

- `TurnReply.question` comes before `text`: `latest` (their message in one word), `intent` (situation, feeling, belief, wants, step) and `why_now`. These are plain strings, so a stray value never fails the call. Code normalises the intent and records anything else as `unsaid`.
- `threads.understanding.questions` keeps the last 12 open-chat replies as `{q, intent}`, with `q` empty when a reply asked nothing. A rewind restores it with the rest of the record.
- `facts.question_lines` tells the next open-chat turn every question asked and its job, and after three replies in a row that ended on a question, tells it to give something and ask nothing unless its question moves them on. The jobs are given as information, not as a to-do list: a fixed order would fight "never steer toward a belief".
- `questions.held_to_one` runs only in the open chat with no set, offer or safety worry. It keeps the last question and deletes the others, and deletes every question when `latest` is frustrated. It never adds words.
- "step" means a step on toward the core and the set, never advice. The no-solutions rule stands.

Known gap: a short "I'd like to understand..." line before a cut question can be left standing. The prompt now keeps that line out of Directive. The rest is marked `ponytail:` in `questions.py`.

Not measured: no live run, by muhammad's rule ([[muhammad-tests-live-himself]]). Main's prompt runs on MiniMax M3.1 Flash, not the saved branch's DeepSeek, so the saved branch's evaluation numbers do not carry over.

Later the same day, muhammad decided `mani-chat-improvement`'s work stays local and out of this branch, and main keeps its one `mani.md`. This branch is main plus the question job, the one-question cut, a Directive that never says sorry, and the new feelings buttons (Feel stronger / Feel more focused / I'm not sure yet). The saved work and a combined version of both are kept in stashes and tags `saved/mani-chat-improvement-2026-11-24` and `saved/fixing-directive-combined-2026-11-24`. Not on this branch, so prod still lacks them: the picture with tense and what was answered, the stage guides for B, D and E, the honest close, let-them-go, and the fixed "So how do you feel about that belief?" question.
