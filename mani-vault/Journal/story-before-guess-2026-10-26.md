# Story before guess: the ChatGPT cadence in every style (2026-10-26)

muhammad's hand test of the friendship chat, after the heart-of-it redesign, still went down a rabbit hole:

- Turn 1 opened with "I want to understand what's behind it." instead of care plus one question.
- Turn 2 guessed ("missing the closeness, or not knowing where you stand? Which feels closer?") before
  knowing what happened. Cause: "each reply moves toward the heart of it", "say your reading as a guess",
  and "when they give almost nothing, offer possibilities" read a short answer as a cue to guess.
- Turns 2 and 3 repeated her facts back ("So the silence began after you disagreed").
- Turn 4 asked about a pattern ("Has this happened before?") she never raised.

ChatGPT's order, which the client wants: care and ask for the story; once the event is known, ask between the
surface and the deeper reading; say back what it means; follow what they did and what came of it; then what
they want and what is stopping them.

Changed: `mani_base.md` how_you_talk and understanding_them describe that order and the two-part reply; the
"never a general statement about how people are" boundary is gone (it banned "A difference of opinion can be
difficult when it affects a friendship"); both client chats moved from `style_directive.md` into `mani_base.md`
so every style learns them; Supportive and Reflective lost the lines that banned a reading of what it means;
the reasoning step and the [ctx] understanding line ask "do I know what happened yet?" first.

Not changed: the layout in `repairs.laid_out` (the client's 10-21 layout puts the question on its own line, and
ChatGPT mostly does too), the heart field and check timing, the framework walk.

## Later the same day: the chat before a framework became its own path

The prompt edits above were still read through the whole framework system prompt, the [ctx] rulebook and a reply
schema of a dozen fields, and muhammad asked for the cadence without the old constraints. So the chat before a
framework now has its own prompt (`conversation.md`), its own small reply shape (`ConversationReply`, text first) and
its own turn (`orchestrator._converse`, pure parts in `chat/converse.py`). The two client chats moved out of
`mani_base.md` into `conversation.md`, restored to her wording except the announced questions, 43 years and "she".
Tests: unit 395 passed (3 pre-existing `abcde.md` wording failures untouched), integration 135 passed against a local
Postgres with `supabase/test_harness.sql`. Not yet run against the real model: neither the cloud workspace nor the
device shell could reach OpenRouter.
