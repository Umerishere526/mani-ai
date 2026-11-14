---
type: journal
date: 2026-11-14
apps: [backend, chat-tester]
tags: [journal, library, feedback, streamlit, worktree]
---

# Library feedback, built beside another session

2026-11-14.

- muhammad ran another session in the main checkout on `feat/crisis-handling`, with migration `037_chat_pauses.sql` uncommitted there and already applied to the shared local database. This work went into its own worktree (`../mani-ai-library-feedback`, branch `feat/library-feedback` from `origin/main`) and took migration 038. Don't switch branches or stash in a checkout another session is using: `git stash` is shared by every worktree of the repository.
- The reply feedback (👍/👎 under Mani's replies) is on `feat/feedback-per-response`, unmerged and based on PR #48. Its migration is `031_message_feedback.sql`, a number `main` already uses, so it needs renumbering before it lands. The library feedback reuses its `FeedbackIn`/`FeedbackOut`/`FeedbackRating` shapes, defined identically, so whichever branch merges second keeps one copy.
- `scripts/test_db.sh` always recreates `mani-pg-test` on port 55432. Running it while another session uses that container wipes theirs, so this run used a copy with its own name and port (`mani-pg-libfeedback`, 55436). A fresh test database needs `scripts/seed.py` (with a dummy `OPENROUTER_API_KEY`) before `test_turn.py` passes.
- In the tester the 👍/👎 row is an `st.fragment`, so a tap reruns only the row. Measured in headless Chrome, an exercise kept playing (same signed link, time still advancing) through a tap, and the reason field appeared about 0.1 s after it. A full rerun would re-sign every link and stop the audio ([[streamlit-audio-speed-in-the-browser-2026-11-13]]).
- AppTest's `.run()` reruns the whole script even for a fragment, so a fake backend in a test must keep what was saved, or the page reads back an unrated exercise.
- zsh reads `"$B:c..."` as a parameter modifier: write `"${B}:chat-tester/..."` when building a `git show` path from a variable.
