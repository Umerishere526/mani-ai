# 0015. Rationale: the offer and Tell Me More per framework and style

## Context

> ⚠️ Premise note: the client's ABCDE offer lines are examples for one user, not lines for everyone. They answer "I'm just overwhelmed, anxious, and don't feel like I'm handling things well". The Direct and Supportive lines say "the thoughts behind your anxiety", and Supportive opens with "Feeling overwhelmed can make you question how well you're handling things." Sent as fixed text, they tell a person who never mentioned anxiety that they are anxious, which `mani_base.md` forbids ("Nothing they did not tell you"). muhammad chose on 2026-10-08 to generalise those words and keep the rest. Reflective's line, and all three Tell Me More texts, are already general and stay word for word. Scope feature 17's done line ("the client's text for the chosen style") is reworded to match.

> ⚠️ Premise note: the client's Tell Me More is written as a bulleted list. The chat tester renders replies as markdown, and single line breaks there join lines into one paragraph. So the steps are stored as `- ` lines after a blank line. Web and mobile are not wired to the API yet, and whether they render markdown is their decision when they are.

Spec 0013 made the code write every offer: a shared lead, `Framework: <name>` and the client's description from the intro document, with three buttons. A tap on Tell Me More is answered with no model call, from the same seeded rows, and for now it repeats the name and description. muhammad kept the shared lead over a repeat it makes on Structured Problem Solving, and scope feature 17 was left for the client's Tell Me More wording.

That wording has arrived for ABCDE only (`docs/client-share-docs/ABCDE Framework.docx`, transcribed in `backend/docs/specs/framework-abcde.md` §0). It gives an offer line for each of the three conversation styles, each naming ABCDE inline and ending "Would you like to try it?", and a Tell Me More for each style that lists all five steps. The client says Try It after Tell Me More must not restart the conversation or repeat the steps. The other five frameworks have no such document yet.

Three facts about the code shape what is possible. The style is always known on a turn: `context.resolve_style` takes the thread's choice, then the profile's, then the tuning default, and names it in `[ctx]`. Every line Mani sends without the model lives in the `replies` row, checked strictly by `Replies` at seed, admin write and cache load, and the style keyed lines (`style_labels`, `openers`) already follow the same shape. And muhammad's rule from 2026-10-08 holds: change Mani by cutting prompt rules, never by adding them.

## Options considered

### Option 1: Literal per style text in the `replies` row, keyed by framework id (chosen)

`offer.by_framework.<id>.<style>` holds `text` and `more_text`. The code sends the framework's text for the style when it is there, and the shared frame otherwise.

**Pros**:
- Exact text, as spec 0013 decided, now in the person's style.
- No migration. One row, already checked strictly, and the same per style shape as `openers`.
- The next framework's document is a content edit and a reseed.

**Cons**:
- Framework text lives in two places: the description in the framework file, the per style text in `replies.md`.
- `replies.md` grows by about 18 lines per framework.
- An id rename must touch both files; the seed check makes that loud rather than silent.

### Option 2: The same text in each framework file

Front matter beside `name` and `summary` in `abcde.md`, seeded into a new `jsonb` column on `admin.frameworks`.

**Pros**:
- Everything about ABCDE in one file.
- No id to keep in step between two files.

**Cons**:
- A migration, plus changes to the `Framework` model, the query and the seed, for a feature that needs none of them.
- The person facing per style lines split between `replies` and the framework rows, so "the lines Mani sends without the model" no longer has one home.

### Option 3: The model's short line, then the fixed sentence

The model's one short line on the offer turn, thrown away today, is kept as an opening in Supportive and Reflective, and the code adds the fixed ABCDE sentence and question.

**Pros**:
- Closest to what the client's examples do: acknowledge the person, then offer.

**Cons**:
- The opening is no longer exact, and it could make an offer of its own before the fixed one.
- A code addition to model text, two voices in one message.

### Option 4: The model writes the offer in style

Back to the model's own offer, with the client's three lines as the pattern.

**Pros**:
- Fits each person and each conversation.

**Cons**:
- Reverses spec 0013: no wording is guaranteed, and Tell Me More would cost a model call and vary.
- Adds a rule to the prompt.

## Rationale

The force that decides it is exactness, already chosen in spec 0013 and kept by muhammad here: the offer and Tell Me More show the same seeded words every time and change only by a reseed. That rules out Options 3 and 4, which hand words back to the model. Between Options 1 and 2, both exact, Option 1 needs no migration and keeps every line Mani sends without the model in one row. That row already has the strict checks, the admin write path and the per style shape. Option 2's one real advantage, no id to keep in step, is covered by a seed check that refuses a `by_framework` key with no framework file.

The text is literal, with no `{name}` or `{description}`, because the client writes "a framework called ABCDE" while the row's name is "ABCDE Framework". A field would add nothing but a wrong name. A framework must have all three styles or none, so a person never gets one framework's offer in a shape that depends on their style. The other five keep the shared frame, rather than drafts of ours, so nothing is invented that the client would then replace.

No prompt line changes for "Try It after Tell Me More neither restarts nor repeats". The accept path after Tell Me More is already the ordinary accept (spec 0013). The model sees the Tell Me More reply in its history, and the base prompt already says to open with a short line and the first stage question, and never to explain the method. Adding a rule for it would go against muhammad's rule on prompt changes. So the code path is proven by scripted tests, and the model's behaviour by one real run in Reflective, the style most likely to explain. The run needs muhammad's yes, since it spends the client's credits. The eval gains a `@more` token that waits for the offer the way `@accept` does, so one paid run is enough even if the offer comes a turn later than expected.
