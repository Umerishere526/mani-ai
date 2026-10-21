2026-10-22

# The body check-in is the client's script, and code owns its order

The client's document "SOMATIC SECTION OF MANI" (2026-10-16) replaced the 2026-10-02 flow (four places, per-style practices,
Chat More, three follow-up questions, an automatic exercise pick). Built as five code-owned phases after every framework
(`mani/chat/body.py`, `content/prompts/somatic.md`): the model only reads a typed answer into one closed `body` value and writes
words where the document gives none. Related: [[failure-classes-from-later-branches-2026-10-21]] (class 4, gates on the model,
and class 6, what must always be there is data or a field, not a prompt line).

- The exercises and fixed lines were built from the .docx itself (read with `zipfile`, one paragraph per line) and
  `tests/unit/test_body.py` compares every one with the document, so a retype cannot drift. Join runs inside a paragraph
  with no space, or the text breaks mid-word.
- A YAML flow mapping `{id: x, label: Yes, It Helped}` splits at the comma. Quote any label with a comma.
- `tries` on a stage entry only existed to gate the old "closing asked once" rule; it went with it.
- Dropping `library_offered_since` and the exercise pick removed a second model call per completed framework. The
  `exercise_select` value stays in the database enum (a value cannot be dropped from an enum), unused.
- A message such as "I can't breathe" is caught by the safety screen before the body route, which is correct: the framework
  pauses. Use a different phrase when testing the pain branch.

## Later the same day: four fixes from a Supportive chat

- The ask-first question (my addition at muhammad's choice) was removed: Step 1 follows the last stage directly, and No
  Tension is the way out, as in the document. A thread stored at the removed phase is not carried over (no compatibility
  code), so a reset of the local database is the way to test.
- "Ask next_stage_ask as written" sent the client's E line ("both sides") with no side in view. A stage with nothing known
  is now a mirror of their situation, the question in the model's words, and options. The client's line is only the fallback.
- A said back one example, so the feeling had to be said twice. A's `reach` now says back what happened with the feeling
  they confirmed, and `CONFIRM_ASK` lets a stage's reach name another part.
- Keep Chatting asked "what would you like to talk about now?" because the retiring turn showed the case as the pre-offer
  line. It now gets `their_case` and `landed_on` and the same mirror, question, possibilities shape.
