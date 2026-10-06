---
type: decision
status: proposed
date: 2026-10-05
apps: [backend]
tags: [decision, ai, conversation, questions]
---

# ADR-017: Questions are asked plainly

**Status:** proposed, 2026-10-05 (built; the real model run of spec 0008 AC-9, six conversations, is still to come and muhammad has to say yes before it runs).
Amends [[ADR-015-what-the-person-said-before-accepting-is-not-asked-again]] (the say back is its own short sentence, not a clause) and [[ADR-012-mani-speaks-plainly-and-tone-is-the-prompts-job]] (the base prompt gains a question rule and one fixed check).
**Affects:** backend (`context.py`, `mani_base.md`, `response_format.md`, `somatic.md`, `dbt_stop.md`, `abcde.md`, `thought_reframe.md`, `tests/evals/validators.py`, `scripts/eval_replies.py`, `scripts/client_style_counts.py`, `eval_conversations.yaml`)

## Context

The team lead picked four questions from the earlier Mani as the target: plain, neutral, answerable without stopping to think ("What does being alone feel like for you today?"). The step questions were already plain, but the instructions themselves asked for a wrapper: seven `[ctx]` stage notes and two prompt lines said "in their words, never bare" or "say it back in a clause", and the model answered with questions like "Since you've mentioned that you find yourself losing an hour to scrolling, what makes returning to the time you spent doing other things matter to you?". Its own questions ranked or abstracted ("What gives it that meaning?", "Which part is pulling the most on you?"). In the old chat, a person who said they were stuck was handed either/or questions and answered "i cant decide" twice. Spec 0008 holds the options and reasoning.

## Decision

- Every stage note says "ask it plainly": the question as written, or with one of their words in place of a general one, with no clause in front of it. On a turn that credits what they said before accepting, the say back stays, as its own short sentence before the question. The client's opening line after a yes does not count toward the one or two sentences.
- The base prompt says a question asks one thing they can answer straight away, about something they said, in fewer than 16 words, never opening with a clause. It never asks them to rank or judge their own state, or what would help before they have named something. "conclusion" and "meaning" join the words Mani never uses. Supportive's questions are about something they said, not about what would help.
- Before any offer, a person who cannot think or decide, is confused, or says "I don't know" twice running may be asked exactly "Are you feeling stuck?", once in a conversation, never under `safety: concern`. It is a check, never a statement, so it is the one exception to naming no feeling. Then one concrete question about something they said, and never a choice of two things. It never forces an offer: spec 0005's fit rule still decides.
- Two body check lines are reworded (Supportive "What are you noticing in your body right now?", Reflective "Where do you feel that in your body?"), one DBT STOP panic line loses "present for you", and three `to_find_out` lines drop "took it to mean", "believing" and "why that thought hurts".
- Nothing at runtime rejects or redrafts a reply for its question. Measurement is in the eval only: `validators.question_findings` counts long questions, lead clauses, flagged words and either/or questions after a stuck message, printed by `eval_replies.py` and `eval_client_style.py`. A unit test holds every authored question to the same rules.
- The base prompt line limit goes from 115 to 118 (muhammad, 2026-10-05). The question rule and the stuck check did not fit in 115 without cutting the examples and the "once in a conversation" that make them clear.

## Consequences

- Questions get shorter and plainer with no new model call and no new code path at runtime.
- Prompt only enforcement is not a guarantee; the AC-9 counts show how far the model follows it.
- Dropping the clause can make a reply feel less connected; the one swapped word and the say back sentence carry that, and the AC-9 read judges it.
- "At most once" for the stuck check is the model's judgment, not code; it can repeat once it scrolls out of the history.
- Supportive's body check is now open, so its "agree to notice" branch goes unused in that style.
- The client has not been told about the two body lines or the stuck check.
- Reversal: restore the content files and `mani_base.md` from the commit before, revert the notes in `context.py`, reseed. The eval checks can stay; they only measure.

## Links

- Spec: `docs/specs/0008-questions-answerable-without-thinking/index.md`
- Related: [[ADR-015-what-the-person-said-before-accepting-is-not-asked-again]], [[ADR-012-mani-speaks-plainly-and-tone-is-the-prompts-job]], [[ADR-014-a-framework-is-offered-only-when-the-facts-fit]]
- Journal: [[questions-easy-to-answer-old-mani-chat-2026-10-05]]
