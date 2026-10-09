---
type: journal
date: 2026-10-09
apps: [chat-tester]
tags: [journal, chat-tester, streamlit]
---

# st.chat_input has a mic and can be filled from code

## What happened

chat-tester's composer was built by hand: an `st.audio_input` panel behind a mic toggle, an
`st.form` with a `text_area`, about 60 lines of CSS, and two `components.html` scripts, one
to keep the floating bar aligned with the content column, one to send on Enter. The reason
given in a comment was that `st.chat_input` "has no way to seed the field from a voice
transcript". On Streamlit 1.64 that was false, and nobody had checked the signature.

## What to remember

- `st.chat_input(accept_audio=True)` puts a mic inside the input. The return value is a
  `ChatInputValue` with `.text` and `.audio` (a WAV `UploadedFile`, 16 kHz by default).
  Recording submits on stop; there is no listen-back before it is submitted.
- `st.session_state[key] = "..."` sets the field's text, as long as it happens **before**
  `st.chat_input` is called in that run (or in a callback). After it renders, writing the key
  raises. So a transcript is held in its own state key for one rerun, then written to the
  input's key at the top of the next.
- Verified with `AppTest`: after the write, the element's proto carries `value` and
  `set_value: True`, which is what makes the browser fill the field.
- Before building a custom widget, run `inspect.signature(st.<widget>)` against the
  installed version. Streamlit adds parameters often.
- `AppTest` can type into `chat_input` but cannot submit audio, so the mic path itself
  needs a browser.

Related: [[streamlit-text-area-three-row-minimum]] (the text area this replaced).
