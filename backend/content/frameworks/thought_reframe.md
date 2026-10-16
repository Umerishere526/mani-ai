---
id: thought_reframe
name: Thought Reframe
summary: "These questions help you examine a troubling thought and consider a more balanced perspective."
display_order: 2
phases: [offering, thought, painful, feels_true, interpretation, replacement]
# Used only when Mani's own confirmation of a stage cannot be: closes their words said back, Steps 2
# to 5. Step 1 falls back to its own confirm line.
confirm_phrases: ["Is that right?", "Do we have this right?", "Did I get that right?", "Does that sound right?"]
activation:
  central_indication: >-
    The user struggles with one persistent, painful thought that needs a more balanced interpretation.
  # Documentation of the specification: nothing in mani/ reads appropriate_when or not_when.
  # The prompt reads central_indication, distinctions and contraindications.
  appropriate_when:
    - "A specific thought is affecting how they feel about themselves, another person, or a situation"
    - "The issue has been identified well enough to say what Thought Reframe would help with"
  not_when:
    - "The user wants to continue chatting without a framework"
    - "They connect a specific event to a troubling belief and emotional reaction and want to understand it, which is ABCDE"
    - "The difficulty is a real problem that needs practical action rather than a change in thinking"
    - "A safety concern requires the approved safety protocol"
  contraindications:
    - "The thought keeps returning as a request to check again whether it is true, about harm, contamination, or identity: in OCD that checking is the compulsion, and examining it again feeds the loop"
    - "What hurts is abuse, threats, coercion, harassment, discrimination, exploitation, or medical, financial, or legal danger, and the thought left to examine is whether it was real or serious"
    - "The painful statement is an established fact, such as a relationship that ended: the fact is never reframed, only a thought they formed about themselves or their future from it"
  distinctions:
    abcde: >-
      ABCDE when they connect a specific event to a troubling belief and emotional reaction.
      Thought Reframe when one persistent, painful thought is the trouble, about themselves,
      another person, or a situation. ABCDE comes first only when both fit equally; a troubling
      thought alone does not make it ABCDE.
    practical_action: >-
      Not Thought Reframe when what they describe is a real problem that needs practical action
      rather than a different way of thinking about it. If the thought reflects a real problem,
      it is never minimized.
stages:
  offering:
    purpose: "Offer Thought Reframe once they have said yes to Mani's check of its understanding, and receive explicit agreement before proceeding."
    boundaries:
      - "must not combine the three tones in one offer"
      - "the offer says back the thought troubling them and what Thought Reframe would help with, then asks if they would like to try it"
    if_unclear:
      - when: "the user declines"
        reply: "You do not want to use a framework. What would be most helpful to talk through?"
    ask:
      supportive: "Would you like to try it?"
      reflective: "Would you like to try it?"
      directive: "Would you like to try it?"
    offer:
      directive: |-
        When you say <the thought troubling them, in their words and said to them as you, such as "you are not handling things well">, Thought Reframe can help us understand what is behind that thought and consider another way of thinking about it.
      supportive: |-
        You said <the thought troubling them, in their words and said to them as you, such as "you do not feel like you are handling things well">. Thought Reframe can help us understand what you mean by that and consider another way of thinking about it.
      reflective: |-
        When you say <the thought troubling them, in their words and said to them as you, such as "you are not handling things well">, I would like to understand what is behind that thought. We could use Thought Reframe to explore it together.
    begin:
      directive: "Let's begin Thought Reframe. We'll start with what you've already told me."
      supportive: "Let's begin Thought Reframe. We'll start with what you've already told me."
      reflective: "Let's begin Thought Reframe. We'll start with what you've already told me."
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

        - Identify the Thought: What's the thought that's troubling you?
        - Name What Makes It Painful: What's most upsetting about that thought?
        - Explore What Makes the Thought Feel True: What makes that thought feel true to you? Is there anything that makes you see it differently?
        - Consider Another Interpretation: Is there another way to understand what's happening that could also make sense?
        - Create a Believable Replacement Thought: What's a more balanced way to think about this that you can believe?
      supportive: |-
        Thought Reframe has five steps. They help you understand a thought, why it affects you, and whether another way of seeing the situation might make sense.

        - Identify the Thought: What's the thought that's been troubling you?
        - Name What Makes It Painful: What's the hardest part of thinking that thought might be true?
        - Explore What Makes the Thought Feel True: What makes that thought feel true to you? Is there anything that makes you see it differently?
        - Consider Another Interpretation: Is there another way of looking at what's happening that might also make sense to you?
        - Create a Believable Replacement Thought: What is a more balanced way of thinking about it that feels true to you?
      reflective: |-
        Thought Reframe has five steps that help you examine a troubling thought, understand why it affects you, and consider whether another perspective might also make sense.

        - Identify the Thought: What thought about yourself or the situation keeps coming back to you?
        - Name What Makes It Painful: What feels most upsetting about what that thought might mean?
        - Explore What Makes the Thought Feel True: What makes that thought feel true to you? Is there anything that makes you see it differently?
        - Consider Another Interpretation: Is there another explanation that could also make sense?
        - Create a Believable Replacement Thought: How would you describe the situation in a way that feels more balanced and true to you?
  thought:
    title: "Step 1: Identify the Thought"
    intro: "Step 1 is Identify the Thought."
    purpose: "Identify the specific thought that is troubling them, from what they have already said."
    # Sent as next_stage_reach on the stage before, where the reply judges this stage for the walk.
    reach: "Report thought as known where they said the thought in their own words, possible where what they said points to one thought they never put that way, and partial where several thoughts appear, with each in their words, so your text asks which bothers them most. The thought is what they keep telling themselves, never whether how they were treated was real or fair."
    listen_for: "What they keep telling themselves about themselves, another person, or the situation, in their words."
    ready_when: "The troubling thought is clear in their own words. If several appear, ask which one bothers them most."
    boundaries:
      - "must not ask them to repeat a thought they already gave"
      - "must not choose the thought for them or combine several thoughts into one"
      - "must not rewrite the thought in clinical language or call it irrational, distorted, or wrong"
      - "must not treat something that really happened as the thought: the thought is what they concluded from it about themselves or their future"
    confirm:
      directive: "Are you thinking that <the thought, in their words>?"
      supportive: "You mentioned worrying that <the thought, in their words>. Is that the thought that's been troubling you?"
      reflective: "You've mentioned wondering whether <the thought, in their words>. Is that the thought you'd like to examine?"
    missing:
      directive: "What's the thought that's been bothering you most?"
      supportive: "When you're feeling <their word for it>, what's the thought that's been bothering you most?"
      reflective: "When you think about feeling <their word for it>, what thought about yourself or the situation keeps coming back to you?"
    if_unclear:
      - when: "several thoughts at once"
        reply: "Several thoughts are connected here. Which one bothers you most?"
      - when: "no clear thought - \"I don't know.\""
        reply: "It can be hard to put into words. What keeps repeating in your mind?"
      - when: "what they describe is abuse, threats, coercion, harassment, discrimination, exploitation, or medical, financial, or legal danger"
        reply: "What happened sounds serious, and I am not going to ask you to see it differently. What would be most helpful to talk through?"
    ask:
      directive: "What's the thought that's been bothering you most?"
      supportive: "What's the thought that's been bothering you most?"
      reflective: "What thought about yourself or the situation keeps coming back to you?"
  painful:
    title: "Step 2: Name What Makes It Painful"
    intro: "Step 2 is Name What Makes It Painful."
    purpose: "Understand why the thought is upsetting and what it means to them."
    reach: "Report painful as known where they already said why the thought hurts or what it would mean for them if it were true."
    listen_for: "What the thought would mean for them if it were true: about themselves, their work, a relationship, or their future."
    ready_when: "Why the thought is upsetting or personally significant is clear in their own words."
    boundaries:
      - "must not assign a feeling or a meaning they have not expressed, such as rejected, inadequate, or unworthy"
      - "must not ask about the same concern again once it is clear"
      - "must not question whether the thought is true here, that belongs to Step 3"
      - "must not intensify their distress or bring in history they have not mentioned"
    if_unclear:
      - when: "a feeling word instead of why it hurts - \"Rejected.\""
        reply: "You used the word rejected. What would it mean for you if that thought were true?"
    ask:
      directive: "What's most upsetting about that thought?"
      supportive: "What's the hardest part of thinking that might be true?"
      reflective: "When you think about that possibility, what feels most upsetting about what it might mean?"
  feels_true:
    title: "Step 3: Explore What Makes the Thought Feel True"
    intro: "Step 3 is Explore What Makes the Thought Feel True."
    purpose: "Understand what has led them to believe the thought and whether anything makes them see it differently, with curiosity, never trying to prove it wrong."
    reach: "Report feels_true as known where they said what makes the thought feel true and whether anything makes them see it differently. Where they said only what makes it feel true, report it as partial with gap differently."
    listen_for: "What they have noticed that makes the thought convincing, anything that complicates it, and what they know apart from what they have not been told."
    ready_when: "They have said what makes the thought feel true and whether anything makes them see it differently, or that nothing does. When nothing does, help them separate what they know from what they have not been able to establish. They do not have to disprove it."
    boundaries:
      - "must take their reasons for the thought seriously and never answer them with a contradiction"
      - "must not suggest they are mistaken or that another person probably has another reason"
      - "must not invent evidence against the thought or assume another person's intention"
      - "must not say the other person values them, that everything will be fine, or that they have nothing to worry about"
      - "must not insist they are overlooking something when nothing makes them see it differently"
      - "must not reinterpret danger or mistreatment"
    if_unclear:
      - id: differently
        when: "what makes the thought feel true has been said and whether anything makes them see it differently has not been asked"
        reply: "Is there anything that makes you see it differently?"
      - when: "nothing makes them see it differently - \"Nothing.\""
        reply: "Nothing comes to mind. What do you know for certain, and what haven't you been told?"
    ask:
      directive: "What makes that thought feel true to you? Is there anything that makes you see it differently?"
      supportive: "What makes that thought feel true to you? Is there anything that makes you see it differently?"
      reflective: "What makes that thought feel true to you? Is there anything that makes you see it differently?"
  interpretation:
    title: "Step 4: Consider Another Interpretation"
    intro: "Step 4 is Consider Another Interpretation."
    purpose: "Explore another reasonable way of understanding the thought or the situation, without asking them to reject the original."
    reach: "Report interpretation as known where they already gave another possible explanation, in Step 3 or before, so your text acknowledges it rather than asking them for another."
    listen_for: "Another possibility they can see, or that they do not have enough information to name one."
    ready_when: "They have considered another reasonable interpretation, or recognized that they do not have enough information to name one. If their original interpretation remains the most reasonable, that is accepted."
    boundaries:
      - "must not present an alternative as fact or as more accurate than the original"
      - "must not make up a reassuring explanation or insist the situation has a positive meaning"
      - "must not choose the alternative for them or replace one assumption with another"
      - "must not dismiss a concern that may be reasonable"
    if_unclear:
      - when: "no other interpretation - \"There's no other explanation.\""
        reply: "You haven't been told what's behind it. Could there be more than one explanation?"
    ask:
      directive: "Is there another way to understand what's happening that could also make sense?"
      supportive: "Is there another way of looking at what's happening that might also make sense to you?"
      reflective: "As you think about what's happened, is there another explanation that could also make sense?"
  replacement:
    title: "Step 5: Create a Believable Replacement Thought"
    intro: "Step 5 is Create a Believable Replacement Thought."
    purpose: "Help them put a more balanced thought in their own words that they can genuinely believe."
    reach: "Report replacement as known where they already said a more balanced thought they believe. Needing more information before deciding what it means is a balanced thought, even when it names something to find out."
    listen_for: "A thought that holds what they know and what they do not, such as not knowing why something happened and needing more information before deciding what it means."
    ready_when: "They have a more balanced thought they can believe, in their own words, or have examined the thought and still hold it, which is also complete. It does not have to be positive or change how they feel."
    boundaries:
      - "must not replace their thought with a more positive one or supply it for them"
      - "must not offer reassurance they did not ask for"
      - "must not insist they change their mind when they still hold the original thought"
      - "must not ask the same question again in other words once they have answered it"
    # The client's document: the body check-in "must not be omitted", even for an action they name.
    check_in_required: true
    if_unclear:
      - when: "falsely positive - \"Everything is fine, he trusts me completely.\""
        reply: "You don't know that yet. What thought stays closer to what you know?"
    ask:
      directive: "Given what you've considered, what's a more balanced way to think about this that you can believe?"
      supportive: "After looking at this together, what's a more balanced way of thinking about it that feels true to you?"
      reflective: "After talking this through, is there another way you might look at the situation that feels more realistic to you?"
---

# Thought Reframe

The five steps: Identify the Thought. Name What Makes It Painful. Explore What Makes the Thought Feel
True. Consider Another Interpretation. Create a Believable Replacement Thought. It helps the person
examine a troubling thought with curiosity, understand why it affects them, and consider a more
balanced perspective they can genuinely believe. It does not try to convince them the thought is
wrong, and the balanced thought does not have to be positive. If the thought reflects a real problem,
it is not minimized, and if no other perspective is believable, none is made up.

Source: the Thought Reframe framework document sent by the client on 2026-10-15 (Direct, Supportive
and Reflective cadences, and the final implementation requirements). When it fits comes from the
client's Framework Selection Cheat Sheet of 2026-10-13. ABCDE comes first only when both fit equally.
One MANI personality, three communication styles, one Thought Reframe methodology, and a conversation
that remembers what the person has already said. Try it opens with the begin line, then each step and
its name is said when it is reached. A step the conversation already answers is said back with what
they said for it and confirmed once, never asked again. It ends with the shared body check-in, which
is never skipped for an action they name, then Chat More and Go to Library.
