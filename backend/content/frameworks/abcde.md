---
id: abcde
name: ABCDE
summary: "These questions help you see what happened, what you started believing about it, and how that belief has affected you, then look at whether it is true and find a more realistic and helpful way to see it."
display_order: 1
phases: [offering, activate, belief, consequence, dispute, effective]
# Used only when Mani's own confirmation of a stage cannot be: closes their words said back, B to E.
# A falls back to its own confirm line.
confirm_phrases: ["Is that right?", "Do we have this right?", "Did I get that right?", "Does that sound right?"]
activation:
  central_indication: >-
    The user connects a specific event to a troubling belief and emotional reaction.
  # Documentation of the specification: nothing in mani/ reads appropriate_when or not_when.
  # The prompt reads central_indication, distinctions and contraindications.
  appropriate_when:
    - "A situation, what the person believes it means, or how that belief is affecting them has come up"
    - "The person wants to understand their thinking rather than only talk"
    - "The issue has been identified well enough to say what ABCDE would help with"
  not_when:
    - "The user wants to continue chatting without a framework"
    - "The issue has not been identified"
    - "The user cannot take part in reflective questions"
    - "A safety concern requires the approved safety protocol"
  contraindications:
    - "The only thing left to examine would be whether abuse, threats, coercion, harassment, discrimination, exploitation, or medical, financial, or legal danger was real or as serious as it felt. What they came to believe about themselves after it may still be examined; the event itself is never questioned or reinterpreted as harmless"
  distinctions:
    continued_conversation: >-
      Continue chatting when the issue is unclear, the user wants to be heard, does not want a
      framework, or does not want to examine the belief.
stages:
  offering:
    purpose: "Offer ABCDE once they have said yes to Mani's check of its understanding, and receive explicit agreement before proceeding."
    boundaries:
      - "must not combine the three tones in one offer"
      - "the offer says what ABCDE would help them do, in their situation, then asks if they would like to try it"
    if_unclear:
      - when: "the user declines"
        reply: "You do not want to use a framework. What would be most helpful to talk through?"
    ask:
      supportive: "Would you like to try it?"
      reflective: "Would you like to try it?"
      directive: "Would you like to try it?"
    offer:
      directive: |-
        There's a framework called ABCDE that helps you identify the thoughts behind <their feeling from understanding as a short noun phrase that reads naturally after "the thoughts behind", such as "your frustration"; what is worrying them only when they named no feeling>, question whether they're true, and replace them with more realistic ones.
      supportive: |-
        <A short warm line in your own words about what they're facing and what they've decided, never about doubting themselves, such as "That's a lot to carry for you and your team, and it takes something to decide to speak up.">
        There's a framework called ABCDE that can help you understand the thoughts behind <their feeling from understanding as a short noun phrase that reads naturally after "the thoughts behind", such as "your frustration"; what is worrying them only when they named no feeling>, see whether those thoughts are really true, and find a more helpful way to think about what's happening.
      reflective: |-
        <A short line about how the way we interpret what is happening can make it feel harder, fitted to what they said, such as "Sometimes the way we interpret what's happening can make a difficult situation feel even harder.">
        There's a framework called ABCDE that helps you examine what you're telling yourself about <their feeling from understanding as a short noun phrase that reads naturally after "what you're telling yourself about", such as "your frustration"; what is worrying them only when they named no feeling>, understand how those thoughts affect you, and consider whether there's a more realistic way to see things.
    keep_chatting:
      directive: |-
        What's been happening that's making you feel like <what they said they are struggling with, in their words>?
      supportive: |-
        We can keep talking. What's been happening that's making things feel so <how they described it, in their words>?
      reflective: |-
        When you say <what they said about themselves or the situation, in their words>, what experiences have led you to see it that way?
    explain:
      directive: |-
        The ABCDE framework has five steps:

        1. A: Activating Event: What happened or what has been happening?
        2. B: Belief: What did you start telling yourself about it?
        3. C: Consequences: How did that thought affect how you felt or what you did?
        4. D: Dispute: What makes you believe it's true, and what makes you question it?
        5. E: Effective New Belief: What's a more realistic and helpful way to think about it?
      supportive: |-
        The ABCDE framework has five steps. Each one helps you understand what happened, what you started believing about it, and how those thoughts may be affecting you.

        1. A: Activating Event: What happened or what has been happening that brought up these feelings?
        2. B: Belief: What did you begin telling yourself about the situation?
        3. C: Consequences: How did that belief affect how you felt or what you did?
        4. D: Dispute: What makes you believe that thought is true, and is there anything that might suggest otherwise?
        5. E: Effective New Belief: What's a more realistic and helpful way to think about what happened?
      reflective: |-
        The ABCDE framework has five steps that help you examine how your interpretation of an experience influences what you believe and how you respond.

        1. A: Activating Event: What happened or what has been happening that started these concerns?
        2. B: Belief: What meaning did you give to what happened?
        3. C: Consequences: How did that belief influence your feelings or actions?
        4. D: Dispute: What supports your interpretation, and what might suggest a different understanding?
        5. E: Effective New Belief: What's a more accurate and helpful way to understand the situation?
  activate:
    title: "A: Activating Event"
    intro: "A is for Activating Event."
    purpose: "Identify the activating event from the conversation."
    reach: "Where their_case already gives the problem, report activate as known in their words. Your text says back what happened together with the underlying feeling they confirmed, in one sentence, then asks whether that is the situation to look at, never asking for it again. What happened is the objective trigger, never their belief about it or its consequences. Where their_case holds no concrete happening, report activate as missing and ask what happened."
    listen_for: "What happened or has been happening, what was said or done, and whether the person is describing what they observed or what they inferred."
    ready_when: "The event is clear from what they have said."
    boundaries:
      - "must not ask them to repeat an event they have already described"
      - "must not assume why the event occurred"
      - "must not assign another person's motive"
      - "must not merge several events"
      - "must not treat the user's interpretation as observable fact"
    confirm:
      directive: "From what you've shared, <the event, in their words> seems to be what started these concerns. Is that right?"
      supportive: "You mentioned <the event, in their words>. Is that what started these feelings?"
      reflective: "You've mentioned <the event, in their words>. Is that where these concerns began?"
    missing:
      directive: "What's been happening that's left you feeling <their word for it>?"
      supportive: "What's been happening that's left you feeling so <their word for it>?"
      reflective: "When you think about feeling <their word for it>, what's been happening that seems connected to it?"
    if_unclear:
      - when: "assumed motive - \"My manager embarrassed me because she wants me to fail.\""
        reply: "You believe she wants you to fail. What did she say or do?"
      - when: "event too broad - \"Everything went wrong.\""
        reply: "Several things went wrong. Which one do you want to look at?"
      - when: "what they describe is abuse, threats, coercion, harassment, discrimination, exploitation, or medical, financial, or legal danger"
        reply: "What happened sounds serious, and I am not going to ask you to see it differently. What would be most helpful to talk through?"
    ask:
      directive: "What's been happening that's behind this?"
      supportive: "What's been happening that's left things feeling so hard?"
      reflective: "What's been happening that seems connected to it?"
  belief:
    title: "B: Belief"
    intro: "B is for Belief."
    purpose: "Identify what the person began believing about the event, in their own words."
    # Sent as next_stage_reach on the stage before, where the reply judges this stage for the walk.
    reach: "Where several beliefs appear, report belief as partial with each in their words, so your text asks which affected them most. A belief is what they concluded about themselves or what it means for them, never whether how they were treated was real or fair. Where their_case already gives what it comes down to for them, report belief as known in their words, so your text says it back and asks whether that is what they started telling themselves."
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
    ask:
      directive: "What did you start telling yourself about what was happening?"
      supportive: "Sometimes when things are difficult, we start drawing conclusions about ourselves or what's happening. What were you telling yourself about the situation?"
      reflective: "When that happened, what did you begin believing about yourself or the situation?"
  consequence:
    title: "C: Consequences"
    carries_case: true
    intro: "C is for Consequences."
    purpose: "Identify how believing that affected what they felt, did or avoided."
    reach: "Report consequence as known where they tied a feeling or an action to that belief. Where they described feelings or actions that may follow from it but never tied them, report it as partial with those words, so your text says them back and asks whether that is how the belief has affected them. Where their_case already gives the feeling underneath, report consequence as known in their words, so your text says it back and asks whether that is how the belief has affected them."
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
    ask:
      directive: "How did that thought affect how you felt or what you did?"
      supportive: "Our thoughts can affect how we feel and respond. How did that belief affect how you felt or what you did?"
      reflective: "When you believed that thought, how did it influence your feelings or the way you responded?"
  dispute:
    title: "D: Dispute"
    carries_case: true
    intro: "D is for Dispute."
    purpose: "Help them look at what supports the belief and what may challenge it, and tell what they know from what they assume, without trying to prove the belief wrong."
    listen_for: "What they have observed, what supports the belief, what may suggest a different understanding, and what they do not yet know."
    reach: "Report dispute as missing where nothing has been said for it, so your text asks only what supports the belief. Where what supports it is said and what might challenge it was never asked, report it as partial with that support in their words and the gap challenge, so your text asks only what might challenge it."
    ready_when: "The belief has been meaningfully looked at. They have said what supports it and what might challenge it, or have considered whether they have enough information to know it is true. They do not have to disprove it."
    boundaries:
      - "must not argue with them, lead them to a conclusion or try to prove the belief wrong"
      - "must take information that supports the belief seriously and never answer it with a contradiction"
      - "must not say the other person trusts them, that nothing is wrong or that everything will be fine"
      - "must not invent evidence against the belief or assume another person's intention"
      - "must not reinterpret danger or mistreatment"
      - "each question asks one part, in their belief and the feeling underneath, and never says what it is for"
    if_unclear:
      - id: information
        when: "what might challenge the belief was asked and nothing came to mind, so ask only whether they have enough information to know it is true"
        reply: "Nothing comes to mind. Do you have enough information to know it is true?"
      - id: challenge
        # The stage whose words fill the reply's slot.
        slot: belief
        when: "what supports the belief has been said and what challenges it has not been asked, so ask only what might make them question it"
        reply: "What might make you question the belief that <their belief, in their words>?"
    ask:
      directive: "What makes you believe this is true, and what makes you question it?"
      supportive: "Let's look at that belief together. What makes you think it's true? Is there anything that suggests otherwise?"
      reflective: "As you think about that belief, what seems to support it, and what might suggest a different explanation?"
  effective:
    title: "E: Effective New Belief"
    carries_case: true
    intro: "E is for Effective New Belief."
    purpose: "Help them reach a more realistic and helpful way to see it from what they have looked at, and one clear path they will focus on, in their own words."
    reach: "Report effective as known only where they gave both a more realistic way to see it and one path, such as raising it with someone. Where only the new view came, report it as partial with their words and the gap path, so your text asks what one thing they could focus on."
    listen_for: "A more realistic and helpful view that separates what they know from what they assumed, and the one thing they will focus on from here."
    ready_when: "They have said a more realistic and helpful way to see it and one clear path they will focus on, in their own words, or picked one of Mani's possibilities as theirs. A plan or an action counts as the path."
    boundaries:
      - "when they are unsure, may offer two or three loose possibilities for the view or the path, never as advice and never deciding for them"
      - "must not offer reassurance they did not ask for"
      - "must not reinterpret danger or mistreatment"
      - "must not keep questioning once they have a clear view and a path"
    if_unclear:
      - id: path
        when: "a more realistic way to see it has been said and the one thing they will focus on has not been asked"
        reply: "What is one thing you could focus on from here?"
    ask:
      directive: "What's a more realistic and helpful way to think about what's happening?"
      supportive: "Now that you've looked at both sides, what's a more realistic and helpful way to think about what's happening?"
      reflective: "After considering both sides, what do you think would be a more accurate and helpful way to understand what happened?"
---

# ABCDE

The five steps: A, Activating Event. B, Belief. C, Consequences. D, Dispute. E, Effective New Belief.
It helps the person understand how their beliefs about a situation influence their feelings and
actions. It does not try to convince them their belief is wrong. It helps them examine it and reach
their own conclusion.

Source: the ABCDE framework document sent by the client on 2026-10-09 (Direct, Supportive and
Reflective cadences, and the implementation requirements). When it fits comes from the client's
Framework Selection Cheat Sheet of 2026-10-13. One MANI personality, three
communication styles, one ABCDE methodology, and a conversation that remembers what the person has
already said. Each letter and its name is said when the stage is reached. A stage the conversation
already answers is said back with what they said for it and confirmed once, never asked again. It
ends with the shared body check-in, then Chat More and Go to Library.
