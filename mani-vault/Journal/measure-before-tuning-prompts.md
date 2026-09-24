---
type: journal
date: 2026-09-23
tags: [journal, prompts, evals, lessons]
---

# Measure before tuning prompts

Lessons from the chat-quality audit on 2026-09-23. See [[ADR-005-per-person-memory-across-conversations]].

## One eval run is not a measurement

`eval_replies.py` makes 48 stochastic model calls. The same prompt produced 3 findings and then 7.
Prompt changes judged from single runs were judged on noise. Run a scenario three times before and
three times after (`--scenario` exists for this), and compare counts.

## Check what the eval can observe

"94% mirror and ask" looked like a failure, but every scripted turn was one where a question
belonged. The eval had no turn where another shape could win. Adding
`disclosure_no_question_needed` showed the shapes were fine. The first version of that scenario reused
the prompt's own example sentences and got near-verbatim replies back: that was testing recall.

## Schema field order is the strongest lever

Structured output is generated in schema order, confirmed from the provider's raw JSON. With
`reasoning` and `style` declared after `text`, the model's "check your openers" step ran after the
reply was written. Moving them first cut repeated openers from 6 in 9 conversations to 1 in 15.

More prose rules did not work for style. A style check added to the reasoning steps did nothing, and
average latency rose. It was reverted.

## Fakes hide cross-connection behaviour

The memory fold deadlocked live and passed every scripted test. `client.complete` records its cost row
on a separate admin connection. That row's foreign key needed a key-share lock on the thread the fold
had claimed `FOR UPDATE`, and the fakes never wrote a cost row. The fix was `FOR NO KEY UPDATE`.

When a fake stands in for something that touches the database, make at least one test do the real write.

## Mutation-check new queries

Breaking the fold condition on purpose made `fold_finished` loop forever, paying for a model call each
time. That is why there is `MAX_FOLDS_PER_RUN`. Whether a test catches a mutation is a cheap question
to ask of any new query.

## Check the measurement table for test residue

Integration tests ran against the same local database the evals read, and left 108 fake
`admin.llm_calls` rows behind. Deleting the user sets `user_id` to null, and one test used the
real model name. Cache and latency averages over any window that included a `pytest` run were
wrong: "53% cached" was really about 60%. Fixed at the fixtures. When reading cost numbers,
exclude rows with no user if they look synthetic.

## Things muhammad decided (2026-09-23)

- Framework ending: the closing question, then the body check-in.
- Nickname: allowed sparingly (at most once a conversation, never first word).
- Crisis in another chat: carry a flag, don't lock.
- Memory: separate record, fold on new chat plus 24 h idle, admin-visible, used in chat.
- Unknown library value on a button: send to `home`.
