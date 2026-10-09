---
type: journal
date: 2026-10-09
tags: [journal, prompts, questions, wording, build]
---

# Short plain questions: built as spec 0017

Spec: `docs/specs/0017-mani-asks-short-plain-questions.md`. Scope feature 23. Built on top of the uncommitted spec 0010 amendment.

## Counts (AC-8)

`wc -lw content/prompts/mani_base.md content/prompts/response_format.md`, on the working tree:

- Before the edits: 145 lines, 3360 words (74 and 71 lines; 1784 and 1576 words).
- After the edits: 145 lines, 3278 words (74 and 71 lines; 1748 and 1530 words).

No line added, 82 words fewer. Every after text matched the ACs exactly, checked by a scratchpad script against the file lines, and none of the cut phrases is left in either file. Nothing in `mani/`, `tests/` or `scripts/` quoted a cut phrase.

## Seed and tests (AC-7, AC-9)

`python scripts/seed.py` accepted all six frameworks and ten prompts. The seeded rows hold the new text. The only "in their words" left in `admin.frameworks` is the `Starts when` line of `thought_reframe`, as the spec keeps it.

The running `fastapi dev` server does not reload on a `.md` edit. `touch main.py` restarts its worker (new pid), which clears the in process prompt cache without changing a file's content.

Whole `pytest`: 700 passed, 4 skipped (the four JWKS symmetric token skips, as before). `tests/integration` alone: 155 passed, none skipped.

## The three runs (AC-10)

After muhammad's yes. Credit 18.08 dollars of 60 before, 18.05 after: the three runs cost about 0.03.

The eval deletes its users at the end, so a scratchpad wrapper (`run_0017.py`) wraps `ev._open_chat` and runs `select conversation_style from public.threads where id = $1` as the thread's owner right after the style tap. Every thread had its style stored:

| Style | Thread | Stored |
|---|---|---|
| direct | 9df1fe8c | direct |
| supportive | 9ff57e01 | supportive |
| reflective | cab7ca4c | reflective |

What got better: the C question now reads like the client's in every style. Direct: "How has thinking you're bad at your job affected what you've felt or done?" Reflective: "How has thinking you're bad at your job affected how you feel or what you've done since?" The D questions are plain too ("What makes it seem true that you're bad at your job, and what makes you question it?").

Replies Claude read as breaking the bar (muhammad's verdict pending):

- Direct: "The criticism is real, and so is being asked to lead the next project. What's a fair way to see your ability that makes room for both?" (story said back, "a fair way to"). "You can recognize that the presentation had gaps without treating it as proof that you're bad at your job. How do you feel about yourself now, looking at it that way?" (story said back). After the framework, each reply opens by saying back what they said ("The meeting is still on your mind.").
- Supportive: "That lets the feedback about one presentation be real without making it a verdict on your whole job. How does that thought sit with you now?" ("verdict", "sit with you"). "What's a realistic way to hold both of those things in mind?" after a restatement. "gently press your feet into the floor and notice the support under them."
- Reflective: "What part of that is weighing on you most?" after a restatement. "What feels like a fair, believable way to think about your work, taking both into account?" "How does that view sit with you now?" after "a verdict on all your work". "press your feet gently into the floor and notice the support beneath them." "finding steadier footing at work."

The pattern: the say back and the fancy phrases now cluster on the E stage, the closing and the body check, not on C and D. "sit with you" and "notice the support beneath them" both came back word for word from the before sample. That points at the levers in 0017's Follow-up: the `mirror and ask` shape and `mirroring` move for the say back, "gentle attention to where they feel it" in `ending` line 3 for the body check, and the after framework `[ctx]` line, which says "Reflect what they said, then ask".

## Eval findings, not part of AC-10

The eval also failed checks that are not about wording: no Chat More button to tap in all three runs, Direct never asked the after framework questions word for word, Supportive never reached the body check (the stage cap passed `effective_new_belief` after two turns with no stages reported). `journey_abcde` came in with the uncommitted 0010 work and has no earlier recorded run, so there is no before to say whether these cuts caused any of them.

Related: [[short-plain-questions-design-2026-10-09]], [[stage-skip-and-short-questions-scope-2026-10-09]], [[understand-then-offer-build-2026-10-08]]
