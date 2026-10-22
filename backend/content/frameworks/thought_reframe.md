---
id: thought_reframe
name: Thought Reframe
summary: "These questions help you examine a troubling thought and consider a more balanced perspective."
display_order: 2
phases: [offering, thought, painful, feels_true, alternative, replacement]
# Used only when Mani's own confirmation of a stage cannot be: closes their words said back.
confirm_phrases: ["Is that right?", "Do we have this right?", "Did I get that right?", "Does that sound right?"]
activation:
  central_indication: >-
    The user is struggling with a specific thought that is affecting how they feel about
    themselves, another person, or a situation.
  to_find_out:
    - "the exact thought going round, in their words"
    - "the situation it is attached to"
    - "why that thought hurts"
    - "whether they want a brief look rather than a deep one"
    - "whether it could be tested against facts (a loss or a settled fact is not a thought to test)"
  # Documentation of the specification: nothing in mani/ reads to_find_out, appropriate_when or not_when.
  # The prompt reads central_indication, distinctions and contraindications.
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
    - "The only thought left to examine would be whether abuse, threats, coercion, harassment, discrimination, exploitation, or medical, financial, or legal danger was real or as serious as it felt. A thought they formed about themselves after it may still be examined; the event itself is never questioned or reinterpreted as harmless"
    - "The painful statement is itself an established fact - a relationship ended, a person said they want to end the friendship - the fact is not reframed, only a related thought about themselves or their future"
  redirects:
    - signal: "I keep thinking I am incompetent, and I want to understand why one criticism affected me so strongly."
      instead: abcde
    - signal: "I know the thought may never go away, but I do not want it making my decisions."
      instead: act_choice_point
    - signal: "I know what I need to do, but I cannot make myself begin."
      instead: behavioral_activation
  distinctions:
    abcde: >-
      Reframe when one thought is already clear, a shorter process is wanted, and the full
      event-belief-consequence sequence does not require examination. ABCDE when the user wants
      deeper understanding and the event, belief, and consequences need separating. ABCDE takes
      priority when both are equally appropriate, but never choose ABCDE only because the user
      expresses a troubling thought.
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
      directive: "Would you like to test that thought against the facts?"
    offer:
      directive: |-
        There's a framework called Thought Reframe that helps you look at <what is weighing on them, as a short noun phrase that reads naturally after "look at", such as "the thought that you are not doing enough"; their feeling only when they named no thought>, test it against the facts, and land on a more balanced thought you can believe.
      supportive: |-
        <A short warm line in your own words about what they're carrying, never about doubting themselves.>
        There's a framework called Thought Reframe that can help you look at <what is weighing on them, as a short noun phrase that reads naturally after "look at", such as "the thought that you are not doing enough"; their feeling only when they named no thought>, understand what makes it feel so true, and find a more balanced thought you can actually believe.
      reflective: |-
        <A short line about how one thought can start to feel like the whole truth, fitted to what they said.>
        There's a framework called Thought Reframe that helps you examine <what is weighing on them, as a short noun phrase that reads naturally after "examine", such as "the thought that you are not doing enough"; their feeling only when they named no thought>, notice what supports it and what else might be true, and arrive at a more balanced thought you can believe.
    keep_chatting:
      directive: |-
        What's been going through your mind about <what they said is troubling them, in their words>?
      supportive: |-
        We can keep talking. What's been going through your mind about <how they described it, in their words>?
      reflective: |-
        When you say <what they said about themselves or the situation, in their words>, what makes it feel true to you?
    explain:
      directive: |-
        The Thought Reframe framework has five steps:

        1. Identify the Thought: What thought is troubling you?
        2. Name What Makes It Painful: What is the most upsetting thing it might mean?
        3. Explore What Makes the Thought Feel True: What makes it convincing, and is there anything that complicates it?
        4. Consider Another Interpretation: Is there another explanation that could also make sense?
        5. Create a Believable Replacement Thought: What is a more balanced way to see this that you can believe?
      supportive: |-
        The Thought Reframe framework has five steps. Each one helps you understand a thought that is weighing on you and consider a more balanced way to see it.

        1. Identify the Thought: What thought has been weighing on you?
        2. Name What Makes It Painful: What feels most upsetting about what it might mean?
        3. Explore What Makes the Thought Feel True: What makes it so convincing, and is there anything that complicates it?
        4. Consider Another Interpretation: Is there another explanation that could also make sense?
        5. Create a Believable Replacement Thought: What is a more balanced way of seeing this that you could genuinely believe?
      reflective: |-
        The Thought Reframe framework has five steps that help you examine one thought and what it means to you.

        1. Identify the Thought: What thought about yourself, someone else, or the situation keeps coming back?
        2. Name What Makes It Painful: When you think about what it might mean, what feels most painful?
        3. Explore What Makes the Thought Feel True: What seems to support it, and is there anything that makes you see it a little differently?
        4. Consider Another Interpretation: Given what you know, is there another explanation that could also fit?
        5. Create a Believable Replacement Thought: What more balanced understanding could you genuinely believe?
  thought:
    title: "Identify the Thought"
    intro: "Step 1 is Identify the Thought"
    purpose: "Establish the specific thought they want to examine."
    reach: "Where their_case already gives the thought, in what it comes down to, report thought as known in their words. Your text says back the thought together with the underlying feeling they confirmed, in one sentence, then asks whether that is what they want to look at, never asking for it again. The thought is what they tell themselves, in their words, never a reading of it. Where their_case holds no clear thought, report thought as missing and ask what keeps coming back to their mind."
    listen_for: "A specific thought about themselves, another person, or the situation, in their language, and whether they describe what happened or what they concluded it means."
    ready_when: >-
      One specific thought identified, in their own words. If several appear, ask which one to
      examine. A thought they have already said is identified; never ask them to confirm it.
    boundaries:
      - "must use their own words and never select the thought for them or combine several"
      - "must not rewrite the thought in clinical language or call it irrational, distorted or wrong"
      - "must not treat a real event as if it were only a thought: what happened is separate from what they concluded it means"
      - "a broad judgment about who they are: use the conversation to understand what brought it up, and clarify only if necessary"
    if_unclear:
      - when: "several thoughts appear"
        reply: "Several thoughts are connected here. Which one do you want to examine?"
      - when: "no clear thought - \"I don't know.\""
        reply: "The thought is difficult to identify. What keeps repeating in your mind?"
      - when: "a broad judgment about who they are, with nothing said about what brought it up - \"I'm just a failure.\""
        reply: "What was happening when that thought came up?"
      - when: "what they describe is an established fact, not a thought - a relationship ended, a person said they want to end the friendship"
        reply: "What happened is real, and I am not going to ask you to see it differently. What thought about yourself or your future has come from it?"
      - when: "what they describe is abuse, threats, coercion, harassment, discrimination, exploitation, or medical, financial, or legal danger"
        reply: "What happened sounds serious, and I am not going to ask you to see it differently. What would be most helpful to talk through?"
    ask:
      supportive: "What thought has been weighing on you about this?"
      reflective: "What thought about yourself, someone else, or the situation keeps coming back?"
      directive: "What thought is troubling you most about this?"
  painful:
    title: "Name What Makes It Painful"
    intro: "Step 2 is Name What Makes It Painful"
    purpose: "Understand the emotional significance of the thought, without labelling their experience."
    reach: "Where their_case already gives the feeling underneath or what makes the thought hurt, report painful as known in their words, so your text says it back and asks whether that is what makes it hard, never asking for it again."
    listen_for: "What feels most upsetting about what the thought might mean, and what they believe it says about themselves, another person, or the future."
    ready_when: "What makes the thought painful is clear, in their words. MANI does not assign the meaning."
    boundaries:
      - "must acknowledge the painful meaning they have already described and ask only if it is not clear yet"
      - "must not interpret beyond what they have expressed, assign feelings or tell them why the thought is painful"
      - "must not over-validate or repeat their distress back to them at length"
      - "must not introduce history they have not mentioned or turn the brief framework into a deeper investigation"
    if_unclear:
      - when: "a feeling word instead - \"Rejected.\""
        reply: "You used the word 'rejected.' What is it about the thought that brings that up?"
    ask:
      supportive: "What feels most upsetting about what that thought might mean?"
      reflective: "When you think about what that thought might mean, what feels most painful?"
      directive: "What is the most upsetting thing that thought might mean?"
  feels_true:
    title: "Explore What Makes the Thought Feel True"
    intro: "Step 3 is Explore What Makes the Thought Feel True"
    purpose: "Understand why the thought feels convincing, and whether anything complicates it."
    reach: "Report feels_true as missing where nothing has been said for it, so your text asks only what makes the thought convincing. Where what makes it convincing is said and anything that complicates it was never asked, report it as partial with that in their words and the gap complicates, so your text asks only whether anything complicates it."
    listen_for: "The experience, feedback, evidence or pattern that makes the thought convincing, and any information that complicates it."
    ready_when: "They have said what makes the thought convincing and have been asked whether anything complicates it. Nothing complicating it is an answer; they do not have to disprove the thought."
    boundaries:
      - "must not dismiss what supports the thought, argue with it or assume it is inaccurate"
      - "must not stack questions or turn the step into a demand that they defend themselves"
      - "must not invent contrary evidence, assume another person's intentions or lead them to a conclusion"
      - "must not reinterpret danger or mistreatment"
      - "each question asks one part, in their thought and the feeling underneath, and never says what it is for"
    if_unclear:
      - id: complicates
        # The stage whose words fill the reply's slot.
        slot: thought
        when: "what makes the thought convincing has been said and whether anything complicates it has not been asked, so ask only that"
        reply: "Is there anything that complicates the thought that <their thought, in their words>?"
    ask:
      supportive: "What makes that thought feel so convincing to you, and is there anything that complicates it?"
      reflective: "What seems to support that thought, and is there anything that makes you see it a little differently?"
      directive: "What makes that thought convincing, and is there anything that complicates it?"
  alternative:
    title: "Consider Another Interpretation"
    intro: "Step 4 is Consider Another Interpretation"
    purpose: "Consider whether another explanation could also fit the known facts."
    listen_for: "A credible possibility that does not deny what is known, or an acknowledgement that there is not enough information to know."
    ready_when: >-
      A credible alternative is named, or they say there is not enough information to know or that
      none feels credible. That is accepted; never replace it with one of Mani's.
    boundaries:
      - "must invite an alternative only when it is plausible and useful, and use one they already offered rather than asking for another"
      - "must not invent a comforting explanation, force a positive one or claim to know another person's motives"
      - "must not insist they find an alternative if none feels credible, and must not choose one for them"
      - "must not minimize a legitimate concern or reinterpret danger or mistreatment"
    if_unclear:
      - when: "no alternative offered - \"There is no other explanation.\""
        reply: "This explanation feels certain to you. What part do you know for a fact?"
    ask:
      supportive: "Is there another way of understanding this that could also make sense?"
      reflective: "Given what you know, is there another explanation that could also fit?"
      directive: "Is there another explanation that could also make sense?"
  replacement:
    title: "Create a Believable Replacement Thought"
    intro: "Step 5 is Create a Believable Replacement Thought"
    purpose: "Help them express a more balanced thought they can genuinely believe, in their own words, grounded in what they have identified."
    reach: "Report replacement as known only where they gave a thought that fits what they know and said they believe it. A thought they offered without saying they believe it is partial with their words and the gap believe, so your text asks whether it feels true to them."
    listen_for: "A balanced thought in their own words that fits what is known and that they find believable. It may be cautious, partial or uncertain."
    ready_when: >-
      A thought, in their own words, that fits what is known and that they say they believe. It does
      not have to be positive. The gate is whether they actually believe it: "yes", "that feels
      fairer", "that's closer" mean it is done. If it does not feel true yet, adjust it with them
      until it does. Check once, plainly, if they have not said; never ask for a number. If they
      already arrived at one, recognise it and finish without asking them to repeat it.
    boundaries:
      - "must build on their own reasoning and language, and never write the thought for them unless they ask for help finding words"
      - "when they are unsure, may offer two or three loose possibilities for a believable thought, from what they know, never as advice and never deciding for them"
      - "must not force an affirmation, claim the new thought is true with certainty or minimize a genuine problem"
      - "must not require them to feel differently or keep revising a thought they already find credible"
      - "if they say it does not feel true, must not argue it - weaken or adjust the thought itself until it is credible to them"
    if_unclear:
      - when: "falsely positive - \"Everything is fine, there is nothing to worry about.\""
        reply: "You do not know that everything is fine. What thought stays closer to what you know?"
      - id: believe
        when: "it does not feel true yet - \"I don't really believe that.\""
        reply: "It isn't there yet. What would need to change in it to make it feel truer?"
    ask:
      supportive: "What would be a more balanced way of seeing this that you could genuinely believe?"
      reflective: "What more balanced understanding could you genuinely believe?"
      directive: "What is a more balanced way to see this that you can believe?"
---

# Thought Reframe

Thought Reframe helps the person examine a troubling thought, understand why it feels painful or
convincing, and consider whether another interpretation might also fit. **The goal is not to prove
the thought wrong or replace it with forced positivity.** It is a guide for reflection, not a
mandatory five-question interview. The person reaches their own conclusion; MANI does not impose one.

It is for a specific thought that is affecting how the person feels about themselves, another
person, or a situation. ABCDE takes priority when both are equally appropriate, but MANI does not
choose ABCDE only because someone expresses a troubling thought. MANI does not turn Thought Reframe
into ABCDE: it stays shorter and lighter.

Source: the client's Thought Reframe document (`docs/client/docs/Thought_Reframe_Framework.md`) and
its framework note. It supersedes the older six-frameworks specification where they differ.

## The five steps

1. **Identify the Thought:** what thought about the self, another person, or the situation is troubling the person?
2. **Name What Makes It Painful:** what feels most upsetting about what the thought might mean?
3. **Explore What Makes the Thought Feel True:** what makes the thought convincing, and is there anything that complicates it?
4. **Consider Another Interpretation:** is there another explanation that could also make sense?
5. **Create a Believable Replacement Thought:** what is a more balanced understanding the person can genuinely believe?

## How it behaves

- Use what the person has already shared; never ask them to restate a thought or feeling that is already clear.
- Introduce the step name naturally, and keep every turn from sounding like a worksheet.
- A step is complete when its purpose has been met, even if no new question is needed.
- Never call the thought irrational, distorted, wrong, or automatically untrue.
- Never treat a real event as if it were merely a thought: separate what happened from what the person concluded it means.
- Never manufacture an alternative explanation or push the person to accept one. If none feels credible, stay with what is known and uncertain.
- A replacement thought must be credible to the person and consistent with what is known. It may be cautious, partial or uncertain, and does not have to sound positive.
- If the original thought reflects a real problem, never minimise or dismiss it. If a practical problem needs attention, do not keep reframing the thought as a substitute for addressing it.
- If the person wants to pause, stop, or carry on chatting, respect that.

## Flexible progression

The five steps describe the work, not five compulsory questions. A step the conversation already
answers is said back and confirmed once, never asked again. If a believable replacement thought
emerges early, recognise it. MANI does not skip a step in silence.

## Example: feeling inadequate after vague feedback

A manager criticised the person's client communication without a concrete example. They conclude
"I'm not enough" and have become anxious around clients. A rigid approach would ask them to list
evidence for and against "I'm not enough", though the conversation has not established what the
manager meant. A more natural approach first recognises the real uncertainty: "Without an example,
you're left trying to guess what needs to change, and that seems to be making every client
interaction feel harder." From there MANI asks only for a missing piece: what the feedback actually
contained, what "I'm not enough" means to them, or whether another plausible way to understand it
exists. It does not assume the manager is wrong, that the person is at fault, or that the thought
must be replaced by a positive one.

## Completion

When Thought Reframe reaches a meaningful conclusion, MANI acknowledges the person's own
understanding in one short sentence, without overexplaining or reopening completed steps. The
shared body check-in follows, introduced naturally, never implying it is mandatory and never
overriding a request to stop or change topic.

Must not be used to question an accurate experience of abuse, threats, coercion, harassment,
discrimination, exploitation, medical danger, financial danger, or legal danger. Some painful
statements are facts: "My relationship ended" is not reframed. A related thought may be examined
instead: "Because the relationship ended, I will always be alone."

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
