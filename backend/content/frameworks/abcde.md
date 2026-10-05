---
id: abcde
name: ABCDE
# The client's sentence, with the name and the steps around it so they know what they are
# starting (client meeting, 2026-10-02). The added wording awaits the client's sign-off.
summary: "There's an approach called ABCDE that fits this. These questions help you separate what happened from what you told yourself about it, question what may not be serving you, and come away with a clearer and more useful way of seeing the situation. We'll take it one step at a time: what happened, what you told yourself about it, what that led to, whether that thought holds up, and a more balanced way of seeing it. You can stop at any point."
display_order: 1
phases: [offering, activate, belief, consequence, examine, balanced, closing]
activation:
  central_indication: >-
    A specific event triggered a belief that is now producing an emotional or behavioural
    consequence, and the user wants deeper reflection and understanding rather than a quick
    reframe.
  # A confident offer waits for their third message: the fit depends on what they took the event or
  # the thought to mean, which the first two messages rarely say.
  earliest_offer_message: 3
  to_find_out:
    - "the specific event that set it off"
    - "what they took it to mean about themselves or the other person"
    - "how believing that has affected what they felt, did or avoided"
    - "whether they want to look at the whole sequence in depth, not one quick thought"
  # Documentation of the specification: nothing in mani/ reads appropriate_when or not_when.
  # The prompt reads central_indication, to_find_out, distinctions and contraindications; the
  # router reads strong_signals and signals.
  appropriate_when:
    - "A specific event occurred"
    - "The user formed a belief about what the event means"
    - "The belief is affecting the user's response"
    - "The user wants to examine the full connection"
    - "The user wants a deeper process rather than a quick reframe"
    - "The issue has been clearly identified"
    - "The user has agreed to try a framework"
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
  # Short fragments, not the full example sentences from the spec. router.py matches these as
  # whole words against what the person actually typed - a real message practically never
  # contains a whole authored sentence verbatim, but it very often contains the three or four
  # words that carry the pattern ("so i must be", "proves i will never"). Confidence now also
  # requires corroboration (two fragments, or one repeated) before a framework is offered, so
  # shortening these to raise recall no longer trades away precision the way it would have
  # before that gate existed.
  strong_signals:
    - "so i must be"
    - "must mean i am"
  signals:
    - "this proves i"
    - "proves i will never"
    - "everyone must think i am"
    - "i always ruin everything"
    - "i will always be alone"
    - "i know i will fail again"
    - "nothing will ever improve"
    - "has no respect for me"
    - "because nobody likes me"
    - "terrible at my job"
    - "because i do not matter"
    - "i failed once"
    - "wants me to fail"
    - "want me to fail"
    - "wanted me to fail"
    - "embarrassed me"
    - "embarassed me"
    - "humiliated me"
  redirects:
    - signal: "Nobody cares about me, and I want a quick way to look at that thought."
      instead: thought_reframe
    - signal: "I know what happened, but I need to decide what to do."
      instead: structured_problem_solving
    - signal: "I cannot control what happened, but I do not want it directing my choices."
      instead: act_choice_point
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
  activate:
    purpose: "Identify the specific event without adding assumptions, explanations, or motives."
    listen_for: "What occurred, what was said or done, which part matters, and whether the user is describing facts or inferred meaning."
    ready_when: "What occurred is clear, the specific event the user wants to examine is settled, and it is described as observed rather than assumed. If the event remains unclear, stay in this stage."
    boundaries:
      - "must not assume why the event occurred"
      - "must not assign another person's motive"
      - "must not merge several events"
      - "must not treat the user's interpretation as observable fact"
      - "must not require repetition of information already provided"
    if_unclear:
      - when: "assumed motive - \"My manager embarrassed me because she wants me to fail.\""
        reply: "You believe she wants you to fail. What did she say or do?"
      - when: "event too broad - \"Everything went wrong.\""
        reply: "Several things went wrong. Which event do you want to examine?"
      - when: "what they describe is abuse, threats, coercion, harassment, discrimination, exploitation, or medical, financial, or legal danger"
        reply: "What happened sounds serious, and I am not going to ask you to see it differently. What would be most helpful to talk through?"
    ask:
      supportive: "What happened?"
      reflective: "What happened?"
      direct: "What happened?"
  belief:
    purpose: "Identify what the user believes the event means."
    listen_for: "The conclusion, prediction, expectation, or judgment the user attached to the event."
    ready_when: "One central belief identified in the user's own language. If several beliefs appear, ask which one affected the user most."
    boundaries:
      - "must not select the belief for the user"
      - "must not assign a feeling"
      - "must not add meaning the user did not identify"
      - "must not call the belief irrational or distorted"
      - "must not investigate several beliefs at once"
      - "must not use a feeling word the user did not use"
    if_unclear:
      - when: "a feeling instead of a belief - \"I felt embarrassed.\""
        reply: "You felt embarrassed. What were you telling yourself at that point?"
      - when: "several beliefs at once"
        reply: "Several thoughts came at once. Which one affected you most?"
    ask:
      supportive: "What did that come to mean for you?"
      reflective: "What did that come to mean for you?"
      direct: "What did that come to mean for you?"
  consequence:
    purpose: "Identify how believing that affected what the user felt, did, avoided, or wanted to do."
    listen_for: "What changed in emotions, behaviour, avoidance, or intended response after believing the thought."
    ready_when: "A consequence the user identified themselves - something felt, did, avoided, or wanted to do. Do not introduce a consequence the user did not name."
    boundaries:
      - "must not name a consequence the user did not identify"
      - "must not tell the user how the belief must have affected them"
      - "must not retell the complete event-belief-consequence sequence"
      - "must not assume the event itself had no effect"
    if_unclear:
      - when: "consequence unclear - \"It affected everything.\""
        reply: "It affected everything. What changed first?"
    ask:
      supportive: "It reached into everything for you. What felt most affected?"
      reflective: "You noticed it affecting everything. Where did you see the effect most?"
      direct: "It affected everything. What changed first?"
  examine:
    purpose: "Determine whether the belief is fully supported, partly supported, incomplete, assumed, or broader than the facts."
    listen_for: "What supports the belief, what challenges it, what may be accurate, what may be assumed, what remains uncertain."
    ready_when: "In this order: first what supports the belief, then what challenges it, then what the full evidence suggests. The user has considered what may be accurate, what may be broader than the facts, and what remains uncertain. The user does not have to disprove the belief. Stay on the current step until the user has answered it."
    boundaries:
      - "must not argue with the user"
      - "must not decide the belief is false"
      - "must not ignore evidence supporting it"
      - "must not invent contrary evidence"
      - "must not assume another person's intention"
      - "must not use rhetorical questions to force a conclusion"
      - "must not reinterpret danger or mistreatment"
    if_unclear:
      - when: "part of the belief is accurate - \"I was not prepared enough.\""
        reply: "You were not prepared enough for those questions. Does that prove you are incompetent?"
      - when: "no contrary evidence comes to mind - \"Nothing challenges it.\""
        reply: "Nothing comes to mind yet. Has anything happened that does not fit the belief?"
      - when: "what supports the belief has been said, and what challenges it has not yet been asked"
        reply: "What might challenge the broader belief that <their belief, in their words>?"
      - when: "the user has named evidence that challenges the belief (use the line for the selected tone)"
        reply: "supportive: She has also trusted you with important work. How does that affect the original belief? | reflective: That evidence does not fully fit the original belief. What does it suggest instead? | direct: That evidence challenges the original belief. What conclusion do the full facts support?"
    ask:
      supportive: "What supports that belief?"
      reflective: "What supports that belief?"
      direct: "What supports that belief?"
  balanced:
    purpose: "Develop a believable belief that includes the relevant evidence and remains in the user's language."
    listen_for: "A credible belief that includes the known facts without becoming falsely positive."
    ready_when: "A belief that acknowledges what happened, includes the evidence, avoids a broad judgment unsupported by the facts, sounds believable, and uses language the user accepts."
    boundaries:
      - "must not force positive language"
      - "must not write a belief that does not sound like the user"
      - "must not deny an accurate fact"
      - "must not replace one unsupported certainty with another"
      - "must not require the user to feel differently"
      - "must not continue changing a belief the user already finds credible"
    if_unclear:
      - when: "falsely positive - \"I am brilliant, and my manager was completely wrong.\""
        reply: "That removes the parts you said needed improvement. What belief includes all the evidence?"
      - when: "cannot form a balanced belief"
        reply: "You said the recommendations needed more support, but one presentation does not define your ability. How would you put those together?"
    ask:
      supportive: "You can recognize the mistake without defining yourself by it. What would feel fairer and still true?"
      reflective: "The full evidence is different from the original conclusion. What belief holds all of it?"
      direct: "The original belief is broader than the facts. What do the facts support?"
  closing:
    purpose: "Confirm completion in the user's own terms, without declaring that the framework worked."
    ready_when: >-
      The user has identified what happened, what they believed it meant, how that belief
      affected them, what supports and challenges the belief, and a more balanced belief. The
      user does not have to feel differently, eliminate the original belief, view the event
      positively, forgive anyone, take immediate action, agree with MANI, or resolve the
      external situation.
    boundaries:
      - "must not require the user to feel differently, forgive anyone, or take action to be done"
      - "must not summarize the completed framework"
      - "must not tell the user the framework worked"
      - "must not say the belief feels fairer unless the user used similar language"
    ask:
      supportive: "This belief feels fairer to what happened. How is it sitting with you?"
      reflective: "The new belief includes the full evidence. What changes when you see it this way?"
      direct: "This belief is supported by the facts you identified. Does it feel accurate?"
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
