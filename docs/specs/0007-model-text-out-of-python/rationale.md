# 0007. Rationale: model facing text out of Python, and offers only from the shortlist

The decision record for [index.md](index.md). `/develop` builds from the index. This file holds why.

## Context

> ⚠️ Premise note: this spec carries two decisions. The first is the scope's feature 8, moving model facing text out of Python. The second changes which frameworks get offered: the closest fit goes, and the router's shortlist becomes the set Mani may offer from. muhammad asked for the closest fit removal to be done here. The offer rule followed from it, because removing the closest fit takes away the fallback that guaranteed an offer, and something had to say what may be offered instead. The build plan keeps them in separate slices (1 to 5 the text, 6 and 7 the routing), so either half can be reverted on its own.

> ⚠️ Premise note: the routing half ships without real model runs, by muhammad's choice (2026-10-07). That was first picked when the spec was only a text move. It was asked again once the routing change joined, and muhammad kept it. The decision in force says a prompt change is judged on numbers, three runs before and three after. This change is not judged that way, so its effect on how often and how well Mani offers is unknown until feature 11 measures it.

> ⚠️ Premise note: this builds on uncommitted work. Specs 0005 and 0006 are built on `feat/turn-cost-baseline` but not committed, and spec 0004 (which moves the exercise pick and translation prompts into rows) is not built. Build plan step 0 makes both preconditions.

The scope's Slice 3 is "nothing hardcoded". Its feature 8 is done when no sentence the model reads is written in `backend/mani/`, and changing any of them needs only a reseed. Today that is far from true. Python writes the Framework Index's intro and closing, the memory heading and its usage paragraph, the techniques offered paragraph, the stage note sent on every framework turn, a description on every schema field, the summary and memory fold instructions, and the debug layer. Several of these say again what the authored prompts already say: `response_format.md` explains every `[ctx]` key, `mani_base.md` defines the six reply shapes that `schema.py` lists again, and `summarization.md` explains `current_issue` as the schema description does. The journal records what that costs. Prompt text names code's keys by their exact words, nothing ties them together, and a rename leaves the prompt pointing at nothing with every test green (`mani-vault/Journal/prompt-text-names-index-sections.md`).

Where text sits also changes what a turn costs. `[ctx]` is sent fresh with every message and is never cached. The system prompt's authored layers are a cached prefix billed at about a tenth. The stage note is three sentences of uncached text on every framework turn.

The router decides more than its comments admit. It scores phrase lists, applies six distinction rules written in Python, and when confident names one framework as `offer:` in `[ctx]`. When the person's fourth message comes with no offer made, the closest fit falls due and the top of the shortlist is offered even when the router is not confident. muhammad's direction is that every framework gets an equal chance and Mani decides from the person's situation and feelings. A nearest fit offered to meet a timer is not that. The distinction rules matter differently than they look. No model reads them, but they rank the shortlist, they can add a framework to it, and one of them (an imminent action) makes DBT STOP urgent enough to skip the usual waiting.

Two constraints bound the design. The decisions in force say a turn is one model call and the reply goes out as the model wrote it, so nothing may be checked by asking again or repaired afterwards. Conversations are special category health data, so nothing new may log what anyone said.

## Options considered

### Where the words go

#### Option A: code sends facts, prompts hold the words (chosen)

Python emits keys, headings and values. Each instruction moves into the authored prompt that already explains that input: `response_format.md` for `[ctx]` and the layers, `summarization.md` and `memory_fold.md` for their calls. Schema descriptions go, and the fields are described in prompts.

**Pros**: one home per rule. No new mechanism. The stage rules move into the cached prefix. A contract test can check keys in both directions.
**Cons**: the model reads a field's meaning in the system prompt rather than next to the field. The prompts grow. Every key becomes a contract between two files.

#### Option B: one keyed snippet row

A seeded row maps keys (`index.intro`, `stage_note.starting`, `memory.heading`) to text, and Python looks each one up and formats it.

**Pros**: the model reads exactly what it reads today, in the same places, so behaviour changes least.
**Cons**: a template format and a key lookup that can fail at runtime. The duplication with the authored prompts stays. The stage note stays uncached.

#### Option C: one template row per layer

Each generated layer becomes a seeded template with placeholders.

**Pros**: each layer is editable as a whole.
**Cons**: five more rows and a template language for text that is mostly data. The same duplication as B.

### The schema descriptions

Stripping them and describing the fields in prompts (chosen) was weighed against loading descriptions from a row and injecting them into the JSON schema at runtime, and against leaving them as code. Injection keeps the guidance next to the field, but it means sending a dict schema, validating separately, and keeping a second map in step with the model classes. Leaving them fails the scope's bar outright.

### What may be offered

#### Option D: the shortlist is the set Mani may offer from, told in the prompt (chosen)

The router lists every framework it saw signs of, ids only. The model offers only one of those, once it has learned what that framework's Starts when line names. With an empty list nothing is offered, and the miss is logged.

**Pros**: both sides must see the fit, as muhammad asked. The model chooses among the candidates, so they get equal chances. It needs no migration and no lag, and it fits "told, not enforced".
**Cons**: the phrase lists' reach caps every offer. The model can break a rule it is only told.

#### Option E: agreement checked in code across turns

The shortlist is hidden, the model's `heading_toward` is stored, and code compares it with the router's top pick on the next turn.

**Pros**: two independent votes, enforced.
**Cons**: a migration and a column, and a one turn lag. Once muhammad chose to keep the shortlist visible, the votes were no longer independent, so it added little over D.

#### Option F: the router as a hint, the model decides alone

The distinction rules are deleted and there is no gate. The model's pick wins.

**Pros**: the simplest, with the most offers.
**Cons**: no second view of the fit, which is what muhammad asked for.

#### Option G: keep the closest fit

**Pros**: everyone who keeps talking gets an offer by their fourth message.
**Cons**: it offers what does not really fit, on a timer. muhammad ruled it out.

## Rationale

Option A wins because it is the only one that removes the duplication instead of moving it. Options B and C keep a second copy of rules the authored prompts already state, which is the drift the journal recorded. They also keep the stage note in the uncached `[ctx]`, when the scope's whole purpose is fewer tokens and lower latency. A's cost is that keys become a contract between code and content. A two way contract test pays that cost: every key the code emits is explained, and every key explained is emitted. That is the check that was missing when the index sections were renamed.

The reply shapes follow the same reasoning. `mani_base.md` defines them for the model, so the guard reads that definition rather than a second list. A broken `reply_shapes` only empties the allowed set, because a reply shape is a nudge against repetition. The schema's own comment says no reported style is worth a lost turn, and a portal edit that takes chat down for a cosmetic list would contradict it. The seed refuses the broken file at authoring time, where refusing costs nothing. A database check also pinned the six shapes. Keeping it would make the seeded list a second copy that a portal edit could break mid turn: a new shape would pass the guard and then fail the insert, losing the turn. Dropping the check leaves the guard as the one gate. The cross check found this; the first draft missed it.

The distinction rules move into the framework files because adding a framework should be a content change, as the `ponytail` comment in `router.py` already asked. The rules are ordered, and two of them prefer the same framework, so order cannot come from file order or `display_order`. An explicit, unique `priority` keeps the order that the code's comment says must not be undone.

Option D follows from muhammad's answers taken together. Mani decides. The shortlist stays visible. Only what fits is offered. The urgency rule stays. Once the shortlist is visible, a told membership rule is something the model can check against a list it can see, and it costs nothing. Enforcing it after the call would be the reply repair 0006 removed. Membership anywhere on the list, rather than only the top, keeps the model deciding: the router narrows, ranking only orders, and nothing is cut at three that the router saw signs of. Router confidence and the `offer:` line go because "Offers follow Mani's confidence" is already in force, and a second confidence in the router only made two rules that could disagree. When the person asks for a kind of help, muhammad wants Mani to explore it and steer toward what fits, not offer on the spot. The shortlist then follows from their own words.

Two details follow from the shortlist becoming a gate. The router weighed only the person's last four messages, so a strong early sign dropped out of the list by their fifth or sixth message. As a ranking hint that was harmless, but as a gate it would lose an offer the person had earned, while the grief veto already reads the whole window. Older messages now keep the last weight instead. The miss log moved from `heading_toward`, which is set on every turn including running ones, to the offer itself: an offer off the list, or before the cooldown, is the one event that shows a told rule was broken.

The cost is stated plainly in the index's Consequences, and muhammad accepted it: fewer offers, a ceiling set by the phrase lists, and no measurement until feature 11.

## The text found in Python (2026-10-07)

| File | Model facing text | Goes to |
|---|---|---|
| `mani/prompts/composer.py` | Framework Index intro and closing line | `response_format.md` `layers`, `mani_base.md` `offers` |
| | `user_context` sentences | `## User Context` keys, `layers` |
| | memory heading, six labels, usage paragraph | `## Memory` keys, `layers` |
| | "Techniques Already Offered" paragraph | `response_format.md` `this_thread` |
| | summary layer labels | `## Conversation Context` keys |
| | `DEBUG_LAYER` | `content/prompts/debug.md` |
| `mani/chat/context.py` | `_stage_note` (three sentences) | `response_format.md` `framework_starting`, `stage_lines` |
| | `question_focus` value "feeling, then the way through" | token `feeling_then_way_through` |
| | `closest_fit`, `offer` lines | removed |
| `mani/llm/schema.py` | every `Field(description=...)` and class docstring on `Reply`, `SmartPrompt`, `TechniqueState`, `Crisis`, `Style`, `Extraction`, `ExtractedTechnique`, `Memory` | `response_format.md` `fields`, `summarization.md`, `memory_fold.md` |
| | `SHAPES` | `mani_base.md` `reply_shapes` (already there) |
| `mani/llm/tools.py` | `StartExercise` docstring and `exercise_id` description | `exercise_select.md` (spec 0004's row) |
| `mani/summarize.py` | wrapper labels, "No existing summary.", the closing instruction | `## Existing Summary` keys, `summarization.md` |
| `mani/memory.py` | "The conversation that just finished" heading | `## Conversation`, named in `memory_fold.md` |
| `mani/chat/router.py` | `DISCRIMINATORS` (no model reads them) | `activation.distinctions` in each framework file |
| `mani/llm/client.py` | exercise pick instruction | spec 0004 AC-6 |
| | "What this conversation is about:", "They said:" | `current_issue:`, `said:` keys, named in `exercise_select.md` |
| `mani/chat/orchestrator.py` | `User tapped the button: "<label>".` | `tapped: <label>`, named in `response_format.md` `buttons` |
| `supabase/migrations/003_thread_ownership_in_rls.sql` | `response_styles_shape_known` pins the six shapes in the database | dropped by migration 019 |
| `mani/stt.py` | translation prompt | spec 0004 AC-6 |
| `mani/chat/greeting.py` | `CLARIFICATION_QUESTIONS`, `AFTER_FRAMEWORK_QUESTIONS` | feature 9, with the code that matches them |
