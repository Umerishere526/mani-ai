# Directive, Supportive, Reflective: the styles document

- **From:** the client
- **To:** muhammad
- **Received:** 2026-10-12 (added to the repo that morning)
- **Document:** [directive, reflective, supportive .docx](../docs/directive%2C%20reflective%2C%20supportive%20.docx), kept as sent
- **Requirements drawn from it:** [R8, R9](../requirements.md#requirements)

## What it is

A Word document, not a message, so it is kept as a file rather than transcribed here. It restates
the client's three conversational styles and the cadence, with four scenarios worked through in every
style: panic ("I feel like I might have a panic attack"), overthinking ("My best friend sent me a text
and I feel like she hates me"), compulsive scrolling ("I cannot stop scrolling, but I need to") and
stress ("I'm trying to balance work, family, and everything else, and I have a deadline coming up").

Its opening rule: the three styles are not three personalities. MANI always remains MANI; what changes
is what each reply is primarily trying to do. Directive leads. Supportive accompanies. Reflective
mirrors and explores.

## What changed from the earlier PDF

Compared with the transcription of the PDF in
[conversational-styles.md](../../../backend/docs/specs/conversational-styles.md):

- The first style is named **Directive**, not Direct.
- Directive carries the heading "Action-oriented, actively leading the conversation forward".
- It ends with a "Tell me more" example for ABCDE: the five steps, then "Would you like to try the
  framework now or keep chatting."
- Each scenario adds its own lines to the within-framework list. Scrolling adds, for Directive,
  "helps the user identify what happens before, during, and after the behavior" and "does not tell
  the user why they scroll or assign a motive to the behavior"; for Supportive and Reflective, "does
  not assume why the user is scrolling or what the behavior means".

The PDF itself is not in the repo, so differences beyond its transcription cannot be checked.

## What it showed about our build

We never sent the client's behavior lists to the model. In their place we wrote our own recipe for
each style in five places, and the rules shared by every style contradicted the client's examples,
for instance banning "what made you think that", banning a question about what feels most pressing,
and telling Reflective never to say their words back. Scope feature 14 rebuilds the styles from this document.
