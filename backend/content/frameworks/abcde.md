---
id: abcde
name: ABCDE
summary: "These questions help you see what happened, what you started believing about it, and how that belief has affected you, then look at whether it is true and find a more realistic and helpful way to see it."
display_order: 1
phases: [offering, activate, belief, consequence, dispute, effective]
activation:
  central_indication: >-
    The person has described a situation, what they started believing it means, or how that
    belief is affecting how they feel or what they do, such as feeling overwhelmed or anxious or
    not handling things well. They do not have to have said what happened: step A asks for the
    event when it is missing.
  to_find_out:
    - "what happened or has been happening that started these concerns"
    - "what they began telling themselves about it"
    - "how that belief has affected what they felt or did"
  contraindications:
    - "The only thing left to examine would be whether abuse, threats, coercion, harassment, discrimination, exploitation, or medical, financial, or legal danger was real or as serious as it felt. What they came to believe about themselves after it may still be examined; the event itself is never questioned or reinterpreted as harmless"
  distinctions:
    continued_conversation: >-
      Continue chatting when the issue is unclear, the user wants to be heard, does not want a
      framework, or does not want to examine the belief.
stages:
  offering:
    purpose: "Offer ABCDE once there is enough understanding to say what it would help with, and receive explicit agreement before proceeding."
    boundaries:
      - "must not combine the three tones in one offer"
      - "the offer says what ABCDE would help them do, in their situation, then asks if they would like to try it"
    if_unclear:
      - when: "the user declines"
        reply: "You do not want to use a framework. What would be most helpful to talk through?"
    ask:
      supportive: "Would you like to try it?"
      reflective: "Would you like to try it?"
      direct: "Would you like to try it?"
    stage_list: |-
      There are five stages in ABCDE:

      - A: Activating Event
      - B: Belief
      - C: Consequences
      - D: Dispute
      - E: Effective New Belief
    check:
      direct:
        - "Does that match what's been going on?"
        - "Have I understood that the way you mean it?"
        - "Is that close to how it is?"
        - "Did I get that right?"
      supportive:
        - "Does that sound like how it's been for you?"
        - "Is that close to what you've been going through?"
        - "Have I understood that the way you mean it?"
        - "Does that feel true to you?"
      reflective:
        - "Does that fit how you see it?"
        - "Is that close to how it sits with you?"
        - "Have I caught that the way you'd put it?"
        - "Does that seem true to you, or is something different?"
    offer:
      direct: |-
        There's a framework called ABCDE that helps you identify the thoughts behind <what they are going through, as a short noun phrase that reads naturally after "the thoughts behind", in their words, such as your anxiety, being left out of meetings, or what happened with your sister. When they describe someone's behaviour, name the situation, never the behaviour as a verb, so not your sister stopping talking to you but how things are with your sister. Never a whole sentence, never "the thought that", never a verb phrase like "wondering whether">, question whether they're true, and replace them with more realistic ones.
      supportive: |-
        <A short warm line in your own words that shows you understood what they said, using their words, such as "Feeling overwhelmed can make you question how well you're handling things.">
        There's a framework called ABCDE that can help you understand the thoughts behind <what they are going through, the same short noun phrase>, see whether those thoughts are really true, and find a more helpful way to think about what's happening.
      reflective: |-
        <A short line about how the way we interpret what is happening can make it feel harder, fitted to what they said, such as "Sometimes the way we interpret what's happening can make a difficult situation feel even harder.">
        There's a framework called ABCDE that helps you examine what you're telling yourself about <what they are going through, the same short noun phrase>, understand how those thoughts affect you, and consider whether there's a more realistic way to see things.
    keep_chatting:
      direct: |-
        What's been happening that's making you feel like <what they said they are struggling with, in their words>?
      supportive: |-
        We can keep talking. What's been happening that's making things feel so <how they described it, in their words>?
      reflective: |-
        When you say <what they said about themselves or the situation, in their words>, what experiences have led you to see it that way?
    explain:
      direct: |-
        The ABCDE framework has five steps:

        - A: Activating Event: What happened or what has been happening?
        - B: Belief: What did you start telling yourself about it?
        - C: Consequences: How did that thought affect how you felt or what you did?
        - D: Dispute: What makes you believe it's true, and what makes you question it?
        - E: Effective New Belief: What's a more realistic and helpful way to think about it?
      supportive: |-
        The ABCDE framework has five steps. Each one helps you understand what happened, what you started believing about it, and how those thoughts may be affecting you.

        - A: Activating Event: What happened or what has been happening that brought up these feelings?
        - B: Belief: What did you begin telling yourself about the situation?
        - C: Consequences: How did that belief affect how you felt or what you did?
        - D: Dispute: What makes you believe that thought is true, and is there anything that might suggest otherwise?
        - E: Effective New Belief: What's a more realistic and helpful way to think about what happened?
      reflective: |-
        The ABCDE framework has five steps that help you examine how your interpretation of an experience influences what you believe and how you respond.

        - A: Activating Event: What happened or what has been happening that started these concerns?
        - B: Belief: What meaning did you give to what happened?
        - C: Consequences: How did that belief influence your feelings or actions?
        - D: Dispute: What supports your interpretation, and what might suggest a different understanding?
        - E: Effective New Belief: What's a more accurate and helpful way to understand the situation?
  activate:
    title: "A: Activating Event"
    label: "A is for Activating Event."
    read_slots: [situation]
    purpose: "Identify the activating event from the conversation, confirming it or asking for it only when it is not already clear."
    listen_for: "What happened or has been happening, what was said or done, and whether the person is describing what they observed or what they inferred."
    ready_when: "The event is clear from what they have already said. If it is only a possible event, confirm it once, in the line below. If there is none, ask for it."
    boundaries:
      - "must not ask them to repeat an event they have already described"
      - "must not assume why the event occurred"
      - "must not assign another person's motive"
      - "must not merge several events"
      - "must not treat the user's interpretation as observable fact"
    if_unclear:
      - when: "a possible event has come up but they have not said it is where this began, so confirm it"
        reply:
          direct: "From what you've shared, <the event, in their words> seems to be what started these concerns. Is that right?"
          supportive: "You mentioned <the event, in their words>. Is that what started these feelings?"
          reflective: "You've mentioned <the event, in their words>. Is that where these concerns began?"
      - when: "they have named how they feel but not what happened, so ask for the event using their own word for the feeling"
        reply:
          direct: "What's been happening that's left you feeling <their word for it>?"
          supportive: "What's been happening that's left you feeling so <their word for it>?"
          reflective: "When you think about feeling <their word for it>, what's been happening that seems connected to it?"
      - when: "assumed motive - \"My manager embarrassed me because she wants me to fail.\""
        reply: "You believe she wants you to fail. What did she say or do?"
      - when: "event too broad - \"Everything went wrong.\""
        reply: "Several things went wrong. Which one do you want to look at?"
      - when: "what they describe is abuse, threats, coercion, harassment, discrimination, exploitation, or medical, financial, or legal danger"
        reply: "What happened sounds serious, and I am not going to ask you to see it differently. What would be most helpful to talk through?"
    confirm:
      direct: "From what you've shared, <the event, in their words> seems to be what started these concerns."
      supportive: "You mentioned <the event, in their words>. We can use that as our starting point."
      reflective: "You've mentioned <the event, in their words>. We can use that as a place to start."
    ask:
      direct: "What's been happening that's behind this?"
      supportive: "What's been happening that's left things feeling so hard?"
      reflective: "What's been happening that seems connected to it?"
  belief:
    title: "B: Belief"
    label: "B is for Belief."
    read_slots: [meaning]
    purpose: "Identify what the person began believing about the event, in their own words."
    listen_for: "The conclusion, prediction, expectation or judgment they attached to what happened."
    ready_when: "A belief they have expressed in their own language. If several appear, ask which one affected them most."
    boundaries:
      - "must not ask them to repeat or explain a belief they already gave"
      - "must not question whether the belief is true here, that belongs to Dispute"
      - "must not suggest another interpretation"
      - "must not interpret the belief beyond what they said"
    if_unclear:
      - when: "a feeling instead of a belief - \"I felt embarrassed.\""
        reply: "You felt embarrassed. What were you telling yourself at that point?"
      - when: "several beliefs at once"
        reply: "Several thoughts came at once. Which one affected you most?"
    confirm:
      direct: "It sounds like you've started to believe <what they began believing, in their words>."
      supportive: "I'm hearing that you've begun to think <what they began believing, in their words>."
      reflective: "It seems the way you've come to see it is <what they began believing, in their words>."
    ask:
      direct: "What did you start telling yourself about what was happening?"
      supportive: "Sometimes when things are difficult, we start drawing conclusions about ourselves or what's happening. What were you telling yourself about the situation?"
      reflective: "When that happened, what did you begin believing about yourself or the situation?"
  consequence:
    title: "C: Consequences"
    label: "C is for Consequences."
    read_slots: [impact, response]
    purpose: "Identify how believing that affected what they felt, did or avoided."
    listen_for: "A change in feeling or behaviour after they believed it, such as anxiety, withdrawing or avoiding."
    ready_when: "A feeling or a behaviour they identified themselves as following from the belief. Do not introduce a consequence they did not name."
    boundaries:
      - "must not ask about the same consequence again"
      - "must not name a consequence they did not identify"
      - "must not tell them how the belief must have affected them"
      - "must not introduce an interpretation they have not expressed"
    if_unclear:
      - when: "consequence unclear - \"It affected everything.\""
        reply: "It affected everything. What changed first?"
    confirm:
      direct: "It sounds like this has meant <how it has affected them, in their words>."
      supportive: "From what you've told me, this has meant <how it has affected them, in their words>."
      reflective: "It seems this has shown up for you as <how it has affected them, in their words>."
    ask:
      direct: "How did that thought affect how you felt or what you did?"
      supportive: "Our thoughts can affect how we feel and respond. How did that belief affect how you felt or what you did?"
      reflective: "When you believed that thought, how did it influence your feelings or the way you responded?"
  dispute:
    title: "D: Dispute"
    label: "D is for Dispute."
    purpose: "Help them look at what supports the belief and what may challenge it, and tell what they know from what they assume, without trying to prove the belief wrong."
    listen_for: "What they have observed, what supports the belief, what may suggest a different understanding, and what they do not yet know."
    ready_when: "The belief has been meaningfully looked at. They have said what supports it and what might challenge it, or have considered whether they have enough information to know it is true, or said they do not know once asked. A partial answer is enough. They do not have to disprove it."
    boundaries:
      - "must not argue with them or try to prove the belief wrong"
      - "must take information that supports the belief seriously and never answer it with a contradiction"
      - "must not say the other person trusts them, that nothing is wrong or that everything will be fine"
      - "must not invent evidence against the belief"
      - "must not assume another person's intention"
      - "must not reinterpret danger or mistreatment"
    if_unclear:
      - when: "nothing challenges the belief - \"Nothing suggests otherwise.\""
        reply: "Nothing comes to mind. Do you have enough information to know it is true?"
      - when: "what supports the belief has been said and what challenges it has not been asked"
        reply: "What might make you question the belief that <their belief, in their words>?"
      - when: "what they have said, across the conversation, shows they have no way to know what the other person actually thinks or decided, only guesses or an absence of feedback"
        reply: "From what you've said, <the gap, grounded in their words, such as \"your manager hasn't told you anything\">, this may not be something you can know for certain either way right now. What do you know for sure, and what are you assuming?"
    ask:
      direct: "What makes you believe this is true, and what makes you question it?"
      supportive: "Let's look at that belief together. What makes you think it's true? Is there anything that suggests otherwise?"
      reflective: "As you think about that belief, what seems to support it, and what might suggest a different explanation?"
  effective:
    title: "E: Effective New Belief"
    label: "E is for Effective New Belief."
    purpose: "Help them reach a more realistic and helpful understanding from what they have looked at, in their own words."
    listen_for: "A conclusion that separates what they know from what they assumed, such as not knowing why something happened and wanting more information."
    ready_when: "They have a more realistic and helpful understanding in their own words, or have looked at the belief and have no different one. If they do not reach a different belief, accept that and never make one up."
    boundaries:
      - "must not replace their conclusion with a more positive one"
      - "must not supply the new belief or tell them what to believe"
      - "must not offer reassurance they did not ask for"
      - "must not keep questioning once they have reached a clear understanding"
      - "must not force a positive conclusion or a change of feeling"
    ask:
      direct: "What's a more realistic and helpful way to think about what's happening?"
      supportive: "Now that you've looked at both sides, what's a more realistic and helpful way to think about what's happening?"
      reflective: "After considering both sides, what do you think would be a more accurate and helpful way to understand what happened?"
---

# ABCDE

The five steps: A, Activating Event. B, Belief. C, Consequences. D, Dispute. E, Effective New Belief.
It helps the person understand how their beliefs about a situation influence their feelings and
actions. It does not try to convince them their belief is wrong. It helps them examine it and reach
their own conclusion.

Source: the ABCDE framework document sent by the client on 2026-10-09 (Direct, Supportive and
Reflective cadences, and the implementation requirements). One MANI personality, three
communication styles, one ABCDE methodology, and a conversation that remembers what the person has
already said. Each letter and its name is said when the stage is reached. A stage the conversation
already answers is named, with what they said for it, and not asked again. It ends with the
shared body check-in, then Chat More and Go to Library.
