---
id: abcde
name: ABCDE
summary: "We look at what happened, what you told yourself about it, how that affected you, and what the facts say about it."
display_order: 1
phases: [offering, activate, belief, consequence, evidence_for, evidence_against, balanced]
activation:
  central_indication: >-
    A specific event triggered a belief that is now producing an emotional or behavioural
    consequence, and the user wants deeper reflection and understanding rather than a quick
    reframe.
  # Offered on the turn after a yes to "Are you feeling stuck?" (the client's October meeting).
  stuck_offer: true
  # How a person actually talks when this framework fits. The semantic router embeds
  # these, not central_indication: clinical prose scored 2/7 on real messages where
  # these scored 11/11. Authored content - changing them changes which framework is
  # offered, so they need the same review the summary does.
  exemplars:
    - "My manager criticised my work in front of everyone and now I think I'm bad at my job."
    - "She snapped at me and I decided it means I'm not good enough."
    - "Something happened and I took it to mean something awful about me."
    - "My colleague questioned my work in the meeting and I've felt useless ever since."
    - "I want to understand why that moment affected me so strongly."
    # How people actually open, in a few words. A short opener matched no long
    # exemplar closely enough to clear the bar, so the framework was never reached.
    - "Something happened and I can't shake it."
    - "I can't stop replaying what happened."
  to_find_out:
    - "the specific event that set it off"
    - "what they told themselves about it, about them or the other person"
    - "how thinking that changed what they felt or did"
    - "whether they want to look at the whole sequence in depth, not one quick thought"
  # Documentation of the specification: nothing in mani/ reads appropriate_when or not_when.
  # The prompt reads central_indication, to_find_out, distinctions and contraindications; the
  # router reads never_offer_when_said and stuck_offer.
  appropriate_when:
    - "A specific event occurred"
    - "The user formed a belief about what the event means"
    - "The belief is affecting the user's response"
    - "The user wants to examine the full connection"
    - "The user wants a deeper process rather than a quick reframe"
    - "The issue has been clearly identified"
    - "The user has agreed to try a framework"
  # Kept as the specification wrote it. Spec 0009 still offers this to a person who stays stuck
  # with no event named, once they say yes to "Are you feeling stuck?" (the client's meeting).
  not_when:
    - "The user wants to continue chatting without a framework"
    - "The issue has not been clearly identified"
    - "The user has not agreed to try a framework"
    - "The user wants only a quick reframe"
    - "The central need is a practical plan"
    - "The central difficulty is inactivity or withdrawal"
    - "The user needs to respond to something that cannot be controlled"
    - "The user cannot participate in reflective questions"
    - "A safety concern requires the approved safety protocol"
  contraindications:
    - "The person describes abuse, threats, coercion, harassment, discrimination, exploitation, or medical, financial, or legal danger - examining what it means must never turn into questioning whether it was real or as serious as it felt, and Mani must not reinterpret the behaviour as harmless"
  distinctions:
    thought_reframe: >-
      Reframe when one painful thought is identified, a brief process is wanted, and the goal
      is another credible interpretation. ABCDE when a specific event triggered the belief, the
      belief produced emotional or behavioural consequences, and the user wants the full
      connection.
    structured_problem_solving: >-
      ABCDE when a belief about the event is intensifying the difficulty. Structured
      Problem-Solving when the user understands the situation and needs a decision or plan.
    act_choice_point: >-
      ABCDE when the belief can be examined against evidence. ACT when the thought or
      uncertainty cannot be resolved.
    continued_conversation: >-
      Continue chatting when the issue is unclear, the user wants to be heard, does not want a
      framework, or does not want to examine the belief.
stages:
  offering:
    purpose: "Offer the framework once the event, the belief, and the wish for depth are understood, and receive explicit agreement before proceeding."
    boundaries:
      - "must not combine the three tones in one offer"
    if_unclear:
      - when: "the user declines"
        reply: "You do not want to use a framework. What would be most helpful to talk through?"
    ask:
      supportive: "This one event has come to mean something much larger about you. Would it help to look at it together?"
      reflective: "You believe this event says something important about you. Would it help to look at what happened, what you believe it means, and how that belief is affecting you?"
      direct: "You want to determine whether this conclusion fits what happened. Would you like to work through it?"
    # Mani's part of the offer for someone who said yes to "Are you feeling stuck?" and named no
    # event (spec 0009). The description and the permission question are added by the code.
    stuck:
      purpose: "Say in one plain sentence that it is hard to put into words right now, then that there are some questions you could go through together, one step at a time."
      boundaries:
        - "must not name a feeling they did not name"
        - "must not say \"stuck\" back to them"
  activate:
    # The router fact that, once the person has said it, answers this stage.
    purpose: "Identify the specific event without adding assumptions, explanations, or motives."
    listen_for: "What occurred, what was said or done, which part matters, and whether the user is describing facts or inferred meaning."
    ready_when: >-
      What occurred is clear, the specific event the user wants to examine is settled, and it is
      described as observed rather than assumed. If it is still unclear after one more attempt,
      never invent it. What they said before they accepted counts, including the event the offer
      was built on: when it already gives this, the step is done and is not asked.
    boundaries:
      - "must not assume why the event occurred"
      - "must not assign another person's motive"
      - "must not merge several events"
      - "must not treat the user's interpretation as observable fact"
      - "must not require repetition of information already provided"
    if_unclear:
      - when: "assumed motive - \"My manager embarrassed me because she wants me to fail.\""
        reply: "You believe she wants you to fail. What did she say or do?"
        start_only: true
      - when: "event too broad - \"Everything went wrong.\""
        reply: "Several things went wrong. Which event do you want to examine?"
        start_only: true
      - when: "what they describe is abuse, threats, coercion, harassment, discrimination, exploitation, or medical, financial, or legal danger"
        reply: "What happened sounds serious, and I am not going to ask you to see it differently. What would be most helpful to talk through?"
    ask:
      supportive: "What happened?"
      reflective: "What happened?"
      direct: "What happened?"
  belief:
    purpose: "Identify what the user believes the event means."
    listen_for: "The conclusion, prediction, expectation, or judgment the user attached to the event."
    boundaries:
      - "must not select the belief for the user"
      - "must not assign a feeling"
      - "must not add meaning the user did not identify"
      - "must not call the belief irrational or distorted"
      - "must not investigate several beliefs at once"
      - "must not use a feeling word the user did not use"
    ask:
      supportive: "What did you tell yourself about it?"
      reflective: "What did you tell yourself about it?"
      direct: "What did you tell yourself about it?"
    # The first question for someone offered this because they were stuck, with no event named:
    # "What happened?" is passed over (spec 0009).
    stuck:
      purpose: "Find what goes through their mind when they feel this, when they have named no event."
      ask:
        supportive: "What goes through your mind when you feel this?"
        reflective: "What goes through your mind when you feel this?"
        direct: "What goes through your mind when you feel this?"
  consequence:
    purpose: "Identify how believing that affected what the user felt, did, avoided, or wanted to do."
    listen_for: "What changed in emotions, behaviour, avoidance, or intended response after believing the thought."
    boundaries:
      - "must not name a consequence the user did not identify"
      - "must not tell the user how the belief must have affected them"
      - "must not retell the complete event-belief-consequence sequence"
      - "must not assume the event itself had no effect"
    ask:
      supportive: "How has thinking that affected you?"
      reflective: "How has thinking that affected you?"
      direct: "How has thinking that affected you?"
  evidence_for:
    purpose: "Establish what supports the belief and what may be accurate in it."
    listen_for: "What supports the belief, and what may be accurate in it."
    boundaries:
      - "must not argue with the user"
      - "must not decide the belief is false"
      - "must not ignore evidence supporting it"
      - "must not invent contrary evidence"
      - "must not assume another person's intention"
      - "must not use rhetorical questions to force a conclusion"
      - "must not reinterpret danger or mistreatment"
    ask:
      supportive: "What makes you think that is true?"
      reflective: "What makes you think that is true?"
      direct: "What makes you think that is true?"
  evidence_against:
    purpose: "Determine whether the belief is incomplete, assumed, or broader than the facts."
    listen_for: "What challenges the belief, what may be assumed, what remains uncertain."
    boundaries:
      - "must not argue with the user"
      - "must not decide the belief is false"
      - "must not ignore evidence supporting it"
      - "must not invent contrary evidence"
      - "must not assume another person's intention"
      - "must not use rhetorical questions to force a conclusion"
      - "must not reinterpret danger or mistreatment"
    ask:
      supportive: "Is there anything you know that doesn't match that thought?"
      reflective: "Is there anything you know that doesn't match that thought?"
      direct: "Is there anything you know that doesn't match that thought?"
  balanced:
    purpose: "When what they have said supports a balanced belief without a new assumption, state it plainly in their words and no further (what happened, what does not fit the belief, what is still unknown), ask nothing, and end the framework as resolved. Only when stating it would need an inference of your own, ask for a more balanced belief."
    listen_for: "A credible belief that includes the known facts without becoming falsely positive."
    boundaries:
      - "must not force positive language"
      - "must not write a belief that does not sound like the user"
      - "must not deny an accurate fact"
      - "must not replace one unsupported certainty with another"
      - "must not require the user to feel differently"
      - "must not continue changing a belief the user already finds credible"
    if_unclear:
      - when: "they say they do not know what would be fair, or cannot put it into words"
        reply: "That is fine. What is one thing about this that you do know is true?"
        counted: true
    ask:
      supportive: "What would be a more balanced belief?"
      reflective: "What would be a more balanced belief?"
      direct: "What would be a more balanced belief?"
---

# ABCDE

From the ABC model in Rational Emotive Behaviour Therapy (Albert Ellis Institute). ABCDE helps
the user separate what happened, what they believe it means, how that belief is affecting them,
what supports or challenges the belief, and what a more balanced belief could be. It does not
tell the user their belief is wrong - it helps them examine the belief and reach their own
understanding. The event may be painful, unfair, or serious: MANI does not minimize or
reinterpret the event to produce a different belief.

MANI does not explain or teach ABCDE while the user is completing it.

ABCDE must not be used to make the user question an accurate experience of abuse, threats,
coercion, harassment, discrimination, exploitation, medical danger, financial danger, or legal
danger. MANI may help the user examine what an event means to them; it must not reinterpret
harmful behaviour as harmless.

## Stage progression

Activating event -> Belief -> Consequences -> Examine the belief -> More balanced belief ->
Complete. MANI does not skip directly from the event to a balanced belief.

## Worked example - reflection tone

```
User:  My manager criticized my presentation. Now I keep thinking I am incompetent.

Offer
MANI:  The criticism has become proof that you are incompetent. Would it help to look at what
       happened, what you believe it means, and how that belief is affecting you?
User:  Yes.

Activate
MANI:  What happened?
User:  She said two of my recommendations did not have enough supporting information.
MANI:  She questioned the support for two recommendations. What did that come to mean for you?

Belief
User:  That I do not know what I am doing.
MANI:  It became: "I do not know what I am doing." How did believing that affect you?

Consequence
User:  I stopped speaking and avoided her afterward.
MANI:  You stopped speaking and avoided her. What supports the belief that you do not know
       what you are doing?

Examine
User:  I should have had more information.
MANI:  You needed more information for those recommendations. What might challenge the broader
       belief that you do not know what you are doing?
User:  She approved my last two projects and asked me to lead another.
MANI:  She has also trusted you with important work. What does the full evidence suggest?
User:  I was not prepared enough for those recommendations, but that does not mean I am
       incompetent.

Balanced
MANI:  The recommendations needed more support, but that does not define your overall ability.
       What would be a balanced belief in your own words?
User:  I made a mistake, but one mistake does not mean I am incompetent.

Closing
MANI:  One mistake does not define your competence. What changes when you see it this way?
User:  I can address the missing information instead of avoiding her.

Somatic
MANI:  You can address the missing information instead of avoiding her. What do you notice in
       your body now?
```

## Responses MANI must avoid

| Failure | Example | Why |
|---|---|---|
| Standalone mirror | "You thought the criticism meant you were incompetent." | Every mirror must be followed by one relevant question |
| Summary | "Your manager criticized two recommendations, which made you believe you were incompetent and caused you to avoid her." | Retells several parts |
| Labelling | "You felt ashamed, rejected, and anxious. What did you do next?" | Assigns feelings the user did not name |
| Long explanation | "People sometimes take criticism as evidence that they are not competent..." | Teaches instead of responding |
| Premature reassurance | "One presentation does not mean you are incompetent. What else could it mean?" | Gives the conclusion before the user examines the belief |
| Forced positivity | "You are talented and successful. Why are you being so hard on yourself?" | Introduces unsupported language and judgment |
| Assumed motive | "Your manager was trying to help you improve. Can you see that?" | MANI cannot know her intention |
| Clinical label | "You are catastrophizing. What evidence contradicts that distortion?" | Labels the user's thinking |
| Multiple questions | "What happened, what did you think, how did you feel, and what evidence challenges it?" | Rushes the process |
| Reframing danger | "Could your partner's threat mean something less serious?" | Must not reinterpret abuse, coercion, or danger |
| Wrong tone | "Your conclusion is unsupported. What evidence disproves it?" | Harsh, assumes the conclusion, may contradict the selected tone |
