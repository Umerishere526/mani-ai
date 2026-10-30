# Confirm phrases dropped with no stage asking (2026-10-27)

Commit f3e7016 ("fix: add chat flow and admin ui", 2026-10-26) removed `confirm_phrases` from both `abcde.md` and
`thought_reframe.md`. Nothing recorded why, and `walk.confirm_phrase` still reads them: with an empty pool it returns
"", so a stage said back by the fallback ended on a full stop and asked nothing ("B is for Belief. You mentioned I am
useless. "). Nine tests went red on main; five of them were only stale wording against the framework files, whose
requirements (R16 "need not be positive", D's two halves, A's observable trigger) were all still present.

Fixed: both lists restored, and `cache._read` now refuses a framework with no `confirm_phrases`, as it already
refuses one without its body check-in scripts, so the gap cannot come back silently. The stale tests were updated to
the files' current wording, keeping what each one guards.

Lesson: content keys that code reads need a load-time check, not only a test of the file. A test of the file is
the first thing a content edit "fixes" by deletion.
