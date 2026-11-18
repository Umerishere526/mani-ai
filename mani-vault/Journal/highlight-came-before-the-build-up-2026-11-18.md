---
type: journal
date: 2026-11-18
tags: [journal, prompt, supportive, reflective, client-feedback]
summary: "Supportive and Reflective gave the highlight in the first reply because the prompt's example and two rules asked for an insight every reply."
failed:
  - "Tried an insight in the first reply (the R73 overrule, 2026-11-17); failed because the client found the highlight came before the person built up to it"
---

# The highlight came before the build-up (2026-11-18)

The client likes how much Supportive and Reflective say. Her complaint is that the highlight comes too early:
the reading that ties what they said to what is really at stake. Replies should also grow as the chat grows. Her
words are in `docs/client/messages/2026-11-18-supportive-reflective-build-up.md`.

## Cause

Three things in `backend/content/prompts/mani.md` asked for it:

- **The flatmate first-reply example.** It made three readings stated as fact ("isn't really about the dishes…",
  "That last part might sting the most…", "Maybe you just want…"). The line above it said to ask, and the model
  copied the example, not the line.
- **"Every reply gives them something they did not say themselves"** and **"most replies do two or three of
  these".** Both required an insight from the first reply on.
- **One length band, "usually 120 to 220 words".** First replies landed in the middle of it, so nothing grew.

The early reading was allowed on purpose. muhammad overruled R73 on 2026-11-17 because, next to ChatGPT, the reply
that held back read as generic. That reason still matters: an early reply has to stay specific to what they said.
What it may not do is reach past their words.

## Evidence

- Reflective coworker noise, first reply (139 words): the whole outside connection after a one-line message.
- Supportive coworker noise, first reply (148 words): "proving your place", which the person never said.
- Supportive partner lying: replies of 85, 113, 124, 101 and 114 words, flat.
- The client's own example replies (the eval references in `backend/evals/cases.json`) already have the shape she
  wants. One-line openers get 64 to 80 words (`sad-1`, `office-1`), and later replies get 190 to 207. Her only
  first-reply readings answer long, detailed first messages, and they only link things the person said.

## Fix

The lines that caused it were replaced, with nothing new stacked on them. This is the same lesson as
[[directive-replies-ran-long-and-definitive-2026-11-18]]: a rule fails while older lines still contradict it.

- Early replies notice one small thing drawn from their own words.
- What is at stake waits until they have said what happened, what it does to them and what it means to them, judged
  from their words, never from a count.
- Length grows from about 60 to 110 words up to 150 to 250.

The eval cases are `rule-sr-first-reply-builds`, `rule-sr-first-reply-builds-reflective` and
`rule-sr-highlight-when-laid-out`.

## Results (same session)

- The gate went from 3.45 to 3.64.
- Supportive first replies passed 10 of 10 over two runs. Reflective passed 7 of 10, and the misses say "there's
  something underneath it". The Reflective style line ("notice patterns and tensions") may be what pulls it deeper.
- A guilt example in the first-reply paragraph ("I wonder if there's something deeper behind that guilt") still
  modelled a deep reading. Removing it took first replies from 7 of 10 to 10 of 10.
- The long band first waited for "laid out", and later replies stayed short (office-2 at 97 words against the
  client's 193). It now starts once they have told what happened.
- In the highlight case the highlight arrives every time. Two problems that predate this change still fail it:
  - Readings are stated as fact ("That's the part that stings").
  - In 4 of 5 samples the model offers the set in the same reply where it first says the core back. The prompt
    asks for an earlier reply, and this is the same mistake as the Directive coworker-noise chat.
- Two calibration lessons for eval cases:
  - A judge stricter than the client's own references fails good replies.
  - A case history written shorter than the prompt's own band anchors the model short.
