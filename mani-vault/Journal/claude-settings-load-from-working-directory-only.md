---
type: journal
date: 2026-09-11
apps: [mobile, web, backend]
tags: [journal, tooling, claude-code]
---

# Claude Code settings load from the working directory only

## What happened

While folding `mobile/` into the root monorepo, `mobile/.claude/settings.json` turned up
alongside the root `.claude/`. It held one key — `enabledPlugins` enabling
`expo@claude-plugins-official`.

I first assumed it was directory-scoped: active while working under `mobile/`, and that
merging it to the root would widen its scope as a deliberate trade. muhammad pushed back
and asked whether the original arrangement was actually good. Checking the docs via the
`claude-code-guide` agent showed the assumption was wrong.

## Insight

**Claude Code reads project settings only from the session's primary working directory.**
There is no nested, inherited, or file-triggered directory scoping. A `.claude/` in a
subdirectory is never loaded unless a session is started from that subdirectory.

So `mobile/.claude/settings.json` was dead weight, not a narrower scope. Since the root
CLAUDE.md tells us to `cd mobile` *within* a session rather than launching there, the Expo
plugin was almost certainly never enabled at all. Merging it to the root is the first time
it actually takes effect — not a widening of something that worked.

Related facts worth keeping straight:

- Precedence, highest first: managed settings → command line (`--settings`) →
  `.claude/settings.local.json` → `.claude/settings.json` → `~/.claude/settings.json`.
- List-valued keys like `enabledPlugins` **merge** across levels rather than one winning.
  muhammad's `~/.claude/settings.json` curates plugins deliberately (most `false`), and
  does not mention Expo — so the root project file is the only thing enabling it.
- `/cd` re-reads project files from the new directory, but needs Claude Code 2.1.246+.
  We were on 2.1.240, so it did not apply.

The correction that matters most is not the settings fact. It is that I stated harness
behavior confidently from memory and was wrong, and it took muhammad questioning it to
surface that. Docs are cheap to check; confident recall about tooling is not trustworthy.

## Applies to

- Any time a `.claude/` appears outside the repo root — it does nothing. `*/.claude/` is
  now gitignored and the rule is in the root CLAUDE.md.
- Any time per-app tooling behavior is wanted. It is not achievable through settings;
  use `.claude/WEB.md` / `.claude/MOBILE.md` / `.claude/BACKEND.md` and the skills, which
  scope by content rather than by directory.
- Any claim about Claude Code's own behavior — settings, hooks, skills, plugins, MCP.
  Verify with the `claude-code-guide` agent first.

## Links

- [[Mobile]]
- [[ADR-001-project-knowledge-lives-in-two-places]]
