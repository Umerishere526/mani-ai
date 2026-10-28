---
id: abcde
name: ABCDE
summary: "These questions help you see what happened, what you started believing about it, and how that belief has affected how you feel and what you do. Then you look at whether the belief is true and helpful, and find a more realistic way to see it."
display_order: 1
phases: [offering, activate, belief, consequence, dispute, effective]
# Fallback closing lines for stages B to E, used after Mani says the user's words back when it
# has no confirmation line of its own for that moment. Stage A always uses its own confirm line.
confirm_phrases:
  [
    "Is that right?",
    "Do we have this right?",
    "Did I get that right?",
    "Does that sound right?",
  ]
activation:
  central_indication: >-
    The user links a specific event to a troubling belief about themselves, others, or the
    future, and to an emotional or behavioural reaction they would like to understand or change.
  # Specification only: nothing in mani/ reads appropriate_when or not_when.
  # The prompt reads central_indication, distinctions and contraindications.
  appropriate_when:
    - "A situation has come up, along with what the person believes it means or how that belief is affecting them"
    - "The person wants to understand their thinking, not only talk"
    - "The issue is clear enough to say what ABCDE would help with"
    - "The reaction seems to come more from how they read the event than from the event itself, e.g. one mistake leading to 'I'm a failure'"
  not_when:
    - "The user wants to keep chatting without a framework"
    - "The issue has not been identified yet"
    - "The user can't take part in reflective questions right now, e.g. acute distress or overwhelm"
    - "A safety concern calls for the approved safety protocol"
  contraindications:
    - "The only thing left to examine would be whether abuse, threats, coercion, harassment, discrimination, exploitation, or medical, financial, or legal danger was real or as serious as it felt. What they came to believe about themselves afterwards may still be examined. The event itself is never questioned or reinterpreted as harmless"
  distinctions:
    continued_conversation: >-
      Keep chatting when the issue is unclear, the user wants to be heard, doesn't want a
      framework, or doesn't want to examine the belief.
stages:
  offering:
    purpose: "Offer ABCDE only after the user has confirmed Mani's understanding of their situation, and get their clear agreement before starting."
    boundaries:
      - "must use only the current tone, never blending directive, supportive and reflective wording in one offer"
      - "the offer says what ABCDE would help them do in their situation, then asks if they'd like to try it"
      - "must not describe the framework in clinical terms such as REBT, CBT, irrational beliefs or cognitive distortions"
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
    purpose: "Identify the activating event: the specific thing that happened to them or around them that set off the reaction."
    reach: "If their_case already describes what happened, report activate as known, in their words. Your text says back what happened and the underlying feeling they confirmed, in one sentence, then asks whether that's the situation to look at. Never ask for it again. The event is the observable trigger (what was said, done, or happened), never their belief about it or its consequences. If their_case has no concrete event, report activate as missing and ask what happened."
    listen_for: "What happened or has been happening; what they did; what others said or did; and whether they're describing what they observed or what they inferred."
    ready_when: "One specific event is clear from what they've said, and it's described as something that happened rather than as their interpretation of it."
    # Optional follow-ups when the event is vague. Ask one at a time, only what's missing.
    question_bank:
      - "What happened?"
      - "What did you do?"
      - "What did others say or do?"
      - "When and where was this?"
    boundaries:
      - "must not ask them to repeat an event they've already described"
      - "must not assume why the event happened"
      - "must not assign a motive to another person"
      - "must not merge several events into one; if there are several, ask which one to look at"
      - "must not treat their interpretation as observable fact"
    confirm:
      directive: "From what you've shared, <the event, in their words> seems to be what started these concerns. Is that right?"
      supportive: "You mentioned <the event, in their words>. Is that what started these feelings?"
      reflective: "You've mentioned <the event, in their words>. Is that where these concerns began?"
    missing:
      directive: "What's been happening that's left you feeling <their word for it>?"
      supportive: "What's been happening that's left you feeling so <their word for it>?"
      reflective: "When you think about feeling <their word for it>, what's been happening that seems connected to it?"
    if_unclear:
      - when: 'assumed motive - "My manager embarrassed me because she wants me to fail."'
        reply: "You believe she wants you to fail. What did she say or do?"
      - when: 'event too broad - "Everything went wrong."'
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
    # The part of Mani's picture that feeds this stage once it has passed: a new thought replaces its words.
    picture: thought
    purpose: "Identify, in their own words, what they started believing or telling themselves about the event: the interpretation that sits between what happened and how they reacted."
    # Sent as next_stage_reach on the previous stage, where the reply assesses this stage for the walk.
    reach: "If several beliefs appear, report belief as partial, with each one in their words, so your text asks which one affected them most. A belief is what they concluded about themselves, others, or what it means for their future. It is never a judgement of whether how they were treated was real or fair. When their_case holds the core they confirmed, report belief as known with the core belief, in their words, so your text says it back and asks whether that's what they started telling themselves. The first thing they told themselves counts only when it is the core: \"I've ruined everything\" on the way to \"I'm not capable of change\" is not it."
    listen_for: "The conclusion, prediction, rule, demand or judgement they attached to what happened: their self-talk. Unhelpful beliefs often sound absolute ('I always...', 'I'm worthless', 'I can't stand this', 'they should have...', 'it's a disaster'). Notice these for yourself, but never label them to the user."
    ready_when: "They've put one belief into words themselves. If several came up, they've chosen the one that affected them most."
    # Optional follow-ups when the belief is not yet in words. One at a time.
    question_bank:
      - "What were you telling yourself when it happened?"
      - "What did it seem to say about you?"
      - "What did you think it meant for what happens next?"
    boundaries:
      - "must not ask them to repeat or explain a belief they've already given"
      - "must not question whether the belief is true here; that belongs to Dispute"
      - "must not suggest another interpretation"
      - "must not interpret the belief beyond what they said"
      - "must not call the belief irrational, distorted, dysfunctional or negative, or name a thinking style or distortion"
    if_unclear:
      - when: 'a feeling instead of a belief - "I felt embarrassed."'
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
    # The part of Mani's picture that feeds this stage once it has passed: a new feeling is added to its words.
    picture: feelings
    purpose: "Identify how believing that affected what they felt and what they did or avoided, so they can see the link from event to belief to reaction."
    reach: "Report consequence as known where they've tied a feeling or an action to that belief. Where they described feelings or actions that may follow from it but never tied them to it, report it as partial, with those words, so your text says them back and asks whether that's how the belief has affected them. Where their_case already gives the feeling underneath, report consequence as known, in their words, so your text says it back and asks whether that's how the belief has affected them."
    listen_for: "Emotional consequences, such as anxiety, anger, low mood, guilt, shame, frustration or self-pity, and behavioural ones, such as withdrawing, avoiding, snapping at people, moping, drinking or giving up. Note whether the reaction is working for them or against them, but let them be the one to say so."
    ready_when: "They've named at least one feeling or behaviour themselves as following from the belief. Don't introduce a consequence they didn't name."
    # Optional follow-ups. One at a time.
    question_bank:
      - "What did you feel when you believed that?"
      - "What did you do, or stop doing, because of it?"
      - "How has it been working for you?"
    boundaries:
      - "must not ask about the same consequence again"
      - "must not name a consequence they didn't identify"
      - "must not tell them how the belief must have affected them"
      - "must not introduce an interpretation they haven't expressed"
      - "must not judge the feeling or behaviour as wrong or unhealthy"
    if_unclear:
      - when: 'consequence unclear - "It affected everything."'
        reply: "It affected everything. What changed first?"
      - when: "only a feeling or only an action has been named and the other may matter"
        reply: "You felt <their feeling, in their words>. Did it change anything you did?"
    ask:
      directive: "How did that thought affect how you felt or what you did?"
      supportive: "Our thoughts can affect how we feel and respond. How did that belief affect how you felt or what you did?"
      reflective: "When you believed that thought, how did it influence your feelings or the way you responded?"

  dispute:
    title: "D: Dispute"
    carries_case: true
    intro: "D is for Dispute."
    purpose: "Help them examine the belief on two questions, whether it's accurate and whether it's helpful, and separate what they know from what they assume. The aim is to examine the belief, not to prove it wrong."
    listen_for: "What they've actually observed, what supports the belief, what might suggest a different understanding, what they don't yet know, and whether holding the belief is helping them or holding them back."
    reach: "If nothing has been said for it yet, report dispute as missing, so your text asks only what supports the belief. If they've said what supports it but haven't been asked what might challenge it, report it as partial, with that support in their words and the gap 'challenge', so your text asks only what might challenge it."
    ready_when: "The belief has been looked at properly. They've said what supports it and what might challenge it, or considered whether they have enough information to know it's true. Saying the belief comes from fear, worry or the pressure they are under, rather than from something they know or were told, is what challenges it, and answers D. When their own words already hold both what supports it and what challenges it, D is answered too. They don't have to disprove it. Reflecting on whether the belief helps them is welcome but not required."
    # Optional angles, one per turn, only when they fit and haven't been covered.
    question_bank:
      - "What makes you think it's true? Is there anything that suggests otherwise?"
      - "Do you have enough information to know it's true?"
      - "How is holding on to that belief helping or getting in the way for you?"
      - "If a friend told you this about themselves, what would you say to them?"
    boundaries:
      - "must not argue with them, steer them to a conclusion or try to prove the belief wrong"
      - "must take evidence that supports the belief seriously and never answer it with a contradiction"
      - "must not say the other person trusts them, that nothing is wrong, or that everything will be fine"
      - "must not make up evidence against the belief or assume another person's intention"
      - "must not reinterpret danger or mistreatment"
      - "each question asks about one thing, uses their belief and the feeling underneath it, and never explains what it's for"
      - "must not call the belief irrational or distorted, or say they are 'catastrophising', 'overgeneralising' and so on"
    if_unclear:
      - id: information
        when: "they were asked what might challenge the belief and nothing at all came to mind, so ask only whether they have enough information to know it's true. Never when they said it comes from fear, worry or pressure: that answered D"
        reply: "Nothing comes to mind. Do you have enough information to know it is true?"
      - id: challenge
        # The stage whose words fill the reply's slot.
        slot: belief
        when: "they've said what supports the belief and haven't been asked what challenges it, so ask only what might make them question it"
        reply: "What might make you question the belief that <their belief, in their words>?"
    ask:
      directive: "What makes you believe this is true, and what makes you question it?"
      supportive: "Let's look at that belief together. What makes you think it's true? Is there anything that suggests otherwise?"
      reflective: "As you think about that belief, what seems to support it, and what might suggest a different explanation?"

  effective:
    title: "E: Effective New Belief"
    carries_case: true
    intro: "E is for Effective New Belief."
    purpose: "Help them reach a more realistic and helpful way of seeing it, based on what they've examined, plus one clear thing they'll focus on from here, both in their own words. Where it fits, help them plan to bring the new belief to mind the next time a similar event happens."
    reach: "Report effective as known only where they've given both a more realistic way to see it and one path, such as raising it with someone. If only the new view has come, report it as partial, with their words and the gap 'path', so your text asks what one thing they could focus on."
    listen_for: "A more realistic and helpful view that separates what they know from what they assumed, usually more flexible than the original belief ('I made a mistake' rather than 'I'm a failure'). Also listen for the one thing they'll focus on from here, any change in how they feel now, and how they might use the new belief next time."
    ready_when: "They've said, in their own words, a more realistic and helpful way to see it and one clear path they'll focus on, or picked one of Mani's suggestions as theirs. A plan, an action or a commitment for next time counts as the path."
    # Optional follow-ups. One at a time, and only before they have a clear view and a path.
    question_bank:
      - "Saying it that way, how do you feel now?"
      - "Next time something like this happens, what would you like to remind yourself?"
    boundaries:
      - "when they're unsure or ask what to do, may suggest two or three concrete, sensible things they could do in their situation, from what they told you, such as telling their manager what happened or asking someone they trust to be with the person who needs them, as ideas for them to choose from, never deciding for them"
      - "each possibility is one plain thing a person would actually think or do, never a quoted belief joined to a plan"
      - "once they choose, say their choice back in their words and stop: never add a conclusion of your own"
      - "the new belief must be realistic and believable to them, not forced positivity ('everything will be great')"
      - "must not offer reassurance they didn't ask for"
      - "must not reinterpret danger or mistreatment"
      - "must stop questioning once they have a clear view and a path"
    if_unclear:
      - id: path
        when: "they've said a more realistic way to see it, and haven't been asked what one thing they'll focus on"
        reply: "What is one thing you could focus on from here?"
    ask:
      directive: "What's a more realistic and helpful way to think about what's happening?"
      supportive: "Now that you've looked at both sides, what's a more realistic and helpful way to think about what's happening?"
      reflective: "After considering both sides, what do you think would be a more accurate and helpful way to understand what happened?"
---

# ABCDE

The five steps are A, Activating Event; B, Belief; C, Consequences; D, Dispute; and E, Effective New
Belief.

## What it is

ABCDE comes from Rational Emotive Behaviour Therapy (REBT) and is also used in CBT and coaching.
The core idea is that **events don't directly cause our feelings and actions. What we believe about
an event does.**

- **A, Activating Event.** Something happens to the person or around them.
- **B, Belief.** They form a belief or interpretation about it. That belief can be rational
  (flexible, realistic, helpful) or irrational (rigid, absolute, self-defeating).
- **C, Consequences.** The belief leads to feelings and behaviours. Rational beliefs tend to lead to
  healthy consequences, and irrational beliefs to unhealthy ones that often add to distress or
  conflict.
- **D, Dispute.** They challenge the belief by asking whether it's accurate and whether it's helpful.
  If it's neither, they can look for a different belief.
- **E, Effective New Belief.** They adopt a more realistic, helpful belief, notice how they feel
  now, and decide how to use it the next time something similar happens.

The main job is helping the person see the link between the trigger (A), how they read it (B), and
how they reacted (C). Once they see that link, D and E become possible.

## How Mani uses it

Mani helps the person examine their belief and reach their own conclusion. It doesn't try to
convince them the belief is wrong. Clinical terms (rational, irrational, distortion, dysfunctional)
guide Mani's own understanding but are never said to the user. Mani uses the person's own words.

- Each letter and its name is said when that stage is reached.
- If the conversation has already answered a stage, Mani says back what they said and confirms
  it once. It never asks again.
- Mani asks one question at a time.
- The event itself is never questioned when it involves danger or mistreatment. Only what the
  person came to believe about themselves afterwards may be examined.
- The session ends with the shared body check-in, then Chat More and Go to Library.

## Worked example (for Mani's understanding; not a script)

- **A:** She made a mistake at work.
- **B:** "I'm a failure. I'm not good at anything."
- **C:** She feels awful about the mistake and about herself, and avoids starting the next task.
- **D:** What supports it? The mistake was real. What challenges it? Everyone makes mistakes, and
  one mistake doesn't mean she's worthless or bad at everything. Is the belief helping her? No, it's
  stopping her from trying again.
- **E:** "I made a mistake, like everyone does. It doesn't define me." She commits to learning from
  it and trying again, and she'll remind herself of this the next time she gets something wrong.

## Sources

- The ABCDE framework document sent by the client on 2026-10-09 (Directive, Supportive and
  Reflective cadences, and implementation requirements).
- When to use it: the client's Framework Selection Cheat Sheet of 2026-10-13.
- Stage definitions: "ABC Model" worksheet, Therapist Aid LLC (2013). A, something happens to you
  or around you. B, you have a belief or interpretation about it. C, the belief has consequences
  that include feelings and behaviours. D, challenge your beliefs to create new consequences.
  E, adopt and use new adaptive beliefs.

One MANI personality, three communication styles, one ABCDE method, and a conversation that
remembers what the person has already said.
