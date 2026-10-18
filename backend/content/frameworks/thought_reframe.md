---
id: thought_reframe
name: Thought Reframe
summary: "These questions help you examine a troubling thought and consider a more balanced perspective. By the end, you will be able to see the situation differently."
display_order: 2
phases: [offering, thought, significance, facts, alternative, reframe]
confirm_phrases: ["Is that right?", "Do we have this right?", "Did I get that right?", "Does that sound right?"]
activation:
  central_indication: >-
    The user struggles with one persistent, painful thought that needs a more balanced interpretation.
  contraindications:
    - "The thought keeps returning as a repeated request to check whether it is true, especially about harm, contamination, or identity - in OCD this checking is the compulsion, and answering it again only feeds the loop it is trying to escape"
    - "The only thought left to examine would be whether abuse, threats, coercion, harassment, discrimination, exploitation, or medical, financial, or legal danger was real or as serious as it felt. A thought they formed about themselves after it may still be examined; the event itself is never questioned or reinterpreted as harmless"
    - "The painful statement is itself an established fact - a relationship ended, a person said they want to end the friendship - the fact is not reframed, only a related thought about themselves or their future"
  distinctions:
    abcde: >-
      ABCDE when a specific event or someone's behaviour is at the centre, and what they came to
      believe about it and what it led to need separating. Reframe when one sweeping thought about
      themselves, other people or their future keeps coming back, more than any one event, and the
      event behind it is vague or long past. Only when both fit equally, ABCDE takes priority.
    continued_conversation: >-
      Continue chatting when the thought is unclear, the user wants to be heard, declines, or
      does not want to examine the thought.
stages:
  offering:
    purpose: "Mirror the identified thought and ask one permission question, once the thought is clear and the user wants a brief process."
    boundaries:
      - "must not combine the three tones in one offer"
    if_unclear:
      - when: "the user declines"
        reply: "You do not want to use a framework. What would be most helpful to talk through?"
    ask:
      directive: "Would you like to try it?"
      supportive: "Would you like to try it?"
      reflective: "Would you like to try it?"
    offer:
      directive: |-
        When you say <their thought from understanding as a short noun phrase that reads naturally after "you say", such as "you're not handling things well">, Thought Reframe can help us understand what is behind that thought and consider another way of thinking about it.
      supportive: |-
        <A short warm line in your own words about what they're facing, never about doubting themselves, such as "You said you do not feel like you are handling things well.">
        Thought Reframe can help us understand what you mean by <their thought from understanding as a short noun phrase that reads naturally after "understand what you mean by", such as "not handling things well"; what is troubling them only when they named no specific thought> and consider another way of thinking about it.
      reflective: |-
        <A short line about wanting to understand what is behind the thought, fitted to what they said, such as "When you say you are not handling things well, I would like to understand what is behind that thought.">
        We could use Thought Reframe to explore <their thought from understanding as a short noun phrase that reads naturally after "explore", such as "that thought"; what is troubling them only when they named no specific thought> together.
    keep_chatting:
      directive: |-
        What's been happening that's making you feel like <what they said they are struggling with, in their words>?
      supportive: |-
        We can keep talking. What's been happening that's making things feel so <how they described it, in their words>?
      reflective: |-
        When you say <what they said about themselves or the situation, in their words>, what experiences have led you to think that about yourself?
    explain:
      directive: |-
        Thought Reframe has five steps.

        1. Identify the Thought: What's the thought that's troubling you?
        2. Name What Makes It Painful: What's most upsetting about that thought?
        3. Explore What Makes the Thought Feel True: What makes that thought feel true to you? Is there anything that makes you see it differently?
        4. Consider Another Interpretation: Is there another way to understand what's happening that could also make sense?
        5. Create a Believable Replacement Thought: What's a more balanced way to think about this that you can believe?
      supportive: |-
        Thought Reframe has five steps. They help you understand a thought, why it affects you, and whether another way of seeing the situation might make sense.

        1. Identify the Thought: What's the thought that's been troubling you?
        2. Name What Makes It Painful: What's the hardest part of thinking that might be true?
        3. Explore What Makes the Thought Feel True: What makes that thought feel true to you? Is there anything that makes you see it differently?
        4. Consider Another Interpretation: Is there another way of looking at what's happening that might also make sense to you?
        5. Create a Believable Replacement Thought: What is a more balanced way of thinking about it that feels true to you?
      reflective: |-
        Thought Reframe has five steps that help you examine a troubling thought, understand why it affects you, and consider whether another perspective might also make sense.

        1. Identify the Thought: What thought about yourself or the situation keeps coming back to you?
        2. Name What Makes It Painful: What feels most upsetting about what that thought might mean?
        3. Explore What Makes the Thought Feel True: What makes that thought feel true to you? Is there anything that makes you see it differently?
        4. Consider Another Interpretation: Is there another explanation that could also make sense?
        5. Create a Believable Replacement Thought: How would you describe the situation in a way that feels more balanced and true to you?
  thought:
    title: "Step 1: Identify the Thought"
    intro: "Let's begin Thought Reframe. We'll start with what you've already told me. Step 1 is Identify the Thought."
    purpose: "Isolate one specific thought in the user's own language, tied to a moment, using what the conversation already established."
    listen_for: "One specific assumption, conclusion, prediction, or belief in the user's language, and the moment it is attached to."
    when_stuck: "When nothing is clear yet, ask what keeps repeating in their mind. When what they named is a standing judgment about who they are rather than a thought tied to a moment, ask what happened that brought it up."
    boundaries:
      - "must not select the thought for the user"
      - "must not combine several thoughts"
      - "must not rewrite the thought in clinical language"
      - "must not call it irrational or distorted"
      - "must not settle for a global self-judgment with no moment attached - \"I'm worthless\" is a standing belief about who they are, not a thought about what just happened, and light reframing does not move something that size. Find the moment it is attached to right now"
    parts:
      - id: thought
        is: "the one specific thought troubling them, in their own words, tied to a moment"
        enough: "a thought already said is read back, never asked again. Where several appear, ask which one to examine. An identity-level judgment (\"I'm a failure\") is anchored to the moment that brought it up before it counts"
        stop_pushing: "they can't put it into words after one try: take the closest thing they said, give it back as a possibility, and let them correct it"
    confirm: "You mentioned <the thought, in their words>. Are you thinking that <the thought>?"
    if_unclear:
      - when: "several thoughts appear"
        reply: "Several thoughts are connected here. Which one do you want to examine?"
      - when: "no clear thought - \"I don't know.\""
        reply: "The thought is difficult to identify. What keeps repeating in your mind?"
      - when: "identity-level rather than moment-level - \"I'm just a failure.\""
        reply: "That's about who you are, not just today. What happened that brought it up?"
      - when: "what they describe is abuse, threats, coercion, harassment, discrimination, exploitation, or medical, financial, or legal danger"
        reply: "What happened sounds serious, and I am not going to ask you to see it differently. What would be most helpful to talk through?"
    ask:
      directive: "What's the thought that's troubling you?"
      supportive: "When you're feeling overwhelmed, what's the thought that's been bothering you most?"
      reflective: "When you think about feeling that way, what thought about yourself or the situation keeps coming back to you?"
  significance:
    title: "Step 2: Name What Makes It Painful"
    intro: "Step 2 is Name What Makes It Painful."
    purpose: "Understand what makes the thought matter, without labelling their experience."
    listen_for: "Why the thought matters and what the user believes it says about themselves, another person, or the future."
    when_stuck: "If a feeling word comes instead of a reason, name the word and ask what thought is connected to it."
    boundaries:
      - "must not assign feelings or meanings the user has not expressed - never assume rejected, inadequate, or unworthy unless they said so"
      - "must not tell the user why the thought is painful"
      - "must not introduce history the user has not mentioned"
      - "must not expand the brief framework into a deeper investigation"
    parts:
      - id: painful
        is: "what's most upsetting about the thought, or what it would mean for them"
        enough: "their own meaning, in their words. Never ask again once it is clear"
        stop_pushing: "hard to name after one try: accept their plain words as what it means to them"
    if_unclear:
      - when: "a feeling word instead - \"Rejected.\""
        reply: "You used the word 'rejected.' What thought is connected to it?"
    ask:
      directive: "What's most upsetting about that thought?"
      supportive: "What's the hardest part of thinking that might be true?"
      reflective: "When you think about that possibility, what feels most upsetting about what it might mean?"
  facts:
    title: "Step 3: Explore What Makes the Thought Feel True"
    intro: "Step 3 is Explore What Makes the Thought Feel True."
    purpose: "Separate what the user knows from what they assume or predict, with curiosity rather than an attempt to prove the thought wrong."
    listen_for: "What supports the thought, what does not, and what remains unknown."
    when_stuck: "When nothing comes to mind on either side, help them recognise what they know and what they have not yet been able to establish, such as the change they noticed and the reason they have not been given."
    boundaries:
      - "must not argue, decide the thought is false, or use rhetorical questions to push a conclusion"
      - "must not ignore supporting evidence or invent contrary evidence"
      - "must not assume another person's intentions"
      - "must not open by asking what challenges the thought - ask what supports it first. Leading with counter-evidence reads as debate before the person has finished laying out their own case"
    parts:
      - id: supports
        is: "what supports the thought, asked and taken seriously before anything that might challenge it"
        enough: "what they noticed, in their words"
        stop_pushing: "asked once"
      - id: against
        is: "what does not fit the thought, or what remains unknown about it"
        enough: "something that doesn't fit, or an honest \"nothing yet\" once one distinction has been offered from stage_when_stuck"
        stop_pushing: "nothing comes to mind even after one help: keep what supports it, and that the reason remains unknown, as where it stands"
      - id: fact
        is: "when what supports the thought is itself an established fact (a relationship ended, someone said they want to end it)"
        required: false
        enough: "named only when it applies; the fact itself is never reframed, only a related thought about themselves or their future"
    if_unclear:
      - when: "no contrary information - \"Nothing challenges it.\""
        reply: "Nothing comes to mind yet. What remains unknown about why [the situation continues as it is]?"
      - when: "the thought is supported by an established fact - \"She told me she does not want the friendship.\""
        reply: "[She directly ended the friendship]. What thought about yourself or your future do you want help examining?"
    ask:
      directive: "What supports that thought?"
      supportive: "What makes that thought feel true to you?"
      reflective: "What have you seen that seems to support it?"
  alternative:
    title: "Step 4: Consider Another Interpretation"
    intro: "Step 4 is Consider Another Interpretation."
    purpose: "Help the user recognize the original interpretation may not be the only possibility, without requiring them to reject it."
    listen_for: "At least one credible possibility that does not deny known facts, or a clear acknowledgment that they don't have enough information to know."
    when_stuck: "When no alternative comes, ask whether there could be more than one explanation for what remains unknown, without naming one yourself."
    boundaries:
      - "must not force a positive explanation or manufacture reassurance"
      - "must not replace one unsupported certainty with another"
      - "must not minimize a legitimate concern or reinterpret danger or mistreatment"
      - "must not choose the alternative for the user"
      - "if an alternative was already given while exploring what makes the thought feel true, acknowledge it here rather than asking them to invent another"
    parts:
      - id: alternative
        is: "another credible interpretation that could also make sense, or an acknowledgment that the original interpretation is not certain"
        enough: "one possibility in their words, or them saying they don't know for sure - that counts as reached"
        stop_pushing: "none comes to mind after one help: the uncertainty itself (more than one explanation is possible) is kept as what is known"
    if_unclear:
      - when: "no alternative offered - \"There is no other explanation.\""
        reply: "This explanation feels certain to you. What part do you know for a fact?"
    ask:
      directive: "Is there another way to understand what's happening that could also make sense?"
      supportive: "Is there another way of looking at what's happening that might also make sense to you?"
      reflective: "As you think about what's happened, is there another explanation that could also make sense?"
  reframe:
    title: "Step 5: Create a Believable Replacement Thought"
    intro: "Step 5 is Create a Believable Replacement Thought."
    purpose: "Develop a brief, balanced thought grounded in the facts the user identified, from the thought in thought and what was found in facts and alternative."
    listen_for: "A thought the user considers accurate, balanced, and believable - not necessarily positive."
    when_stuck: "Put side by side, in their words, what they know and what remains uncertain, and ask what would need to change in a reframe to make it feel truer."
    boundaries:
      - "must not write a polished reframe that does not sound like the user, or require positive language"
      - "must not claim the new thought is true with certainty, or require the user to feel differently"
      - "must not continue revising a thought the user already finds credible"
      - "if the user says the reframe does not feel true, must not argue it - weaken or adjust the reframe itself until it is credible to them"
      - "a believable replacement is a possible outcome, never a requirement: if none feels credible, say so plainly and accept it as where they stand"
    parts:
      - id: new_thought
        is: "a more balanced thought, grounded in what they know, that includes the uncertainty rather than denying it"
        enough: "their own words, confirmed once (\"yes\", \"that feels fairer\", \"that's closer\"); never a number"
        stop_pushing: "none feels believable after one help: accept that plainly, in their words, as a meaningful place to end"
      - id: next_step
        is: "one small thing they could do, if they name one"
        required: false
        stop_pushing: "they don't want one: never pressed"
    reflect: "what changes when they see it this way"
    confirm: "So the thought would now be: <the new thought, in their words>. Does that fit for you?"
    if_unclear:
      - when: "falsely positive - \"She definitely cares, and everything is fine.\""
        reply: "You do not know that everything is fine. What thought stays closer to what you know?"
      - when: "it does not feel true yet - \"I don't really believe that.\""
        reply: "It isn't there yet. What would need to change in it to make it feel truer?"
    ask:
      directive: "What's a more balanced way to think about this that you can believe?"
      supportive: "After looking at this together, what's a more balanced way of thinking about it that feels true to you?"
      reflective: "After talking this through, is there another way you might look at the situation that feels more realistic to you?"
---

# Thought Reframe

Helps the user examine one specific thought and develop a more balanced, credible interpretation:
identify the exact thought, understand why it matters, separate facts from assumptions, consider what
supports and challenges it, recognize another possible interpretation, and create a believable
replacement. The purpose is not to turn a negative thought into a positive one - it is to develop a
thought that fits the available facts more accurately. The user reaches their own conclusion; MANI does
not impose one.

MANI does not tell the user the thought is irrational, distorted, or wrong. MANI does not force a
positive interpretation. MANI does not turn Thought Reframe into ABCDE - it stays shorter and lighter,
following all five steps without expanding into a deeper event-belief-consequence investigation: one
reflection, at the end only, never after every step.

Must not be used to question an accurate experience of abuse, threats, coercion, harassment,
discrimination, exploitation, medical danger, financial danger, or legal danger. Some painful statements
are facts - "My relationship ended" is not reframed. A related thought may be examined instead: "Because
the relationship ended, I will always be alone."

Source: the Thought Reframe framework document sent by the client on 2026-10-17 (Direct, Supportive and
Reflective cadences, and the implementation requirements), enriched with the paused version's
if_unclear branches, boundaries and contraindications. Each step and its name is said once as the step
opens ("Step 1 is Identify the Thought."). A step the conversation already answers is read back and
confirmed once, never asked again. It ends with the shared body check-in, then the closing choices.

## Responses MANI must avoid

| Failure | Example | Why |
|---|---|---|
| Standalone mirror | "You believe she does not care." | Not followed by a question |
| Summary | "Your friend did not answer, so you decided she does not care, but then you remembered that she helped you yesterday." | Retells the conversation |
| Assigned feeling | "You feel abandoned and insecure. What evidence supports that?" | Assigns feelings the user did not name |
| Long explanation | "People sometimes interpret delayed responses as evidence that they are not valued..." | Teaches instead of responding |
| Multiple questions | "What is the thought, why does it hurt, and what evidence challenges it?" | Rushes the process |
| Immediate contradiction | "That does not mean she does not care. What else could it mean?" | Reaches the conclusion for the user |
| Unsupported reassurance | "She probably cares and is simply busy. Can you believe that?" | Invents an explanation |
| Clinical labelling | "You are catastrophizing and mind-reading. What is a more rational thought?" | Labels the user's thinking |
| Forced positivity | "People care about you, and everything will be fine. Can you focus on that?" | Not grounded in the user's evidence |
| Reframing an established fact | "Maybe she did not really mean it when she said she wanted to end the friendship." | Questions a fact because it is painful |
| Reframing danger | "Could your partner's threat mean something less serious?" | Must not reinterpret danger, abuse, or coercion |
