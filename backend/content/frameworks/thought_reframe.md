---
id: thought_reframe
name: Thought Reframe
summary: "These questions help you look at a thought that keeps bothering you and find a fairer way to see it."
display_order: 2
phases: [offering, thought, significance, facts_for, facts_against, alternative, reframe]
activation:
  central_indication: >-
    One specific painful thought or interpretation is intensifying distress, and the user wants
    a brief shift in perspective rather than a deep event-by-event examination.
  to_find_out:
    - "the exact thought going round, in their words"
    - "the situation it is attached to"
    - "what makes that thought hard for them"
    - "whether they want a brief look rather than a deep one"
    - "whether it could be tested against facts (a loss or a settled fact is not a thought to test)"
  # Documentation of the specification: nothing in mani/ reads appropriate_when or not_when.
  # The prompt reads central_indication, to_find_out, distinctions and contraindications; the
  # router reads never_offer_when_said and stuck_offer.
  appropriate_when:
    - "One specific thought is intensifying the user's difficulty"
    - "The thought contains an assumption, prediction, or broad conclusion"
    - "The user is treating one interpretation as certain"
    - "Relevant facts can be considered"
    - "Another interpretation may be possible"
    - "The user wants a brief process"
    - "The issue has already been clearly identified"
    - "The user has agreed to try a framework"
  not_when:
    - "The user wants to continue chatting without a framework"
    - "The user has not agreed to try it"
    - "No specific thought has been identified"
    - "The user wants deeper examination of an event, belief, and consequence"
    - "The primary need is a practical decision or plan"
    - "The primary difficulty is inactivity or withdrawal"
    - "The user needs to choose how to act while uncertainty remains"
    - "The user cannot engage in reflective questions"
    - "A safety concern requires the approved safety protocol"
  contraindications:
    - "The thought keeps returning as a repeated request to check whether it is true, especially about harm, contamination, or identity - in OCD this checking is the compulsion, and answering it again only feeds the loop it is trying to escape"
    - "The person describes abuse, threats, coercion, harassment, discrimination, exploitation, or medical, financial, or legal danger - examining the thought must never turn into questioning whether it was real or as serious as it felt, and Mani must not reinterpret the behaviour as harmless"
    - "The painful statement is itself an established fact - a relationship ended, a person said they want to end the friendship - the fact is not reframed, only a related thought about themselves or their future"
  distinctions:
    abcde: >-
      Reframe when one thought is already clear, a shorter process is wanted, and the full
      event-belief-consequence sequence does not require examination. ABCDE when the user wants
      deeper understanding and the event, belief, and consequences need separating.
    act_choice_point: >-
      Reframe when evidence may help reconsider the thought. ACT when the thought cannot be
      proved or disproved, uncertainty cannot be resolved, examining the thought is keeping the
      user stuck, or the user needs to choose how to act while the thought remains. Reframe asks
      "What else may be true?"; ACT asks "How do you want to respond while this thought is
      present?"
    continued_conversation: >-
      Continue chatting when the thought is unclear, the user wants to be heard, declines, or
      does not want to examine the thought.
stages:
  offering:
    purpose: "Mirror the identified thought and ask one permission question, once the thought is clear and the user wants a brief process."
    boundaries:
      - "must not combine the three tones or shift tone without a reason grounded in the conversation"
    if_unclear:
      - when: "the user declines"
        reply: "You do not want to use a framework. What would be most helpful to talk through?"
    ask:
      supportive: "This thought keeps returning for you. Would it help to look at it together?"
      reflective: "Would it help to examine what supports that thought and what else may be true?"
      direct: "Would you like to test that thought against the facts?"
  thought:
    purpose: "Isolate one specific thought in the user's own language."
    listen_for: "One specific assumption, conclusion, prediction, or belief in the user's language."
    ready_when: >-
      One specific thought identified. If several appear, ask which one to examine. Once you have
      mirrored it back, anything other than a no confirms it: an elaboration, a detail about when
      it came up, or a yes all mean move on to its significance. Never ask for that confirmation
      a second time.
    boundaries:
      - "must not select the thought for the user"
      - "must not combine several thoughts"
      - "must not rewrite the thought in clinical language"
      - "must not call it irrational or distorted"
      - "must not settle for a global self-judgment with no moment attached - \"I'm worthless\" is a standing belief about who they are, not a thought about what just happened, and light reframing does not move something that size. Find the moment it is attached to right now"
    if_unclear:
      - when: "several thoughts appear"
        reply: "Several thoughts are connected here. Which one do you want to examine?"
        start_only: true
      - when: "no clear thought - \"I don't know.\""
        reply: "The thought is difficult to identify. What keeps repeating in your mind?"
        start_only: true
      - when: "identity-level rather than moment-level - \"I'm just a failure.\""
        reply: "That's about who you are, not just today. What happened that brought it up?"
        start_only: true
      - when: "what they describe is abuse, threats, coercion, harassment, discrimination, exploitation, or medical, financial, or legal danger"
        reply: "What happened sounds serious, and I am not going to ask you to see it differently. What would be most helpful to talk through?"
    ask:
      supportive: "Is that the thought you want to look at together?"
      reflective: "Is that the thought you want to look at?"
      direct: "Is that the thought you want to look at?"
  significance:
    purpose: "Understand what makes the thought matter, without labelling their experience."
    listen_for: "Why the thought matters and what the user believes it says about themselves, another person, or the future."
    boundaries:
      - "must not assign feelings"
      - "must not tell the user why the thought is painful"
      - "must not introduce history the user has not mentioned"
      - "must not expand the brief framework into a deeper investigation"
    ask:
      supportive: "Why does that thought matter to you?"
      reflective: "Why does that thought matter to you?"
      direct: "Why does that thought matter to you?"
  facts_for:
    purpose: "Establish what the user knows supports the thought."
    listen_for: "What supports the thought, and what is known rather than assumed."
    boundaries:
      - "must not argue"
      - "must not decide the thought is false"
      - "must not ignore supporting evidence"
      - "must not invent contrary evidence"
      - "must not assume another person's intentions"
      - "must not use rhetorical questions to push a conclusion"
      - "must not open by asking what challenges the thought - ask what supports it first. Leading with counter-evidence reads as debate before the person has finished laying out their own case, and the disconfirming question belongs after, not instead of, that"
    if_unclear:
      - when: "the thought is supported by an established fact - \"She told me she does not want the friendship.\""
        reply: "She directly ended the friendship. What thought about yourself or your future do you want help examining?"
    ask:
      supportive: "What makes you think that is true?"
      reflective: "What makes you think that is true?"
      direct: "What makes you think that is true?"
  facts_against:
    purpose: "Find what does not support the thought, what is assumed or predicted, and what remains unknown."
    listen_for: "What does not support the thought, what is assumed, what remains unknown."
    boundaries:
      - "must not argue"
      - "must not decide the thought is false"
      - "must not ignore supporting evidence"
      - "must not invent contrary evidence"
      - "must not assume another person's intentions"
      - "must not use rhetorical questions to push a conclusion"
    ask:
      supportive: "Is there anything you know that doesn't match that thought?"
      reflective: "Is there anything you know that doesn't match that thought?"
      direct: "Is there anything you know that doesn't match that thought?"
  alternative:
    purpose: "Help the user recognize the original interpretation may not be the only possibility."
    listen_for: "At least one credible possibility that does not deny known facts."
    boundaries:
      - "must not force a positive explanation"
      - "must not replace one unsupported certainty with another"
      - "must not minimize a legitimate concern"
      - "must not reinterpret danger or mistreatment"
      - "must not choose the alternative for the user"
    ask:
      supportive: "What else could be going on?"
      reflective: "What else could be going on?"
      direct: "What else could be going on?"
  reframe:
    purpose: "Develop a brief, balanced thought grounded in the facts the user identified."
    listen_for: "A thought the user considers accurate, balanced, and believable."
    boundaries:
      - "must not write a polished reframe that does not sound like the user"
      - "must not require positive language"
      - "must not claim the new thought is true with certainty"
      - "must not require the user to feel differently"
      - "must not continue revising a thought the user already finds credible"
      - "if the user says the reframe does not feel true, must not argue it"
    if_unclear:
      - when: "they say they do not know what would be fair, or cannot put it into words"
        reply: "That is fine. What is one thing about this that you do know is true?"
        counted: true
    ask:
      supportive: "Putting those together, what would you say is true about this?"
      reflective: "Putting those together, what would you say is true about this?"
      direct: "Putting those together, what would you say is true about this?"
---

# Thought Reframe

Helps the user examine one specific thought and develop a more balanced, credible
interpretation: identify the exact thought, understand why it matters, separate facts from
assumptions, consider what supports and challenges it, recognize another possible
interpretation, and create a believable replacement. **The purpose is not to turn a negative
thought into a positive one** - it is to develop a thought that fits the available facts more
accurately. The user reaches their own conclusion; MANI does not impose one.

MANI does not tell the user the thought is irrational, distorted, or wrong. MANI does not force
a positive interpretation. **MANI does not turn Thought Reframe into ABCDE** - it stays shorter
and lighter, following all five stages without expanding into a deeper event-belief-consequence
investigation.

Must not be used to question an accurate experience of abuse, threats, coercion, harassment,
discrimination, exploitation, medical danger, financial danger, or legal danger. Some painful
statements are facts - "My relationship ended" is not reframed. A related thought may be
examined instead: "Because the relationship ended, I will always be alone."

## Stage progression

Identify the thought -> Identify its significance ->
Examine the facts -> Consider another interpretation -> Create a believable reframe -> Complete.
MANI does not skip directly from the original thought to a replacement thought.

## Worked example - reflection tone

```
User:  My friend has not answered all day. She always responds quickly, so she clearly does
       not care.

Offer
MANI:  You are treating her silence as proof that she does not care. Would it help to examine
       what supports that and what else may be true?
User:  Yes.

Thought
MANI:  The thought is, "She does not care about me." Is that the thought you want to examine?
User:  Yes.

Significance
MANI:  You believe she does not care about you. What makes that thought difficult for you?
User:  It means I do not matter to her.

Facts
MANI:  Her silence has come to mean that you do not matter to her. What supports that conclusion?
User:  She normally answers within an hour, and it has been all day.
MANI:  Her response is much later than usual. What might not support the conclusion that you do
       not matter to her?
User:  She checked on me yesterday and offered to help me.
MANI:  She checked on you and offered help yesterday. What does that add to what you know?
User:  It does not fit with the idea that she does not care.

Alternative
MANI:  Her actions yesterday do not fit the original thought. What else could explain today's
       silence?
User:  She could be busy, or something may have happened.
MANI:  There are reasons you may not know yet. What can you say without guessing which one is
       true?
User:  I do not know why she has not answered.

Reframe
MANI:  The reason remains unknown. What would be a more balanced thought?
User:  She has not answered, but that does not prove she does not care.

Closing
MANI:  Her silence does not prove that she does not care. What changes when you see it this way?
User:  I can wait without deciding what it means.

Somatic
MANI:  You can wait without deciding what her silence means. What do you notice in your body?
```

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
| Wrong tone | after the user selects support: "The evidence is insufficient. Identify a more accurate conclusion." | Abrupt; does not follow the selected tone |
