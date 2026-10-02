# Panic and already answered stages (2026-10-01)

What the lost wallet chat taught, so the next session does not repeat it. Decision: [[ADR-010-a-person-in-panic-is-guided-not-quizzed]].

- **A note in `[ctx]` does not beat a question sitting in `[ctx]`.** The "move on, do not confirm" rule was in
  the prompt, and the first stage's question was still in the context, so the model copied it. Withhold the
  text you do not want asked.
- **Look for examples that contradict a new rule.** `mani_base.md` still showed the answer being "checked
  back"; the model followed the example. Grep the prompt for the old behaviour before measuring.
- **The code had its own say.** `registry.clamp` allows one stage past the offer, so a reply that asked the
  second stage was rewritten to the first. A prompt change alone could not have worked.
- **The harness's journey check was broken.** It looked for a phase named `somatic`; the stages are
  `somatic_checkin` and `somatic_practice`. It failed every journey. Fixed to match the prefix.
- Eval scripts send fixed messages, so when an offer arrives a message early or late the script's "yes" or
  "they are all active" answers the wrong thing. Read the transcript before trusting a count.
- Open: `eval_replies` flags "panic" when the person said "panicking"; the feeling check in the harness does
  not merge stems the way `repairs.introduced_feelings` does.

## Follow up, same day

- Skipping the first stage whenever it "counts as answered" was too blunt: someone who names a wish ("be more
  productive") has not named what they stopped doing. The stage's own `ready_when` is the test; give the model
  the stage and its test, not a blanket rule. See [[ADR-011-first-stage-by-its-own-test-and-one-draft-when-asked-to-pick]].
- "Pick one for me" was met with options again, twice. Offering a list is not the same as helping someone who
  has said they cannot choose; one draft they can change is.
- A repeated question needed a runtime check; the eval's `repeated_question` had been the only guard.
- Scripted test models that return one reply for every turn trip the repeat check. Write distinct replies.
