# 0011 rationale: Mani follows Lolly's review of the meetings chat

The decision record behind [index.md](index.md). `/develop` reads the index; this file is for people.

## Context

Lolly (the client) ran a fresh Direct conversation on hosted on 6 October 2026, the day spec 0010 was built: a person left out of a few important meetings, wondering whether their role is changing and whether they are "making too much of it". Mani offered Thought Reframe, she tapped Tell me more, accepted, went through every step, reached the somatic practice, and answered "This whole chat was horrible this whole experience was bad." Her review takes each reply in turn and says she hates talking to Mani. Later that day muhammad passed on her wider wish: a plain, natural, down to earth therapist that can handle any situation, including open questions, and never crosses the guardrails.

Her objections fall into three groups, traced in the journal note `lolly-meetings-chat-objections-land-on-her-own-lines-2026-10-06`:

1. **Lines from her own earlier documents.** The consent lines ("Okay. I'll guide you through it one step at a time."), the Direct Tell me more text ("focused questions", "without rushing you", "You stay in control of what you want to share"), the unnamed "I have a structured approach" offer, the body check in followed by "Where do you feel that most right now?", and the chest practice's "The chest is often where the body holds tension first. Let's do something brief together." are hers, word for word, from the style document, the Thought Reframe document and the somatic practices.
2. **Lines that are ours.** "Putting those together, what would you say is true about this?" and "What else could be going on?" in the framework files; the **Skip this one** button added that morning (commit `2f617d4`); "ask what they would like to do next" after every practice; and the exercise pick that runs on every ending whatever the person said.
3. **The model's language.** It made her facts stronger ("dropped", "points to", "where you stand", "your role stayed the same"), wrote stiff paraphrases before each question, swapped her words for others ("overthinking" for "making too much of it"), asked her to confirm the thought the offer was built on, presumed the conversation had "settled" something, and mirrored her last message back.

The forces: the client's newest document wins over her older ones and over our rules (spec 0010, ADR-019, and muhammad's standing preference). Spec 0010 deliberately moved judgment to the model and kept code only for what must be exact; that should hold. The somatic step is mandatory in her architecture, and the answer after it is the effectiveness signal she cares about most. Real model runs spend the client's credits and need muhammad's yes. Doing nothing means her next checkpoint finds the same conversation.

## Options considered

### Option 1: Fix in place, code holding only what must be exact

Rewrite the prompts and the framework content to her review, and change code at exactly the points where a model miss would repeat what she saw: the name in the offer and in Tell me more, the Skip button, the body question and its buttons, and the close with no exercise after a negative answer.

**Pros**:
- Keeps spec 0010's split: the model judges, code guarantees structure.
- Each code change is small and sits where similar repairs already live (`repairs.apply`, `_body_route_step`, the retire turn).
- No schema change, no new endpoint, nothing for the frontends to break on.

**Cons**:
- The language problems (stronger facts, stiff paraphrase) are prompt rules only; nothing in code catches them, so the replay is the only check.
- The negative close depends on the model's `felt_after`.

### Option 2: Prompt and content only

Change only `mani_base.md`, `response_format.md`, the framework files and `somatic.md`, and leave the code alone.

**Pros**:
- Smallest change, all reseedable content.

**Cons**:
- The Skip button, the duplicate body question and the exercise after a negative answer are produced by code; a prompt cannot remove them.
- The name in the offer would depend on the model remembering it, and the reason it was missing today is a prompt rule the model followed faithfully.

### Option 3: Fixed templates for every line she rewrote

Code sends her suggested sentences as written: the offer ("We could use a Thought Reframe to look at ..."), Tell me more, the conclusion, and the close.

**Pros**:
- Exactly her words, every time.

**Cons**:
- Her suggestions are fitted to the meetings conversation; as templates they become the same sentence for every situation, which is the scripted, repetitive Mani she is objecting to.
- Puts back the kind of code enforced wording spec 0010 removed.

## Rationale

Option 1, because it treats each objection at the layer that produced it. The model's language is a prompt problem, so the prompt changes; her rejected lines are content, so the content changes; the Skip button, the double body question and the exercise after "this was horrible" are code paths, so the code changes. That keeps the boundary spec 0010 drew, where the model owns tone and judgment and code owns the few things that must be exact, and it is the smallest change that removes every line she pointed at.

The places where code now holds firm are chosen by cost of a miss. An unnamed offer is the same failure she says she has raised many times, so a missing name is repaired, not hoped for. A negative answer followed by a question and a breathing exercise is the worst moment in the transcript, so the closing line is fixed and the exercise call is skipped. Everything else (the stated conclusion, concrete questions, their own words) stays the model's judgment, because a template there would recreate the repetition she dislikes (the reason Option 3 loses).

Several of the changes undo her own approved wording. That is right by the source order (her newest document wins), and muhammad confirmed it ("make it as she is saying"), but it has to be told to her, or a later pass that reads the style document will put the lines back. That is a task for later, not a reason to keep them.

On the wider ask: "therapist" is read as how Mani talks, not what it claims to be. The base prompt already says Mani is not a clinician, and a person in distress being told they are talking to a therapist when they are not is itself a line that should not be crossed. muhammad chose this reading. "Open ended questions" are the person's own questions to Mani; the current prompt pushes those back with a question, which reads as evasive. Answering them plainly, inside the same guardrails (no diagnosis, no medical advice, no softening danger, the safety screen untouched), is what a good therapist does and does not need any code.

A few decisions were made in writing rather than asked:
- The name check inserts "It's called {name}." rather than rewriting the model's sentence, because rewriting it would lose the fit to their situation; the runner up was prefixing the name to the offer sentence, which reads badly when the sentence already starts with "We could".
- "Nothing" gets a small pattern beside the decline pattern rather than being read by the model, because it decides whether the practice happens at all and the decline path it joins is already pattern based.
- `somatic_checkin` keeps its name; renaming touches every framework's phases and the stored rows for no behaviour.
- The closing line drops "I hear you", which Lolly's own style document lists as a formula to avoid; muhammad chose this.
- The base prompt line cap holds at 130 if the removed lines pay for the new ones, and is raised by exactly what is needed otherwise, never by compressing the clinical or safety rules (the same call made on 6 October).

## Evidence: where each objection came from

| Her objection | Source | Changed by |
|---|---|---|
| "brings up real questions about where you stand", "you were dropped", "it points to", "your role stayed the same" | the model, under the say back rule in `mani_base.md` | AC-9 |
| "Did something shift recently", "decide on your next move", "a concrete shift to see happening" | the model | AC-9 |
| "Who would be the best person on the team to ask about it?" too early | the model, Direct "leads toward clarity, action or a next step" | AC-9 |
| "I have a structured approach ..." with no name | style document; our "never its name" rule (spec 0010 AC-4) | AC-1, AC-3 |
| Tell me more: "focused questions", "without rushing you", "You stay in control" | style document, Direct Tell me more text, in `greeting.EXPLANATIONS` | AC-2 |
| "Okay. I'll guide you through it one step at a time." | style document consent lines | AC-4 |
| "Is that the thought you want to look at?" after the offer named it | `thought_reframe.md` `thought` stage and its `ready_when` | AC-5 |
| **Skip this one** after every question | commit `2f617d4`, `repairs.SKIP_LABEL` | AC-6 |
| "What makes that thought matter so much right now?" | the model rewording "Why does that thought matter to you?" | AC-7 |
| "Is there anything you know right now that doesn't point to your role changing?" | the model rewording "Is there anything you know that doesn't match that thought?" | AC-7 |
| "What else could be going on?" | `thought_reframe.md` `alternative` ask (ours) | AC-7 |
| "Putting those together, what would you say is true about this?" | `thought_reframe.md` `reframe` and `abcde.md` `balanced` asks (ours) | AC-8 |
| "what you were filling in" | the model | AC-8 |
| "Take a moment to notice how that settles in your body" | the model's bridge | AC-10 |
| "What do you notice in your body now?" then "Where do you feel that most right now?" | Thought Reframe document section 22 and `somatic.md` | AC-10 |
| "?" from the tester | the duplication above | AC-10, AC-11 |
| "The chest is often where the body holds tension first." "Let's do something brief together." | her approved Direct chest practice | AC-12 |
| "It went badly and felt awful to go through." "What would you like to do next?" | the model, under "Then ask what they would like to do next" in `mani_base.md` | AC-13 |
| Exercise offered: Bee Breathing | `orchestrator._offer_exercise`, run on every ending | AC-14 |

## Cross check

An independent read only pass on a second model (Sonnet) found 17 gaps and 6 soundness points on 6 October. muhammad applied the recommended fixes: the summary in the Framework Index for the default routing path, the exact name match, questions removed from Tell me more in code, a typed question under an offer answered first, the bridge rule moved to where the model sees it, a backstop for a stated conclusion with no ending, a place named early going straight to its practice, the first and second body answers keyed on the stored phase, the decline close set in code, an anchored "nothing" pattern and a six word place rule, the negative close placed after the waves check, no exercise after a body route with no practice, a stale Skip tap still skipping with no compatibility code, a question mid framework as an uncounted hold, a test that the trimmed practices stay distinct, "the chat was bad but the breathing helped" read as mixed, and a "worse" message with its own question keeping the model's answer. Not taken: a scripted eval for medical advice, since it needs real model runs and the replay in AC-17 asks those questions.
