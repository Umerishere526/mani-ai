---
type: journal
date: 2026-10-13
tags: [journal, prompts, offers, client, lessons]
---

# The client's sample voice, and a confirmed check as the offer gate (2026-10-13)

Three client inputs on one day:
- the way of communication document, a ChatGPT conversation;
- the flow agreed in a meeting, which has no transcript;
- the Framework Selection Cheat Sheet.

Scope features 20 and 21, and requirements R13 to R15.

## What we learned

- The client's sample breaks rules we wrote from their own earlier feedback: no summarising, no menu
  of choices, no narrating, never interpreting. A newer client document wins. Rewriting those rules
  was right; patching around them was not. The rule we kept is "nothing they did not tell you". The
  sample's summary invents facts the person never gave, so we keep the rule, and Lolly must be told why.
- By her own cheat sheet, her sample conversation is Structured Problem Solving, not ABCDE.
  muhammad's call: offer ABCDE after every confirmed check while it is the only active set, and
  keep the selection framework agnostic.
- The offer gate had three fixes in a row (features 12, 15, 19), all tuning a message count that
  stood in for "understood enough". The client's flow gives the real signal: the person confirms
  Mani's understanding. The architecture reviewer agreed. That is a design change, not a fourth patch.
- muhammad does not want the check's wording fixed in code. The check is marked by a typed reply
  field, so code never reads the text.

## The cross check paid for itself

The first draft of spec 0006 stored a state machine for the check (open, confirmed, declined). A cross
check on another model found three ways it could leave a chat stuck with no way to an offer. A
confirmed check whose offer was dropped waited forever. A waiting offer never rendered after a
declined row. And the old "they just finished it" rule refused ABCDE for good once it was done.
Storing only *when* the last check was made, and reading "open" as "the last reply was the check",
removed every state that could stick. Prefer state that expires by construction over state that
must be cleared.

## A note reused as speech needs a speech contract

muhammad's live Directive run (thread 5bbf2b5f) reached ABCDE and then said "From what you've shared,
their boss criticized their client communication after a client cancelled the project; he also said…".
Every record the model writes (`stages_known.*.said`, `understanding`) was a third person note about
"the user", and `walk.py` pastes `said` into the client's A line, which speaks to them. No field said it
would be spoken. Any stored model text that code later shows the person needs its spoken form in the
field description (who it addresses, how long), or it will read like a case note. The descriptions now
say "said to them as you, a dozen words at most", and `scenario_check.py` flags "talks about them".

The same run showed feature 20's first pass was too timid. Editing the old rule list left Mani asking
bare one line questions. The rewrite starts from the client's sample and keeps it in the prompt as
`sounds_like`. The style files' terse example conversations were removed, because the model copies
examples over rules.

## Prose steps are skipped; code owned steps are not

muhammad's third live run (thread 9974cd41): Mani restated, asked two questions in one, and checked at the
person's second message, having asked about neither the core issue nor control. The stored record showed
`core_issue` = "you feel like you're not enough", which was the opening feeling again. Features 20 and 21 had put
the three steps only in prompt prose and gated only the check. Now `understanding.merge` takes each step
only once the one before it was stored on an earlier turn, `[ctx]` names the next step, and a check is stored
only when the person's own words give control. Live, 13 conversations in three styles, every check came after a
control question.

What prose still could not do, measured live:
- Accepting "not enough" as a core issue took one more line in the core issue meaning ("a feeling is not yet
  the core issue"). That held.
- Opening the check with the problem did not hold after two tries. The check opens with their control answer,
  because the voice rule says to begin by taking in their last message. That is the patch limit, so it went
  back to muhammad, who chose code ordering with model wording. The check's parts are sentences the model
  writes, and `repairs.check_text` sends them in order. It held on the first live run. When an order matters
  and the prompt loses it twice, give the order to code and keep the words with the model.

Unit tests prove plumbing, not behavior. Run the scenario live (with muhammad's yes) before calling a
conversation change done.

## The sample is the spec; rules that forbid imitating it fail

The fourth live run still read like a case note: "Being criticized by your boss can make it hard to separate one
piece of feedback from what you think it says about your ability." muhammad asked for a different angle. A
second model (Fable) traced the sentence to my own prompt:
- "never repeat their words back" and "respond to what it costs them" forced an abstract paraphrase;
- "never reuse its words", "vary your words" and `recent_openers` banned the sample's plain connectors;
- a "wise friend… see their situation clearly" persona invited aphorisms;
- the understanding, `heading_toward` (ABCDE: event versus belief) and the shape, all written before the text,
  planned the reply as a case note.

Fix: the sample's five replies are in the prompt as the example to copy, the banning rules are deleted, and the
text comes right after the reasoning. The voice then matched the sample's plain, option-giving questions.
I described the sample in rules and forbade imitating it. I should have handed the sample over and got out
of its way.

Two lessons came out of the same run:
- **Moving `offer` after `text` was not why the yes brought no offer.** Capturing the raw reply showed the
  model declining: "they have not named a troubling belief, so ABCDE is not yet a fit". The prompt said
  "offer the set closest", which left room for none. Now a clear yes always brings the offer. Capture the
  raw reply before guessing a second time.
- **A colon followed by a space inside a YAML bullet turns the rule into a mapping.**
  `test_every_rule_in_a_prompt_file_is_a_sentence_not_a_yaml_mapping` caught one after a live run had already
  used it. Run the tests before the live run, not after.

## Stage confirmations in Mani's words

muhammad's team lead found the fixed "Is that right?" / "Do we have this right?" endings canned. Mani now writes
each stage's confirmation after the client's letter line, and the fixed parts are a logged fallback. Live, the
first version mixed the next stage's content into the confirmation (B also told C) and reused its own closing
question ("Is that the X you want to look at?"). One sentence in `walk.CONFIRM_ASK` fixed both: only what they
said for this stage, asked differently from the stage before.

## The seed must use the walk's own tests

muhammad's Supportive run (thread 7e3062ff). B was seeded from the opening line ("whether you're good at your
job") among three beliefs the person voiced, and C from that rejected belief. Fable 5.1 reviewed my plan and
found three things:
- the seed saw only `listen_for`, never `ready_when`, so the client's "If several appear, ask which one" was
  invisible to it;
- `comes_down_to` was dropped from the record;
- the live path was `not_yet` then `answered`, not `corrected`, so a trigger on `corrected` would have missed it.

Fixed by sending `ready_when` in the seed lines, keeping `comes_down_to`, and clearing on state (new words for a
stage being confirmed). Live, B asked "Which of those thoughts affected you most?". Fable also caught that my
verification would have accepted "this is work abuse" as B, and disputing that is what ABCDE's contraindication
forbids.

The same runs showed the core issue gate stalling. Mani's reasoning said "They have not yet named what lies
underneath the issue", so it waited for the person to say it. The wording had now failed both ways (first the
opening feeling was stored as the core issue, then nothing was stored at all). muhammad chose that Mani offers
the core issue once their answers show it. Live: the overtime chat reached the check in 4 of 9 runs (from 1 of
9), the boss chat in 5 of 6. Pacing is still slow when the person never answers the step question directly.

## Gotchas

- `test_questions_follow_their_answers_from_one_rule_with_no_checklist_or_ban_beside_it` pins one
  `rules` line word for word. Keep it when rewriting `mani_base.md`.
- `reply_shapes` names are mirrored in `schema.SHAPES`. Don't rename them in the prompt alone.
- In `tests/integration/test_turn.py`, `past_the_opening` now ends on Mani's check, so the next message
  answers it. `_in_style` adds two messages, so call it *before* `past_the_opening`, or the check is no
  longer the last reply.
- `scenario_check.py` answers each check with the conversation's `check_answer` ("Yes, that's right." by
  default); scenario lines alone never say yes to anything.

See [[offer-window-owned-by-code-2026-10-12]], [[running-understanding-and-one-question-rule-2026-10-13]],
[[general-judgment-over-case-patches-2026-10-12]].
