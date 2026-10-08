---
type: journal
date: 2026-10-07
tags: [journal, prompts, frameworks, lessons]
---

# Prompt text names index sections and [ctx] lines by title

Found while designing spec 0005 (frameworks in eight lines). `content/prompts/mani_base.md`,
`content/prompts/response_format.md` and the redraft notes in `mani/chat/redraft.py` refer to the
Framework Index's section titles ("Finding the fit", "Never offer one when") and to `[ctx]` line
names (`offer_ask`, `stage_ready_when`, the per stage "model question") by their exact text.

Nothing ties them together. Rename or remove a section in `composer.framework_index` or a line in
`context.build` and the prompt keeps telling the model to read something that no longer exists, with
every test still green. The first draft of 0005 missed this; an independent cross check caught it.

When a change removes or renames an index section or a `[ctx]` line, grep `content/prompts/` and
`mani/` for its name in the same change. Spec 0005 adds a test that fails on the removed names.

Related: [[measure-before-tuning-prompts]], [[seeded-content-turns-dormant-paths-live-in-tests]].
