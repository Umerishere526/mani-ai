2026-11-06

# Worktrees share one local database

Three worktrees (`mani-ai`, `mani-ai-somatic`, `mani-ai-codex-latency`) all point at the same local Supabase (`project_id = "mani"`, Postgres 54342). What one branch writes, every other branch reads.

What it cost: on `feat/chat-feedback-core-latency`, New chat went straight to the body check-in. The cause was not this branch. `feat/somatic-only-chat` ("open a new conversation on the body check-in", 74a2b48) had created three threads for `muhammad@example.com` that start at `somatic_ask` with no message from the person. `threads.create_or_reuse` treats any thread without a user message as unused, so New chat handed one of those back.

Second lesson from the same session: `supabase migration list --local` said 031 and 032 were applied, but `threads.pending_follow_up` did not exist and `authenticated` still held INSERT on `threads`. Every send failed with `UndefinedColumnError`. The history table is not proof a migration ran; check the schema itself (`information_schema.columns`, grants) when a branch's code fails on a column. The gap was already in the dump taken before the restart, so it predates that session; how the history got ahead of the schema is unknown.

- Before testing a branch locally, check which threads its user already has, or give each worktree its own stack.
- Related: [[local-db-migration-up-not-reset]] (memory), `.claude/BACKEND.md` ports note.
