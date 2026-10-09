---
type: journal
date: 2026-10-08
tags: [journal, prompts, styles, offers, client, build]
---

# Building spec 0012: Mani speaks and asks as the client wrote

Spec: `docs/specs/0012-mani-speaks-as-client-wrote/`. Scope feature 14. Design: [[client-cadence-design-2026-10-08]].

## Counts (AC-9, AC-12)

- `wc -lw` on `mani_base.md` plus `response_format.md`: 150 lines and 3,616 words before, 148 and 3,460 after.
- `pytest` before: 666 passed, 4 skipped. After: 667 passed, 4 skipped (the four JWKS tests, as before). 139 integration tests ran both times, so none were skipped.
- The one more: 3 tests deleted (`question_focus`, two `clarification_lines`), 4 added (the leftover `clarification_lines` refusal case and three `REMOVED` names).
- Reseeded after muhammad's yes. His `fastapi dev` server was running and reloads on code change, so I left it alone; its prompt cache takes the new rows within 300 seconds.

## Real runs (AC-11), one each, not rerun

| Scenario, style | First offer | Result |
|---|---|---|
| `client_anxiety`, Directive | `[None]` | fail |
| `client_overthinking`, Reflective | `['2:thought_reframe']` | pass |
| `client_stress`, Supportive | `['2:structured_problem_solving']` | pass |

None of "I hear you", "That makes sense" or "I'm here for you" anywhere. "I'm here with you" came in the Directive and Reflective runs, and the validator flags it as presence outside Supportive.

The anxiety fail is not the style line. "My chest feels tight" set off the pain check: `offers` line 4 ("If they mention pain… ask which once before offering") and the `crisis` field's injury guidance. Mani asked whether the tightness was new or severe twice, so it also broke "ask which once". The client's Directive example checks instead ("Does it feel like your body is activated…?") and offers on the next message. Whether the medical check should give way here is muhammad's call: it is a guardrail, and the spec's "adjust the style line" fix does not apply.

## Gotchas

- **zsh does not split `$r`.** `for r in "a b"; do set -- $r` left `$2` empty, so `--style` got no value and argparse exited 2 before any model call. Write the commands out, or use `${=r}`.
- **The tap check is free.** The greeting and the style tap come from the `replies` row with no model call, so opening a thread per style and reading `threads.conversation_style` proves the Directive button still stores `direct` at no cost.
- `client_overthinking` also holds only three user messages, so its window is 2 to 3, the same as anxiety and stress. The spec named only those two.

## Noticed, not fixed

- `backend/docs/specs/conversational-styles.md` says the implementation source of truth is `mani/Programme/conversational-architecture.md`, which does not exist.
- The October 8 style document ends with an ABCDE "Tell me more" example (the five steps, then "Would you like to try the framework now or keep chatting."). It is offer wording, so it belongs to feature 15, and I left it out of `conversational-styles.md`.
- `tests/evals/validators.py` still says "Direct" in a docstring about the style.

Related: [[offer-late-root-cause-prompt-not-code-2026-10-08]], [[client-lines-the-code-matches-exactly]], [[seeded-content-turns-dormant-paths-live-in-tests]]
