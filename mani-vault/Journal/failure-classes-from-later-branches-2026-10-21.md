2026-10-21

# Why the later branches went off the rails, and what stops it recurring

We restarted from `fix/run-cleanup-02` (head a1952fa, same as `fi/run-cleanup`) because the chat and the implementation on
`feat/thought-reframe` (specs 0007 to 0012) and `feat/case-cadence` drifted from what the client liked. These are the
failure classes found in their journals. History, not rules: judge the code on its merits, but check a change against
this list before making it. Links go to the notes on `feat/case-cadence` (`git show feat/case-cadence:mani-vault/Journal/<name>.md`).

1. **Patching one transcript with a case rule.** A coworker offer was fixed twice before "thousands of use cases"
   ([[general-judgment-over-case-patches-2026-10-12]]); a ban on a shape swings to the opposite shape
   ([[direct-questions-have-no-target-2026-10-09]]).
2. **The prompt grows and its phrases get spoken.** "Most of the time, say what you want to understand" became every
   reply; an example beats a rule. Cut, never add. See [[plain-questions-not-rewritten-2026-10-12]] and, on the later branch,
   `framing-step-became-every-reply-2026-10-16`, `the-model-writes-in-the-voice-of-the-instructions-2026-10-20`.
3. **Specs outran measurement.** Seven specs in seven days, a judge built then deleted with no baseline, one run read as
   signal ([[measure-before-tuning-prompts]]; `tuning-timing-not-comprehension-2026-10-18`).
4. **Gates stacked on the model.** The offer window, the check yes-gate, a deadline, a model-timed offer and a reason-wait
   each looped or stalled; a deadline skipped a real answer ([[offer-window-owned-by-code-2026-10-12]];
   `forced-check-skipped-a-real-answer-2026-10-16`, `model-timed-offer-never-came-2026-10-16`,
   `check-due-without-a-stored-case-2026-10-21`, `reason-wait-and-activation-undone-2026-10-21`).
5. **Memory and the stage walk.** "Asked again though said" returned five rounds in a row; fields the model sets for itself
   default to omission ([[transcript-is-the-memory-2026-10-13]], [[reach-judged-in-its-own-field-2026-10-14]]).
6. **Layout and format fixed again and again.** A one-character check dropped a valid offer
   ([[quoted-question-dropped-offer-2026-10-12]]); layout belongs in code ([[reply-layout-in-code-2026-10-14]]).
   2026-10-21: the reply shape was touched three times in one day before the options line moved into `repairs.laid_out`.
7. **Feeling first.** Reading the feeling first built the reply on it before the situation was known
   ([[restating-is-not-reflecting-2026-10-12]], [[running-understanding-and-one-question-rule-2026-10-13]]).
8. **Offering too early, then too late.** R1 offered at turn 1; then nothing offered on a confirmed case
   (`confirmed-case-still-went-in-circles-2026-10-21`).
9. **Comprehension ignored while timing and format were tuned.** The client ranks comprehension first; cutting effort for
   latency traded it away (`tuning-timing-not-comprehension-2026-10-18`, `version-b-remembered-by-model-work-not-storage-2026-10-13`).
10. **Decisions outlived their cause**, and replaced decisions left argument lines behind
    ([[stages-are-skipped-not-confirmed-2026-10-09]]; `stage-questions-from-the-conversation`, `open-window-read-as-offer-now`).
11. **Tooling.** A YAML bullet containing `: ` becomes a mapping, so run the tests before a live run. Reseed after every
    content change, and reset the database when switching branches ([[reverting-code-does-not-revert-the-database]]).

## What we do instead (from the 2026-10-21 restart)

The third step before the check became the underlying feeling by swapping one key in the existing machinery, with no new
gate and no longer prompt (a test holds `mani_base.md` to its size). See `backend/PORT-STATUS.md`, "Decisions in force".

## 2026-10-22: the options line, a fourth change to the reply shape

The options under the question went missing twice because a prose rule lost to three "one question" lines. The fix was not a fourth
prompt edit but a required-to-consider schema field (`options`) laid out by code. Rule of thumb: what must always be there is a
reply field, not a sentence in the prompt.
