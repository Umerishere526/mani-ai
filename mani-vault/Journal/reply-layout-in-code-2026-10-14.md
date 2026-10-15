---
type: journal
date: 2026-10-14
tags: [journal, voice, layout, rendering, lessons]
---

# Mani's reply layout is decided in code (2026-10-14)

muhammad saw a reply arrive as one block: "Your boss criticized your work today, and I still want to understand
what that tends to mean for you. Does it leave you questioning ...?" The client's way of communication document
puts the closing question on a line of its own.

- The prompt already asked for "the question last on its own line". The model followed it in some replies and
  not others, at the same effort. The prompt's copy of the client example also ran the client's lines together,
  so the example taught the merged layout. Both are fixed: the example has the client's line breaks back, and
  `repairs.laid_out` makes the layout in code.
- The client's document breaks between the moves of a reply (say back, what I want to understand, the
  question), not after every sentence. A short reply like "I'm listening. What's frustrating you?" stays one
  line, hence the 8-word minimum before the question.
- How a single `\n` displays differs by client. chat-tester's `st.write` is markdown and shows it as a space.
  Mobile's react-native-marked passes the raw text into RN `<Text>`, which shows it as a line break. The
  backend therefore writes `\n\n`, which every client shows as a break.
- Stage replies inside a framework stay one paragraph ("A is for Activating Event. ... Is that right?"), as the
  ABCDE document writes them. The gate also leaves out a framework that starts on the turn (a declined set asked
  for again), where the walk uses the model's own text as the stage body.
- A sentence splitter needs its own rules: no break after Dr., Mr. or a single-letter initial (as in "a.m."),
  only before a capital, and allowing a closing quote after the stop.

Related: [[styles-from-client-document-2026-10-12]], [[running-understanding-and-one-question-rule-2026-10-13]]
