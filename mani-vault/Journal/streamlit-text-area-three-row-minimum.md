---
type: journal
date: 2026-10-07
apps: [chat-tester]
tags: [journal, chat-tester, streamlit]
---

# Streamlit's text_area never renders under three rows

## What happened

muhammad wanted chat-tester's composer to behave like WhatsApp's: one line tall, growing only
as text wraps or Shift+Enter adds a line. `height="content"` (Streamlit 1.64) does grow the
field, but it renders the textarea with `rows=3` and only raises that number, plus a 68px
`min-height`. So an empty field was always about three lines tall (84px). Overriding
`min-height` alone changed nothing, because the height comes from `rows`.

## What to remember

- `field-sizing: content` on the textarea sizes it to its text and ignores `rows`. With
  `min-height: 0` and a `max-height` cap, it gives the WhatsApp behaviour: 45px empty,
  growing per line, then scrolling inside. Browsers without `field-sizing` keep the
  three-row box, which still works.
- The field's outline is on the `stTextAreaRootElement` wrapper, not the textarea. The
  "Press ⌘+Enter to submit form" hint is `[data-testid="InputInstructions"]`.
- To check composer CSS and JS without signing in: copy the composer block of `app.py` into
  a standalone page in the scratchpad, run it with chat-tester's venv on a spare port, and
  drive it with Playwright (`channel: 'chrome'` uses the installed Chrome when the cached
  Playwright browser is the wrong version).
