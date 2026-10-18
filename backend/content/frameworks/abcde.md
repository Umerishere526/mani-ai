---
id: abcde
name: ABCDE
summary: "These questions help you see what happened, what you started believing about it, and how that belief has affected you, then look at whether it is true and find a more realistic and helpful way to see it."
display_order: 1
phases: [offering, activate, belief, consequence, dispute, effective]
# Used only when Mani's own reading of a stage cannot be: closes their words said back.
# A stage with a confirm line uses it instead.
confirm_phrases: ["Is that right?", "Do we have this right?", "Did I get that right?", "Does that sound right?"]
activation:
  central_indication: >-
    The user connects a specific event to a troubling belief and emotional reaction.
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
    listen_for: "What happened, what was said or done, and whether they observed it or inferred it."
    when_stuck: "When they can't say what happened, ask about one recent moment it came up, built on what they already described."
    boundaries:
      - "must not assume why the event occurred"
      - "must not assign another person's motive"
      - "must not merge several events"
      - "must not treat the user's interpretation as observable fact"
    parts:
      - id: event
        is: "what happened, as they observed it, in the one situation they want to look at"
        enough: "one event or situation in their words. A broad \"everything went wrong\" is narrowed to the one they want to look at. What they infer about someone's motive is not the event. The situation is theirs: what they want to change, such as a feeling, points to the moments that bring it on"
        from: understanding.event
        ask:
          directive: "What's been happening that's left you feeling <understanding.feeling>?"
          supportive: "What's been happening that's left you feeling so <understanding.feeling>?"
          reflective: "When you think about feeling <understanding.feeling>, what's been happening that seems connected to it?"
        stop_pushing: "they described it twice, even loosely: take it as the event"
    confirm:
      directive: "From what you've shared, <the event, in their words> seems to be what started these concerns. Is that right?"
      supportive: "You mentioned <the event, in their words>. Is that what started these feelings?"
      reflective: "You've mentioned <the event, in their words>. Is that where these concerns began?"
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
    listen_for: "The conclusion, prediction, expectation or judgment they attached to what happened."
    when_stuck: "When they can't say what they told themselves, ask what went through their mind at that moment, or what they were afraid it meant. Build on the event and the feeling they already gave, never a belief of your own."
    boundaries:
      - "must not ask them to repeat or explain a belief they already gave"
      - "must not question whether the belief is true here, that belongs to Dispute"
      - "must not suggest another interpretation"
      - "must not interpret the belief beyond what they said"
    parts:
      - id: belief
        is: "what they concluded about themselves or what it means for them: the thought, prediction, expectation or judgment they attached to what happened"
        enough: "a thought in their own words, even a rough one. What they did because of it is not the belief, it belongs to consequence. Where several appear, ask which one hits hardest, the one tied to the strongest feeling. Never whether how they were treated was real or fair. A prediction of real harm from someone with more power, such as being targeted for speaking up, is a real risk, never the belief to question: ask what it means for them, such as that they can't protect themselves or just have to put up with it, and never supply it"
        stop_pushing: "they have said they can't put it into words twice: take the closest thing they said, give it back as a possibility, and let them correct it"
      - id: belief_type
        is: "the kind of thought it is: a must or a should, all or nothing, I can't stand it, or putting themselves down"
        enough: "your own reading from what they said, reported as inferred. Never asked about, and never named to them as a label"
        required: false
    reflect: "how true the thought feels to them right now: a little, a lot, or completely"
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
    intro: "C is for Consequences."
    purpose: "Identify how believing that affected what they felt and what they did or avoided."
    listen_for: "A change in feeling or behaviour after they believed it, such as anxiety, withdrawing or avoiding."
    when_stuck: "When they don't know how it affected them, ask about the last time they believed it: what they felt, then what they did next. Build on what they already said, never a consequence of your own."
    boundaries:
      - "must not ask about the same consequence again"
      - "must not name a consequence they did not identify"
      - "must not tell them how the belief must have affected them"
      - "must not introduce an interpretation they have not expressed"
    parts:
      - id: felt
        is: "how believing the thought left them feeling, tied by them to the belief"
        enough: "a feeling they link to the thought. The feeling they opened the conversation with is only a possibility for them to confirm"
        from: understanding.feeling
        ask: "And when you believe <belief>, how does that leave you feeling?"
        stop_pushing: "they have no word for it after one try: accept a plain description, or that it is hard to name"
      - id: did
        is: "what they did, stopped doing or avoided once they believed it"
        enough: "an action or an avoidance, in their words"
        ask: "What do you do, or stop doing, once you believe <belief>?"
        stop_pushing: "they say nothing changed: accept it"
    reflect: "what believing the thought costs them"
    if_unclear:
      - when: "consequence unclear - \"It affected everything.\""
        reply: "It affected everything. What changed first?"
    ask:
      directive: "How did that thought affect how you felt or what you did?"
      supportive: "Our thoughts can affect how we feel and respond. How did that belief affect how you felt or what you did?"
      reflective: "When you believed that thought, how did it influence your feelings or the way you responded?"
  dispute:
    title: "D: Dispute"
    intro: "D is for Dispute."
    purpose: "Help them look at the belief from B: what supports it, what may challenge it, and whether the conclusion they draw from it follows. Tell what they know from what they assume, without trying to prove the belief wrong."
    listen_for: "What they have observed, what supports the belief, what may suggest a different understanding, what they do not yet know, and where the belief is joined to a conclusion."
    when_stuck: "When nothing comes to mind, help them look, from their own words. Offer one distinction: between the belief and the conclusion they draw from it, or between what they know and what they assume, or where believing it gets them. Ask which is closer to what they tell themselves. Start with the kind of thought belief_type names."
    boundaries:
      - "must not argue with them or try to prove the belief wrong"
      - "must take information that supports the belief seriously and never answer it with a contradiction"
      - "must not say the other person trusts them, that nothing is wrong or that everything will be fine"
      - "must not invent evidence against the belief"
      - "must not assume another person's intention"
      - "must not reinterpret danger or mistreatment"
    parts:
      - id: evidence
        is: "what supports the belief and what, if anything, suggests a different explanation"
        enough: "both looked at, with what supports it taken seriously. Nothing coming to mind for the other side is an answer once one distinction has been offered"
        ask: "As you think about <belief>, what seems to support it, and what might suggest a different explanation?"
        stop_pushing: "nothing comes to mind even after you offered one distinction in their words: keep what supports it, and nothing yet for the other side"
      - id: logic
        is: "whether the conclusion follows from the thought: where the belief is joined to what they conclude or do because of it, the two pulled apart in their words"
        enough: "they have said whether one has to lead to the other, or that they can't tell. Not knowing for sure is not enough on its own, and they do not have to disprove it"
        ask: "Looking at <belief> and what you do because of it, does one really have to lead to the other?"
        stop_pushing: "they say they can't tell after one try and one distinction: accept it and give back that the two feel joined"
      - id: usefulness
        is: "where believing it tends to get them"
        required: false
        ask: "Where does believing <belief> tend to get you?"
        stop_pushing: "asked once, never again"
    reflect: "what stands out to them now that they have looked at it"
    if_unclear:
      - when: "nothing challenges the belief - \"Nothing suggests otherwise.\""
        reply: "Nothing comes to mind yet, and that's fine. <one distinction from when_stuck, in their words, as a question>"
    ask:
      directive: "What makes you believe this is true, and what makes you question it?"
      supportive: "Let's look at that belief together. What makes you think it's true? Is there anything that suggests otherwise?"
      reflective: "As you think about that belief, what seems to support it, and what might suggest a different explanation?"
  effective:
    title: "E: Effective New Belief"
    intro: "E is for Effective New Belief."
    purpose: "Help them reach a more realistic and helpful understanding of the belief from B, from what they have looked at, in their own words."
    listen_for: "A conclusion that separates what they know from what they assumed, such as not knowing why something happened and wanting more information, or one that allows for action alongside the difficulty."
    when_stuck: "Put side by side, in their words, the belief and what they found when they looked at it in dispute, and ask what they would say to themselves now. Never supply the belief, never force a positive one."
    boundaries:
      - "must not replace their conclusion with a more positive one"
      - "must not supply the new belief or tell them what to believe"
      - "must not offer reassurance they did not ask for"
      - "must not keep questioning once they have reached a clear understanding"
      - "must not force a positive conclusion or a change of feeling"
    parts:
      - id: new_belief
        is: "a more realistic and helpful way to understand it, in their own words, from what they looked at"
        enough: "a thought that separates what they know from what they assumed, or that allows for action alongside the difficulty. A plan or an action is not a new belief: acknowledge it and ask for the way of seeing it. One they reject, or not sure, is not reached: stay and help. Never made up"
        stop_pushing: "they offered none after you put the belief and what they found side by side: accept that, say so plainly, and let your reading carry where they are"
      - id: next_step
        is: "one small thing they could do, if they name one"
        required: false
        stop_pushing: "they don't want one: never pressed"
    reflect: "what they take with them from this"
    confirm: "So the thought would now be: <the new belief, in their words>. Does that fit for you?"
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
already said. Each reply inside a stage opens with that stage's letter line. A stage's parts the
conversation already answers are read back and confirmed once, never asked again, and a stage ends
on their yes and what they take from it. It ends with the shared body check-in, then the closing
choices.
