---
id: abcde
name: ABCDE
summary: "These questions help you see what happened, what you started believing about it, and how that belief has affected how you feel and what you do. Then you look at whether the belief is true and helpful, and decide what you would tell yourself instead."
display_order: 1
phases: [offering, activate, belief, consequence, dispute, effective]
activation:
  central_indication: >-
    The user links a specific event to a troubling belief about themselves, others, or the
    future, and to an emotional or behavioural reaction they would like to understand or change.
  # Specification only: nothing in mani/ reads appropriate_when or not_when.
  # The framework guide reads central_indication and contraindications.
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
    if_unclear:
      - when: "the user declines"
        reply: "You do not want to use a framework. What would be most helpful to talk through?"
    # The five steps, word for word from the client's sequence document (2026-11-18), minus the openers that answer
    # only Not sure ("No worries", "It's okay to be unsure").
    explain:
      directive: |-
        The ABCDE technique can really help. It breaks down thoughts into five steps:

        - A: Activating event (what happened)
        - B: Belief (what did your mind start saying)
        - C: Consequences (what did you feel or do)
        - D: Dispute (how can you challenge this belief)
        - E: Effective new belief (What kind of belief could you hold instead)

        Ready to dive into a real life situation?
      supportive: |-
        The ABCDE technique is a kind way to help break these thoughts down:

        - A: Activating event (what happened)
        - B: Belief (what did your mind start saying)
        - C: Consequences (what did you feel or do)
        - D: Dispute (how can you challenge this belief)
        - E: Effective new belief (What kind of belief could you hold instead)

        Would you like to try diving into a real life situation together?
      reflective: |-
        The ABCDE technique can help reflect on these thoughts by breaking them down:

        - A: Activating event (what happened)
        - B: Belief (what did your mind start saying)
        - C: Consequences (what did you feel or do)
        - D: Dispute (how can you challenge this belief)
        - E: Effective new belief (What kind of belief could you hold instead)

        Are you ready to dive into a real life situation?
  activate:
    title: "A: Activating Event"
    intro: "A is for Activating Event."
    purpose: "Identify the activating situation: what happened, or keeps happening, to them or around them that sets off the reaction. An ongoing pattern counts as much as a single event."
    # The parts of the experience this stage can open, each only when it adds something (muhammad, 2026-11-06).
    explore:
      - {id: what_happened, about: "what happened or keeps happening, in plain facts"}
      - {id: when_where, about: "when and where it happens, and how often"}
      - {id: who, about: "who was involved and what they said or did"}
    reach: "If their_case already describes what happened, report activate as known, in their words. A is the situation the confirmed core is about, which may be an ongoing pattern ('when you stop reaching out, days or weeks pass without hearing from anyone'), never simply the latest or most vivid event: a single event that made the pattern hurt more, such as a birthday, is at most a short example inside it, never the frame. Your text says back only that situation, in one sentence, then asks whether that's the situation they'd like to explore. No feeling and no interpretation: those come in B and C. Never ask for it again. The event is the observable trigger (what was said, done, or happened), never their belief about it or its consequences. If their_case has no concrete event, report activate as missing and ask what happened."
    listen_for: "What happened or has been happening; what they did; what others said or did; and whether they're describing what they observed or what they inferred."
    ready_when: "The situation is clear from what they've said, one event or an ongoing pattern, and it's described as something that happened or keeps happening rather than as their interpretation of it."
    # Optional follow-ups when the event is vague. Ask one at a time, only what's missing.
    question_bank:
      - "What happened?"
      - "What did you do?"
      - "What did others say or do?"
      - "When and where was this?"
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
  belief:
    title: "B: Belief"
    intro: "B is for Belief."
    # The part of Mani's picture that feeds this stage once it has passed: a new thought replaces its words.
    picture: thought
    purpose: "Identify, in their own words, what they started believing or telling themselves about the event: the interpretation that sits between what happened and how they reacted."
    # The parts of the experience this stage can open, each only when it adds something (muhammad, 2026-11-06).
    explore:
      - {id: thought, about: "what they told themselves about it"}
      - {id: about_self, about: "what it says to them about themselves"}
      - {id: about_future, about: "what they fear it means for what comes next"}
      - {id: rule, about: "the should or must behind it"}
    # Sent as next_stage_reach on the previous stage, where the reply assesses this stage for the walk.
    reach: "If several beliefs appear, report belief as partial, with each one in their words, so your text asks which one affected them most. A belief is what they concluded about themselves, others, or what it means for their future. It is never a judgement of whether how they were treated was real or fair. When their_case holds the core they confirmed, report belief as known with the core belief, in their words, so your text says it back and asks whether that's the belief underneath it. The belief is tied to the event but need not be the literal thought they had in that moment: it may be one they recognise looking back, so never ask whether it is exactly what they told themselves then. The first thing they told themselves counts only when it is the core: \"I've ruined everything\" on the way to \"I'm not capable of change\" is not it."
    listen_for: "The conclusion, prediction, rule, demand or judgement they attached to what happened: their self-talk. Unhelpful beliefs often sound absolute ('I always...', 'I'm worthless', 'I can't stand this', 'they should have...', 'it's a disaster'). Notice these for yourself, but never label them to the user."
    ready_when: "They've put one belief into words themselves. If several came up, they've chosen the one that affected them most."
    # Optional follow-ups when the belief is not yet in words. One at a time.
    question_bank:
      - "What were you telling yourself when it happened?"
      - "What did it seem to say about you?"
      - "What did you think it meant for what happens next?"
    if_unclear:
      - when: 'a feeling instead of a belief - "I felt embarrassed."'
        reply: "You felt embarrassed. What were you telling yourself at that point?"
      - when: "several beliefs at once"
        reply: "Several thoughts came at once. Which one affected you most?"
  consequence:
    title: "C: Consequences"
    carries_case: true
    intro: "C is for Consequences."
    # The part of Mani's picture that feeds this stage once it has passed: a new feeling is added to its words.
    picture: feelings
    purpose: "Identify how believing that affected what they felt and what they did or avoided, so they can see the link from event to belief to reaction."
    # The parts of the experience this stage can open, each only when it adds something (muhammad, 2026-11-06).
    explore:
      - {id: feelings, about: "what they feel when they believe it"}
      - {id: actions, about: "what they do, avoid or hold back from"}
      - {id: effects, about: "what it does to their work, health or the people close to them"}
      - {id: in_the_moment, about: "what goes through their mind in the moment it happens"}
      - {id: cost, about: "what it is costing them"}
    reach: "Report consequence as known where they've tied a feeling or an action to that belief. Where they described feelings or actions that may follow from it but never tied them to it, report it as partial, with those words, so your text says them back and asks whether that's how the belief has affected them. Where their_case already gives the feeling underneath, report consequence as known, in their words, so your text says it back and asks whether that's how the belief has affected them. Feelings and actions they described in the chat before the framework count: say them back together and ask only what else the belief affects, if anything, never for them again. Consequences are both what they feel and what they do: when only feelings are known, report it as partial and ask openly about the other side, such as 'how does it affect the way you are with them?', rather than asking them to confirm your reading. It is known only when both what they feel and what they do are known."
    listen_for: "Emotional consequences, such as anxiety, anger, low mood, guilt, shame, frustration or self-pity, and behavioural ones, such as withdrawing, avoiding, snapping at people, moping, drinking or giving up. Note whether the reaction is working for them or against them, but let them be the one to say so."
    ready_when: "They've named at least one feeling or behaviour themselves as following from the belief. Don't introduce a consequence they didn't name."
    # Optional follow-ups. One at a time.
    question_bank:
      - "What did you feel when you believed that?"
      - "What did you do, or stop doing, because of it?"
      - "How has it been working for you?"
    if_unclear:
      - when: 'consequence unclear - "It affected everything."'
        reply: "It affected everything. What changed first?"
      - when: "only a feeling or only an action has been named and the other may matter"
        reply: "You felt <their feeling, in their words>. Did it change anything you did?"
  dispute:
    title: "D: Dispute"
    carries_case: true
    intro: "D is for Dispute."
    purpose: "Help them examine the belief on two questions, whether it's accurate and whether it's helpful, and separate what they know from what they assume. The aim is to examine the belief, not to prove it wrong."
    # The parts of the experience this stage can open, each only when it adds something (muhammad, 2026-11-06).
    explore:
      - {id: supports, about: "what makes it feel true"}
      - {id: challenges, about: "what does not fit it"}
      - {id: known_vs_assumed, about: "what they know and what they assume"}
      - {id: friend_view, about: "what they would say to a friend in their place"}
      - {id: helpful, about: "whether holding it helps them or holds them back"}
    listen_for: "Keep three things apart: what happened (real, never questioned), their interpretation of it (understandable, never confirmed as fact), and what they assume without knowing. Then sort what they say into two piles and keep them apart. What supports the belief: something real they've noticed, such as a pattern in what they do (pulling back when things get serious is support, not a challenge). What challenges it: something that suggests it isn't completely true, such as having liked people and had chances. Also what they don't yet know, and whether holding the belief is helping them or holding them back."
    reach: "In said, keep the two piles apart: 'supports: <their words>; challenges: <their words>'. What they said in the chat before the framework counts for either pile: when the chat already holds what supports it, report dispute as partial with the gap 'challenge' from the start, so your text explores only the side not yet examined. If nothing has been said for it yet, report dispute as missing, so your text asks only what supports the belief: what makes it feel true. If they've said what supports it but nothing that challenges it, report it as partial with the gap 'challenge', so your text first acknowledges that what supports it is real, then asks only what makes them question whether it's completely true. Never count support as a challenge because it came as an explanation."
    ready_when: "The belief has been looked at properly. They've said what supports it and, separately, what might challenge it, or considered whether they have enough information to know it's true. Saying the belief comes from fear, worry or the pressure they are under, rather than from something they know or were told, is what challenges it, and answers D once they have been asked once for a concrete moment that challenges it. When their own words already hold both what supports it and what challenges it, D is answered too. They don't have to disprove it. Reflecting on whether the belief helps them is welcome but not required."
    # Optional angles, one per turn, only when they fit and haven't been covered. The three steps run in order, each
    # only if their answers haven't covered it: what makes it feel true, what makes them question it, another way to
    # look at it (the client's review, 2026-10-29).
    question_bank:
      - "What makes this belief feel true?"
      - "What makes you question whether it's completely true?"
      - "Is there another way to look at it?"
      - "What makes you think it's true? Is there anything that suggests otherwise?"
      - "Do you have enough information to know it's true?"
      - "How is holding on to that belief helping or getting in the way for you?"
      - "If a friend told you this about themselves, what would you say to them?"
    if_unclear:
      - id: information
        when: "they were asked what might challenge the belief and nothing at all came to mind, so ask only whether they have enough information to know it's true. Never when they said it comes from fear, worry or pressure: that answered D"
        reply: "Nothing comes to mind. Do you have enough information to know it is true?"
      - id: challenge
        # The stage whose words fill the reply's slot.
        slot: belief
        when: "they've said what supports the belief and haven't been asked what challenges it, so ask only what might make them question it"
        reply: "What might make you question the belief that <their belief, in their words>?"
  effective:
    title: "E: Effective New Belief"
    # Where the new view forms (the career chat, 2026-11-03): the core stays the belief the questions looked at, and the
    # stages before are never rewritten from what is said here (walk.new_view).
    new_view: true
    # Reached with only the path or a practice to ask, the new belief is asked first, in their words: what they said in
    # D is never the new belief (walk._reach; the "can't say no" chat, 2026-11-03).
    first_gap: belief
    carries_case: true
    intro: "E is for Effective New Belief."
    # E ends on the new belief, as the client's sequence document does (muhammad, 2026-11-18): how they feel comes next.
    purpose: "Ask them plainly what they would tell themselves now instead of the belief from B, keeping what supports it and what challenges it, in their own words."
    # The parts of the experience this stage can open, each only when it adds something (muhammad, 2026-11-06).
    explore:
      - {id: new_view, about: "what they would tell themselves now instead, in their words"}
    reach: "Report effective as known only where they've given, at this stage, what they would tell themselves now instead of the old belief, in their own words. What they said in D never counts as the new belief: a challenge to the old belief is not yet a new one. If only an action or intention has come, report it as partial with the gap 'belief', so your text asks what they would tell themselves about the belief now. A new view already forming in the chat before the framework counts: help them refine it rather than start again."
    listen_for: "A view that fits what they know and helps them, that separates what they know from what they assumed, usually more flexible than the original belief ('I made a mistake' rather than 'I'm a failure')."
    ready_when: "They've said, in their own words, what they would tell themselves now instead of the old belief, such as 'I don't have to give up my independence to let someone close', or picked one of Mani's suggested wordings as theirs. A plan, an action or a commitment for next time is not the new belief."
    # Optional follow-ups. One at a time, and only before they have a clear view.
    question_bank:
      - "Saying it that way, how do you feel now?"
      - "Next time something like this happens, what would you like to remind yourself?"
    if_unclear:
      - id: belief
        when: "they've said an action or intention but not yet what they would tell themselves instead"
        reply: "Knowing both sides of it, what would you tell yourself now about that thought?"
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
  helpful consequences, and irrational beliefs to harmful ones that often add to distress or
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
- The session ends with Continue chatting and Visit library (the body check-in is paused).

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
