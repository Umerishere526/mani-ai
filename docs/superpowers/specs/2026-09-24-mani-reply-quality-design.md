# Mani reply quality — design

Date: 2026-09-24. Owner: muhammad. Status: draft for review.

## Why

The client says Mani's replies are worse than the MVP they had: robotic, loopy, cold overall,
and Direct is not direct. muhammad adds that Mani interrogates, pushes frameworks too soon, reads
as scripted and flat, produces awkward sentences, and loses track of the actual issue.

## The bar

The MVP's final prompts: `~/Desktop/Mani Repos/mani-app /apps/backend/prompts/` at commit
`e7776ed` (2026-01-30). That commit deleted the three style files, so the MVP ran one
presence-first voice with two named techniques.

What differs from the prompts we ship now (hypotheses, to be confirmed by measurement):

1. **Pacing.** MVP offered only once presence and curiosity were used up. Ours offers within 2–4
   exchanges, and Direct on the first or second reply.
2. **Questions.** Ours ends every reply with a question until an offer. MVP gave agency most turns
   and allowed presence without a question.
3. **Presence.** MVP allowed "I'm here" at key moments. Ours forbids it outside Supportive, and
   `repairs.py` deletes it.
4. **Rules instead of examples.** MVP's `mani_base` is a goal ("Comfort"), five moves, and two
   whole annotated conversations. Ours leads with what Mani is not, then pages of prohibitions.
5. **Code edits reply text** (presence stripping, offer-sentence removal, an appended permission
   question), which can leave stilted sentences.
6. **Examples become templates.** "How are you holding up with it all?", the generic line the
   client objects to, appears four times in the uncommitted feelings-first diff.

Size is not the difference: both stacks are about 34–38K characters per turn.

## The fixed frame

The client's specs (`backend/docs/specs/`) stay: three styles (Direct, Supportive, Reflective),
six frameworks, never saying a framework's name or the word "framework", the offer described by
the client's own description of each framework, Try it / Keep chatting, the body check-in,
Chat More / Go to Library, and the three forward-moving questions. Where the MVP and our current
prompts differ inside that frame, it is decided item by item at the file where it arises.

## The behaviour we are building

### All three styles

- Warm, like someone very experienced at this work. Never "therapy", "therapist", "session",
  a diagnosis, or clinical vocabulary.
- After a short introduction the conversation moves toward the person feeling better. Mani knows
  where the conversation is heading and how it will conclude.
- Mani holds on to the core issue throughout and does not lose it.
- A question is never repeated unless what the person said calls for it. No loops.
- Every question makes sense where it is asked. No announcing plans ("we're going to do this and
  that"). No generic check-ins ("how are you holding up with it all").
- Mani may name a feeling it senses **as a question to check** ("It sounds like you might feel
  shut out. Is that right?"), never as a statement of fact. This follows the spec's "asks or
  checks rather than presenting that understanding as fact".

### Direct

Genuinely direct, warm and loving, aiming at closure. It stays with their pain and their
perspective, questions that perspective, and once it has enough sense of it, moves to the
framework rather than continuing to question.

### Supportive (the most important)

Emotional support first. Once the feeling and situation are identified, how they got there matters
less than what would make it better. Questions sound experienced, never scripted.

### Reflective

Warm toward their feelings. Asks about the feeling, not the situation that caused it. Names a
feeling it senses and checks it; on a yes, goes deeper: how, why, what would change it.

### Buttons

Only in three places: the greeting's style choice, the framework offer (Try it / Keep chatting),
and the framework's end (the practice replies and Chat More / Go to Library). None during ordinary
chat. Enforced in the backend, so the chat-tester and mobile both get it.

### The flow

1. Greeting, style choice, the style's opener.
2. About four rounds of conversation. Not a fixed count: the offer comes once Mani can identify the
   issue and the framework that fits.
3. Offer the framework with its description, fitted to what they said, never its name.
4. The framework's stages.
5. Closing question.
6. Body check-in, in wording muhammad supplies verbatim (the client spec's per-style lines until
   then).
7. Grounding practice (below).
8. What next: Chat More / Go to Library.
9. Continued conversation. If they stay on the same issue, the three forward-moving questions, one
   per reply, in order:
   - What feels most important about this now?
   - What do you think you need to do differently from here?
   - How could you take one small step toward that?

### Somatic check-in and grounding practice

Restored from the MVP's Ground step, placed before the choice so the person leaves feeling that
something eased.

1. Body question, asked once, never repeated. If they already described their body while answering
   the closing question, it is not asked; Mani reflects what they said.
2. If they name a place or sensation, Mani reflects it in their words and gives one short practice
   for that place, as numbered steps (MVP wording):

   | Where | Practice |
   |---|---|
   | Chest | Hand on chest, breathe in through the nose for 4, out through the mouth for 6, three times |
   | Head | Press your feet into the floor, name 3 things you can see and 2 you can hear, one slow breath out |
   | Stomach | Hand on your belly, a slow breath in so the belly rises, a longer breath out, three times |
   | Somewhere else | Gentle attention to that place, a slow breath, notice what shifts |

   Buttons: I tried it / Still tense / Feeling better.
3. After it, Mani reflects the change in their words, set against where they started only if they
   described it, then asks what they would like to do next: Chat More / Go to Library.
4. Still tense: one line that it comes in waves, the same practice offered once more at most, then
   the choice. Never a loop.
5. Declined or feeling fine: one gentle line, then the choice.
6. **Safety:** no practice when they report pain, trouble breathing, dizziness or anything that
   sounds physical. The safety screen already flags "chest pain" and "cannot breathe" as concern.

In the content this is a new last stage, `grounding`, after `somatic` in all six frameworks.
Completion is positional (`Registry.is_final`), so the hand-off moves with it; no migration.

## Method

### Measurement, before any prompt changes

- Copy the MVP prompts from `e7776ed` into `backend/docs/mvp-prompts/` as provenance.
- Add `scripts/compare_replies.py` beside `scripts/eval_replies.py`, reusing its scenarios and
  runner: each scripted conversation through the
  MVP stack (composed as the MVP did, raw, no repairs) and through ours in each style, same model
  and temperature. Pre-framework turns only; the MVP's two techniques do not map onto our six.
- Output a readable transcript file per run. No automated scoring: muhammad is the only judge of
  reply quality.
- Three runs per comparison, before and after every file.
- Baseline first: "now" is the working tree including the uncommitted feelings-first diff.

### The walk, line by line

For each file, in this order:

1. `content/prompts/mani_base.md`, rebuilt on the MVP's structure: goal and identity, the moves,
   one whole annotated conversation per style, rules only where an example cannot carry them.
2. `content/prompts/response_format.md`
3. The `[ctx]` contract in `mani/chat/context.py`
4. The six `content/frameworks/*.md`, one at a time, including `grounding`
5. `mani/chat/repairs.py` rules that rewrite text
6. `title_generation.md`, `summarization.md`, `memory_fold.md`

Per section of each file: the current text, what is wrong with it against the client's feedback,
the replacement. muhammad decides each before it is written. Then the file is measured before and
after, muhammad reads the transcripts, and it is committed.

### Decisions taken at the file where they arise

- Offer timing, and whether it differs by style (the spec says "same cadence")
- Whether every pre-offer reply must end with a question
- Presence ("I'm here") by style, and the repair that strips it
- Mirroring voices, including the MVP's "I hear that…"
- Which text-editing repairs survive, and the feeling-word list now that checking a feeling is allowed
- Whether the three forward-moving questions also apply in a new chat on the same issue
- The verbatim somatic wording

### Code that may change

Each change is brought to muhammad before it is made: the `[ctx]` fields, text-editing repairs,
the `Reply.prompts` description (buttons only at offers and endings), the validators' labelling
rule, and `phases` gaining `grounding`. One model call per turn, the safety screen, RLS and the
data model do not change.

## Out of scope

Crisis resources and the approved safety protocol (still muhammad's to supply), the safety phrase
lists, mobile and web, hosting.

## Done when

- muhammad, reading the side-by-side, judges the new replies better than the MVP's on every
  scenario in all three styles, and the framework journeys end in the practice and the choice.
- `pytest` green with the skip count unchanged. These tests check that the code works (turns
  are stored, buttons land where they should), never whether a reply is good.
- `backend/PORT-STATUS.md` describes the new behaviour.
