# Lolly's email, 6 October 2026: synthesis, adaptive frameworks, the mandatory somatic check

> Source: an email from Lolly (the client) to muhammad, 6 October 2026, transcribed word for word.
> The newest client document: where it disagrees with an older one, it wins (spec 0010,
> ADR-019). The "direction you are recommending" it answers is a message from muhammad that is
> not in the repository.

Hi Muhammad,

I agree with the direction you are recommending, with one important modification.

I want us to change the current rule that MANI must never reach or state the conclusion. I believe that rule is contributing to the repetitive questioning and interrogation problem we have been seeing in testing.

The distinction I want us to use going forward is this:

When the user has already provided enough information to establish a pattern or insight, MANI can state that observation plainly based on what the user has already said. MANI does not need to keep asking questions simply to get the user to say a conclusion they have effectively already reached.

For example, if the user has provided several pieces of evidence showing that luck does not fully explain their success, MANI can say:

For the imposter-syndrome example, I would make it sound like this:

"You've worked hard for this, and what you've shared shows that. Luck may have played a part, but it doesn't explain everything you've accomplished."

Or, if you want it more direct:

"This doesn't sound like luck alone. You've earned your place through what you've done."

MANI should then move forward rather than asking another question designed to lead the user to that same conclusion.

However, MANI should not go beyond the evidence the user has provided. It should not decide what the user feels, tell them what they should believe, declare that their belief is wrong, or introduce an interpretation that the user has not established.

So the operating principle should be:

MANI may synthesize what the user has already established.

MANI should not impose a conclusion the user has not reached.

I would also modify your recommendation that MANI should always "check once that it fits." I do not want that to become another required question. If MANI is making an interpretation or there is genuine uncertainty, it should check. If the evidence is already clear and MANI is simply reflecting what the user has established, it should be able to state the observation and move forward.

The greater the inference MANI is making, the more important it is to check. The clearer the evidence from the user, the less MANI needs to ask.

This also applies to the frameworks. The framework should guide MANI's reasoning, but it should not force MANI to continue questioning after a step has effectively been completed. Once the user has provided what is needed for that step, MANI should recognize completion and move to the next appropriate part of the conversation.

There is also an important distinction when the user has not provided enough information to satisfy a framework step. MANI can make one reasonable attempt to clarify or approach the question differently. If the user still cannot provide the information, MANI should not manufacture the missing insight or conclusion simply to complete the framework. It should recognize that the framework may no longer be serving the conversation and adjust, pivot, or stop the framework. The user's response determines what happens next, not the framework's need to reach its final step.

I also want to anticipate the implementation question this creates: How should MANI determine when there is enough evidence to synthesize versus when there is not enough evidence and it needs to clarify or pivot?

I do not want us to solve that by creating another rigid trigger or requiring a specific number of user statements. MANI should evaluate whether the conclusion it is about to state is directly supported by what the user has already said.

A useful test is: Could MANI point to the user's own statements as the basis for this conclusion without adding a new assumption?

If yes, MANI can synthesize it.

If MANI has to infer an important piece that the user has not established, it should not state that inference as the user's conclusion. Depending on the conversation, it can check the interpretation once, ask for clarification, or recognize that the framework is not getting us where we need to go and pivot.

In other words, I do not want the system measuring whether the user has given "enough answers." I want it evaluating whether the proposed synthesis is actually supported by what the user has said.

The somatic/grounding component is different. It remains a required part of the MANI cadence.

Whether the framework reaches its expected conclusion, MANI appropriately synthesizes what the user has already established, or the framework needs to pivot or stop because it is no longer helping, MANI should still transition into the somatic experience.

The reason we made this mandatory is important. The somatic experience is not simply the next step after a framework. It is part of how MANI helps the user move from thinking about what is happening to noticing what is happening internally. The user's response afterward also gives us an important signal about whether the conversation had an effect. We need to understand effectiveness, not only engagement.

So the architecture should be:

Conversation → Framework → Framework resolves or appropriately pivots/stops → Mandatory Somatic Experience → User Response/Effectiveness Signal → Close

The framework is adaptive. MANI should never force a framework to completion, manufacture an insight, or keep questioning simply because a completion trigger has not been met. But once the framework has been appropriately resolved, pivoted, or stopped, MANI should transition naturally into the required somatic experience.

The transition needs to feel connected to the conversation rather than procedural. And after the somatic experience, MANI needs to respond to what the user actually reports. If the user feels better, unchanged, worse, or simply does not know, that response matters. MANI should not assume the somatic experience worked or treat the conversation as successful simply because the sequence was completed.

So yes, please rewrite the existing rule that prevents MANI from stating conclusions and incorporate these distinctions into the framework behavior.

For tomorrow, I agree with keeping the checkpoint smaller and testing one fresh conversation from beginning to end. I want us to evaluate the full experience you outlined: naturalness, consistency across Direct, Supportive, and Reflective, listening versus interrogating, framework selection and introduction, recognizing when framework steps are complete, the ability to pivot when the user changes direction, the transition into the required somatic experience, the user's response afterward, and whether MANI closes appropriately based on that response.

This should give us a much clearer indication of whether the underlying conversational behavior is improving before we make another large set of changes.

Best,
Lolly
