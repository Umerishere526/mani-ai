---
type: journal
date: 2026-10-12
tags: [journal, offers, abcde, decisions]
---

# ABCDE was offered at their second message (2026-10-12)

muhammad: before Friday it chatted, now it triggers ABCDE at the 2nd message. Cause: the 2026-10-09 ABCDE-only
commit (`70ca423`) deleted `earliest_offer_message: 3` and `context.earliest_offer_ok`, and `mani_base.md` says
ABCDE "is offered more readily than not" and "does not wait for the event". With one framework there is nothing
for the model to weigh it against, so almost any situation fits. Prompt wording alone does not hold this (see
[[direct-questions-have-no-target-2026-10-09]]: prohibitions swing to the opposite failure), so the wait is code.

Restored: `earliest_offer_message: 3` in `abcde.md`, `context.earliest_offer_ok`, the `earliest_wait` redraft note,
and the gate in `orchestrator` (an early offer is redrafted once, then dropped). The "offered from the first
message" decision of 2026-10-10 is reversed; the decision line in `PORT-STATUS.md` was edited in place.
Needs `python scripts/seed.py` after any change to the file ([[reverting-code-does-not-revert-the-database]]).

Not measured live. Cost to expect: a model that still offers at message 1 or 2 spends one redraft call.
Integration tests must call `past_the_opening` or their message counts are two short.

## Stuck at dispute, and the plan that followed (same day)

muhammad's coworker chat looped at the evidence stage on "idk", "yes", "always": five asks of one stage.
Cause, in both the pre-commit and the Friday code: `context._TWO_TRIES` ended "unless stage_ready_when says to
stay", the stage's own ready_when said stay, and `partial` counted as not met in `redraft.ledger_stage`, so the
ledger check sent the model back each time. Nothing counted asks. Now `thread_technique_state.stage_asks`
(migration 011) counts them, `[ctx]` says `stage_asked: twice`, the ledger check lets the stage go at two, and
`repairs.apply` records the next stage if the reply still stays. The closing and body route are exempt.

Also: the ledger was missing whenever the model left out `stages_known`; it now falls back to the recorded stage.
On the accept turn `said_before_yes` puts their earlier messages beside the stages. A prompt bullet with a colon
failed `test_every_rule_in_a_prompt_file_is_a_sentence_not_a_yaml_mapping` again: write "that is" instead.
Not yet measured live; replay the coworker chat and run `scenario_check.py` before trusting it.
