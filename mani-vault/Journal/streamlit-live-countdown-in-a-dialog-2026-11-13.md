---
type: journal
date: 2026-11-13
apps: [chat-tester]
tags: [journal, streamlit, chat-tester, crisis, pause, lessons]
---

# A live countdown inside a Streamlit dialog (2026-11-13)

2026-11-13. History, not rules. Built for the pause pop-up in `chat-tester/crisis_pause.py` (Streamlit 1.64.0),
checked in headless Chrome against a throwaway page on a spare port.

- An `@st.fragment(run_every=1)` called inside an `@st.dialog` ticks on its own: 0:25 read 0:22 three seconds later,
  with no interaction. The dialog's body is itself a fragment; nesting is supported in this version.
- `st.rerun()` from that fragment reruns the whole page, so a page that no longer calls the dialog closes it. Rounding
  the countdown up (0:00 only once the time is over) keeps a rerun at 0:00 from finding time still left.
- `st.markdown(..., unsafe_allow_html=True)` keeps `tel:` and `sms:` hrefs (its link check only blanks unsafe ones).
- `st.html("<style>...</style>")` with nothing but style goes to the event container and takes no space, so a style
  emitted from inside the dialog applies only while it is open.
- The overlay is `[data-testid="stDialog"]` (flex, `align-items: flex-start`); `margin-block: auto` on its child
  centres the dialog and still lets a tall one scroll from its top. `[data-testid="stDialogIcon"]` is the title icon.
- AppTest renders the fragment once and never ticks; the expiry path is tested by setting the stored pause to one
  that has run out and running the page again.
- Related: [[streamlit-audio-speed-in-the-browser-2026-11-13]].
