> **Historical** (marked 2026-11-25): a design or plan as written at the time; parts no longer match the code (the return check after a pause, for one, is gone). What the backend does today is in `backend/PORT-STATUS.md`.

# Supportive and Reflective build up to the highlight

Date: 2026-11-18. Approved approach: A (prompt only, removing the lines that cause it), muhammad 2026-11-18.

## Intent

The client likes how much Supportive and Reflective say and how the conversation feels. Her complaint is about
timing. Mani gives the highlight, the key insight that ties what they said to what is really at stake, too early.
The person should get to build up to it. Replies should also get longer as the conversation grows.

muhammad reversed his 2026-11-17 overrule of R73 for Supportive and Reflective. R73 came from the client's
2026-11-05 meeting and says a first message is the first layer: no insight from it, and Mani keeps going until they
have said what they wanted. Directive keeps its own rules.

## What causes it today (the evidence)

The chats are from the local database, 2026-11-18:

- Reflective coworker noise, first reply (139 words): it already gives the whole outside connection ("hard to call
  it a problem out loud… you might come across as the person who complains"). The person had written one line.
- Supportive coworker noise, first reply (148 words): "if you're already carrying the feeling that you have to keep
  proving your place". The person never said anything like it.
- Supportive partner lying, replies 85 → 113 → 124 → 101 → 114 words: the length stays flat. By its second reply
  Mani was telling them they felt made a fool of.

In `backend/content/prompts/mani.md`:

1. The flatmate first-reply example makes three readings stated as fact ("isn't really about the dishes…", "That
   last part might sting the most…", "Maybe you just want…"). The line above it says to ask, and the model copies
   the example.
2. "Every reply gives them something they did not say themselves" and "most replies do two or three of these"
   require an insight from the first reply on.
3. Length is one band: "usually 120 to 220 words". First replies already land in the middle of it.

The client's own example replies (the eval references in `backend/evals/cases.json`) show the shape she wants:

- One-line openers get 64 to 80 words (`sad-1`, `office-1`).
- Replies later in a chat get 190 to 207 words.
- Where her first reply reads anything (`colleague-1`, `cover-1`), the first message was long and detailed, and the
  reading only links things they said ("that last part… why your perspective doesn't get the same
  consideration").

## Goals

- In Supportive and Reflective, how deep a reading goes and how long a reply is both follow how much the person has
  told Mani.
- **Early replies** reflect what they said in their own words, notice one small thing drawn only from what they
  said, and ask one question.
- **The highlight waits.** It is the reading that reaches past their words to what is at stake for them: a fear, a
  need, a belief about themselves, or the outside connection. It comes only once they have said what happened, what
  it does to them, and something of what it means to them. Mani judges that from their words, never from a count of
  messages, as R73 asked.
- **Length grows:**
  - About 60 to 110 words while Mani is still learning what happened.
  - Up to about 150 words when the first message is long and detailed.
  - Longer as they tell more, and about 150 to 250 words once they have laid it out.

## Non-goals

- Directive: no change. It keeps three or four sentences and its own rule for the first reply.
- No change to when the set is offered, or to anything inside the set.
- No code that counts messages or decides when the highlight is allowed (approaches B and C).

## Anti-goals

- Early replies that read as generic. That was muhammad's reason for the 2026-11-17 overrule, from the side-by-side
  comparison with ChatGPT. An early reply still has to be specific to what they said, never a stock "tell me more".
- Holding back once they have laid it out. After that, the highlight comes, and it stays a possibility they can
  correct.

## Approaches

- **A. Prompt only, removing the lines that cause it (chosen).** The lines that push an early insight and a flat
  length are replaced, and no rule is stacked on top of them. This is the lesson from the Directive length fix, where
  a new rule failed while older lines still contradicted it.
- **B. A plus a fact from code** saying which of the person's messages this is. Held back, and used only if A's
  eval shows replies not growing.
- **C. Code decides when the highlight is allowed**, from a field the model reports each turn. Rejected. It is the
  "enough is a field" pattern the journal records as needing a push that kept coming back, and it goes against the
  decision that one model call judges the conversation.

## What changes

### `backend/content/prompts/mani.md`

- **"How you listen", the bullet "Every reply gives them something they did not say themselves…".** Replace it with
  a progression for Supportive and Reflective:
  - Early replies give a small, specific observation drawn only from their words.
  - Readings deepen as they tell more.
  - The highlight comes only once they have said what happened, what it does to them, and something of what it
    means to them.
  - Saying their words back is still never enough on its own.
- **"What a good reply gives", the lead-in.** "Most replies do two or three of these" becomes "early on, one, drawn
  from their own words; more as they tell you more". Directive keeps "one or two, never more".
- **"Something to highlight".** Add when it comes: only after the build-up above, one per reply at most.
- **"How a reply looks", the word count line.** Replace it with the growing band from Goals.
- **The first-reply paragraph and its flatmate example.**
  - Rewrite the example as a reply to a short opener, in the shape of `office-1` and `sad-1`: it reflects, notices
    one small thing and asks one question. It is written fresh, never copied from an eval reference, so the eval
    stays a fair test.
  - Keep one example of a later reply that does deliver the highlight, so the model sees where the build-up ends.
    The sister babysitting example already does this.
  - Keep the Directive first-reply text as it is.
- Lines that still assume an early reading go too. "Your reading, held lightly" stays a possibility they can correct.

### `backend/evals/`

- `run_eval.py`: add `max_words` and `min_words` to `rule_checks`, beside `max_sentences`, with a unit test in
  `tests/unit/test_eval_checks.py`.
- `cases.json`, new rule cases (5 samples each):
  - `rule-sr-first-reply-builds` (Supportive) and `rule-sr-first-reply-builds-reflective` (Reflective). The opener
    is "my co workers keep on blabbering and i can't focus". `max_words` 120, plus a judge: the reply reflects what
    they said, notices at most one small thing drawn only from their words, and asks one question. It does not say
    what is at stake beyond their words, such as a fear of being disliked, proving their place, or being judged.
  - `rule-sr-highlight-when-laid-out` (Supportive). A history where they have said what happened, what it does to
    them and what it means to them. `min_words` 150, plus a judge: the reply gives one clear highlight about what is
    at stake for them, held as a possibility.
- The quality gate runs as before: Supportive and Reflective within 0.15 of the baseline. The references already
  have this shape, so the gate should hold or rise.

### Records, in the same change

- `docs/client/messages/2026-11-18-supportive-reflective-build-up.md`: the client's words as relayed by muhammad.
- `docs/client/requirements.md`:
  - A new row for this feedback.
  - The R73 row: overrule reversed for Supportive and Reflective by muhammad, 2026-11-18, and in force for Directive.
  - Its Conflicts row updated to match.
- `backend/PORT-STATUS.md`, Decisions in force: a new entry, "In Supportive and Reflective a reply builds with what
  they have told: early replies reflect and notice one thing, the highlight waits until they have said what
  happened, what it does to them and what it means, and replies grow longer", with its Because line and pointers to
  the eval cases.
- `mani-vault/Journal/`: a note on the cause (the example and two rules that forced an early insight), with a
  `failed:` line for the 2026-11-17 first-reply insight. `> Superseded` lines go on the notes that argued for the
  overrule.
- Reseed the prompts (`scripts/seed.py`).

## Left to the builder

- The exact wording of the replaced lines and the new example, kept in the prompt's voice, with no dashes and no
  semicolons.
- The history for the "laid out" case. Its own invented situation is better than the client's partner chat.

## Open, not blocking

- The question from the coworker-noise review, on Directive and whether practical help belongs in the chat, is
  still unanswered. It is a separate change.
