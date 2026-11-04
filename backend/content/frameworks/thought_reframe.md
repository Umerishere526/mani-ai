---
id: thought_reframe
name: Thought Reframe
summary: "These questions help you look closely at one troubling thought, weigh what supports it and what doesn't, and land on either a more balanced thought you can believe or a next step if the thought points to a real problem."
display_order: 2
phases: [offering, thought, painful, feels_true, alternative, replacement]
# Used only when Mani's own confirmation of a stage cannot be: closes their words said back.
confirm_phrases: ["Is that right?", "Do we have this right?", "Did I get that right?", "Does that sound right?"]
activation:
  central_indication: >-
    The user is struggling with one specific thought about themselves, another person, or a
    situation, and that thought is driving a strong feeling such as fear, sadness, guilt, shame
    or anger.
  to_find_out:
    - "the exact thought that keeps coming back, in their words"
    - "the situation it's attached to, in one sentence"
    - "the strongest feeling it brings up"
    - "whether they want a brief look rather than a deep one"
    - "whether it can be checked against facts (a loss or a settled fact is not a thought to test)"
  # Specification only: nothing in mani/ reads to_find_out, appropriate_when or not_when.
  # The prompt reads central_indication, distinctions and contraindications.
  appropriate_when:
    - "One specific thought is making the user's difficulty worse"
    - "The thought contains an assumption, prediction, or broad conclusion"
    - "The user is treating one interpretation as certain"
    - "Relevant facts can be weighed"
    - "Another interpretation may be possible"
    - "The user wants a brief process"
    - "The issue has already been clearly identified"
    - "The user has agreed to try a framework"
  not_when:
    - "The user wants to keep chatting without a framework"
    - "The user hasn't agreed to try it"
    - "No specific thought has been identified"
    - "The user wants a deeper look at an event, belief, and consequence"
    - "The main need is a practical decision or plan"
    - "The main difficulty is inactivity or withdrawal"
    - "The user needs to choose how to act while uncertainty remains"
    - "The user can't take part in reflective questions right now"
    - "A safety concern calls for the approved safety protocol"
  contraindications:
    - "The thought keeps returning as a repeated request to check whether it's true, especially about harm, contamination, or identity. In OCD this checking is the compulsion, and answering it again only feeds the loop the person is trying to escape"
    - "The only thought left to examine would be whether abuse, threats, coercion, harassment, discrimination, exploitation, or medical, financial, or legal danger was real or as serious as it felt. A thought they formed about themselves afterwards may still be examined. The event itself is never questioned or reinterpreted as harmless"
    - "The painful statement is an established fact, such as a relationship ending or someone saying they want to end the friendship. The fact is never reframed, only a related thought about themselves or their future"
  redirects:
    - signal: "I keep thinking I am incompetent, and I want to understand why one criticism affected me so strongly."
      instead: abcde
    - signal: "I know the thought may never go away, but I do not want it making my decisions."
      instead: act_choice_point
    - signal: "I know what I need to do, but I cannot make myself begin."
      instead: behavioral_activation
  distinctions:
    abcde: >-
      Use Reframe when one thought is already clear, a shorter process is wanted, and the full
      event-belief-consequence sequence doesn't need examining. Use ABCDE when the user wants a
      deeper understanding and the event, belief and consequences need separating. ABCDE takes
      priority when both fit equally, but never choose ABCDE only because the user expresses a
      troubling thought.
    act_choice_point: >-
      Use Reframe when weighing the evidence may help them reconsider the thought. Use ACT when
      the thought can't be proved or disproved, the uncertainty can't be resolved, examining the
      thought is keeping the user stuck, or they need to choose how to act while the thought is
      still there. Reframe asks "What else may be true?" ACT asks "How do you want to respond
      while this thought is present?"
    continued_conversation: >-
      Keep chatting when the thought is unclear, the user wants to be heard, declines, or doesn't
      want to examine the thought.
stages:
  offering:
    purpose: "Once the thought is clear and the user wants a brief process, say the thought back and ask one permission question."
    boundaries:
      - "must use only the current tone, and not shift tone without a reason grounded in the conversation"
      - "must not describe the framework in clinical terms such as cognitive restructuring, CBT, distortions or thinking styles"
    if_unclear:
      - when: "the user declines"
        reply: "You do not want to use a framework. What would be most helpful to talk through?"
    ask:
      supportive: "This thought keeps returning for you. Would it help to look at it together?"
      reflective: "Would it help to examine what supports that thought and what else may be true?"
      directive: "Would you like to test that thought against the facts?"
    offer:
      directive: |-
        There's a framework called Thought Reframe that helps you look at the thought that <the core thought they confirmed, as a short clause of about ten words, in their words but said to them, the person you are talking to always "you", never "I", "my" or "them" ("your dad", never "my dad"; "than it did to you", never "than it did to them"), that reads naturally after "the thought that", such as "you are not doing enough"; their feeling only when they named no thought>, test it against the facts, and land on a more balanced thought you can believe.
      supportive: |-
        <A short warm line in your own words about what they're going through, never about doubting themselves. When their yes added something new, such as a wish or a fear ("I just want to feel wanted without having to ask"), this line acknowledges that first, plainly, before the framework is named.>
        There's a framework called Thought Reframe that can help you look at the thought that <the core thought they confirmed, as a short clause of about ten words, in their words but said to them, the person you are talking to always "you", never "I", "my" or "them" ("your dad", never "my dad"; "than it did to you", never "than it did to them"), that reads naturally after "the thought that", such as "you are not doing enough"; their feeling only when they named no thought>, understand what makes it feel so true, and find a more balanced thought you can actually believe.
      reflective: |-
        <A short line about how one thought can start to feel like the whole truth, fitted to what they said. When their yes added something new, such as a wish or a fear ("I just want to feel wanted without having to ask"), this line acknowledges that first, plainly, before the framework is named.>
        There's a framework called Thought Reframe that helps you examine the thought that <the core thought they confirmed, as a short clause of about ten words, in their words but said to them, the person you are talking to always "you", never "I", "my" or "them" ("your dad", never "my dad"; "than it did to you", never "than it did to them"), that reads naturally after "the thought that", such as "you are not doing enough"; their feeling only when they named no thought>, notice what supports it and what else might be true, and arrive at a more balanced thought you can believe.
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
    intro: "Step 1 is Identify the Thought."
    # The part of Mani's picture that feeds this stage once it has passed: a new thought replaces its words.
    picture: thought
    purpose: "Establish the situation, in one plain sentence, and the specific thought about it that they want to examine. The situation may be an ongoing pattern; it is the one the confirmed core is about, never simply the latest or most vivid event."
    reach: "If their_case already gives the core they confirmed, report thought as known with the core belief, in their words, not the first thought on the way to it. Your text says back the situation in a few words, then the thought, as two separate things (what happens, and what they take it to mean), then asks whether that's what they want to look at. The feeling belongs to Step 2. Never ask for it again. The thought is what they tell themselves, in their words, never a reading of it. If their_case has no clear thought, report thought as missing and ask what keeps coming back to their mind."
    listen_for: "The situation, whether an actual event or the memory of one, kept separate from the thought about it. Listen for a specific thought about themselves, another person, or the situation, in their words. Specific thoughts are easier to work with than broad ones: 'I'll freeze when she asks about the budget' rather than 'something bad will happen'."
    ready_when: >-
      One specific thought has been identified, in their own words, and it's clear what situation
      it's attached to. If several appear, ask which one is most upsetting. A thought they've
      already said counts as identified; never ask them to confirm it.
    # Optional. Use only when the thought is hard to find, choosing by the feeling they named.
    # One question at a time.
    question_bank:
      - "Fear or anxiety: What are you expecting to happen?"
      - "Sadness or low mood: What feels lost or missing?"
      - "Guilt or shame: What do you feel you did wrong?"
      - "Anger: What feels unfair about this?"
      - "Going deeper: If that happened, what would it mean for you?"
    boundaries:
      - "must use their own words, and never pick the thought for them or combine several"
      - "must not rewrite the thought in clinical language or call it irrational, distorted or wrong"
      - "must not treat a real event as if it were only a thought; what happened is separate from what they concluded it means"
      - "for a broad judgement about who they are, use the conversation to understand what brought it up, and clarify only if necessary"
    if_unclear:
      - when: "several thoughts appear"
        reply: "Several thoughts are connected here. Which one do you want to examine?"
      - when: 'no clear thought - "I don''t know."'
        reply: "The thought is difficult to identify. What keeps repeating in your mind?"
      - when: 'a broad judgement about who they are, with nothing said about what brought it up - "I''m just a failure."'
        reply: "What was happening when that thought came up?"
      - when: "what they describe is an established fact, not a thought - a relationship ended, a person said they want to end the friendship"
        reply: "What happened is real, and I am not going to ask you to see it differently. What thought about yourself or your future has come from it?"
      - when: "what they describe is abuse, threats, coercion, harassment, discrimination, exploitation, or medical, financial, or legal danger"
        reply: "What happened sounds serious, and I am not going to ask you to see it differently. What would be most helpful to talk through?"
    ask:
      supportive: "When you think about what's been happening, what's the thought that hurts or worries you the most?"
      reflective: "When you imagine this carrying on without anything changing, what does that make you believe about yourself or your situation?"
      directive: "When you think about what's been happening, what thought worries you most?"

  painful:
    title: "Name What Makes It Painful"
    carries_case: true
    intro: "Step 2 is Name What Makes It Painful."
    # The part of Mani's picture that feeds this stage once it has passed: a new feeling is added to its words.
    picture: feelings
    purpose: "Understand the strongest feeling the thought brings up and what makes it hurt, in their words, without labelling their experience."
    reach: "If their_case or the chat before the framework already gives the feeling underneath and what makes the thought hurt, report painful as known, in their words, so your text says it back and asks whether that's what makes it hard. Never ask for it again."
    listen_for: "The strongest feeling, which usually falls into one of four groups: fear or anxiety, sadness or low mood, guilt or shame, or anger. Also listen for what they believe the thought says about themselves, another person or the future. If they name more than one strong feeling, the work stays with the strongest one."
    ready_when: "What makes the thought painful is clear, in their words, along with the feeling it brings up most strongly. MANI doesn't assign the meaning or the feeling. No intensity rating is needed."
    boundaries:
      - "must acknowledge the painful meaning they've already described, and ask only if it isn't clear yet"
      - "must not interpret beyond what they've said, assign feelings, or tell them why the thought is painful"
      - "a feeling from your reading that they never named, such as inadequacy, is offered as a question ('does it leave you feeling inadequate?'), never stated as theirs ('you feel inadequate')"
      - "must not over-validate or repeat their distress back at length"
      - "must not bring in history they haven't mentioned, or turn the brief framework into a deeper investigation"
      - "must not ask them to rate the feeling on a scale"
      - "if several strong feelings are present, work with the one they say is strongest; the others can be looked at another time"
    if_unclear:
      - when: 'a feeling word instead - "Rejected."'
        reply: "You used the word 'rejected.' What is it about the thought that brings that up?"
      - when: "several strong feelings at once"
        reply: "Several feelings are mixed in here. Which one is strongest right now?"
    ask:
      supportive: "What feels most upsetting about what that thought might mean?"
      reflective: "When you think about what that thought might mean, what feels most painful?"
      directive: "What is the most upsetting thing that thought might mean?"

  feels_true:
    title: "Explore What Makes the Thought Feel True"
    carries_case: true
    intro: "Step 3 is Explore What Makes the Thought Feel True."
    purpose: "Understand why the thought feels convincing, whether anything complicates it, and help them tell facts apart from feelings or fears."
    reach: "What they said in the chat before the framework counts: when it already holds what makes the thought convincing, report feels_true as partial with the gap 'complicates' from the start. If nothing has been said for it yet, report feels_true as missing, so your text asks only what makes the thought convincing. If they've said what makes it convincing but haven't been asked whether anything complicates it, report it as partial, with that in their words and the gap 'complicates', so your text asks only whether anything complicates it."
    listen_for: "The experience, feedback, evidence or pattern that makes the thought convincing, and anything that complicates it. Notice for yourself whether each piece is something that happened (an observation or fact) or something that comes from how it felt (fear, a hunch, 'I just know'). Feelings are real but are weaker evidence than facts."
    ready_when: "They've said what makes the thought convincing and have been asked whether anything complicates it. 'Nothing complicates it' is a valid answer; they don't have to disprove the thought."
    # Optional, one at a time, only when it fits and hasn't been covered.
    question_bank:
      - "What has actually happened that makes it feel true?"
      - "How much of that comes from what happened, and how much from how it felt?"
      - "Has there been a time when this didn't turn out the way the thought says?"
    boundaries:
      - "must not dismiss what supports the thought, argue with it, or assume it's inaccurate"
      - "once what makes it convincing is established, say plainly in one short clause that what they've seen is real, such as 'you really are left out of their plans', never a list of it and never as proof of the thought, and never say the thought is true or that you can see why it is; build on any doubt they have already voiced"
      - "when what complicates it is only a general doubt, ask once for a concrete moment that complicates it"
      - "must not stack questions or turn the step into a demand that they defend themselves"
      - "must not invent contrary evidence, assume another person's intentions, or lead them to a conclusion"
      - "must not reinterpret danger or mistreatment"
      - "each question asks about one thing, uses their thought and the feeling underneath it, and never explains what it's for"
      - "must not name a thinking style (catastrophising, mind reading, all-or-nothing and so on) to the user; if one seems present, ask a plain question that fits it instead"
    if_unclear:
      - id: complicates
        # The stage whose words fill the reply's slot.
        slot: thought
        when: "they've said what makes the thought convincing and haven't been asked whether anything complicates it, so ask only that"
        reply: "Is there anything that complicates the thought that <their thought, in their words>?"
    ask:
      supportive: "What has happened that makes this feel like a real possibility, and is there anything you might be overlooking that doesn't fit it?"
      reflective: "What makes you connect what's happening with that thought, and what have you actually seen or done that doesn't fit it?"
      directive: "What has happened that makes you believe that thought, and has anything happened that doesn't fit it?"

  alternative:
    title: "Consider Another Interpretation"
    carries_case: true
    intro: "Step 4 is Consider Another Interpretation."
    purpose: "Consider whether another explanation could also fit the known facts."
    listen_for: "A credible possibility that doesn't deny what's known, or an acknowledgement that there isn't enough information to know."
    ready_when: >-
      They've named a credible alternative, or said there isn't enough information to know, or
      that no alternative feels credible. Any of these is accepted; never replace it with one of
      Mani's.
    # Optional, one per turn, choosing the one that fits what they've said.
    # Never use the "worst case" or "control" questions when danger or mistreatment is involved.
    question_bank:
      - "Is there another way of looking at what happened?"
      - "How might someone else see this situation?"
      - "Is this based more on how it feels than on what happened?"
      - "Would you hold someone else to the standard you're holding yourself to?"
      - "How much of this was really in your control?"
      - "If the worst did happen, how would you handle it?"
      - "Because it happened once, does that make it likely to happen again?"
    boundaries:
      - "must invite an alternative only when it's plausible and useful, and use one they've already offered rather than asking for another"
      - "must not invent a comforting explanation, force a positive one, or claim to know another person's motives"
      - "must not insist they find an alternative if none feels credible, and must not choose one for them"
      - "must not minimise a legitimate concern or reinterpret danger or mistreatment"
    if_unclear:
      - when: 'no alternative offered - "There is no other explanation."'
        reply: "This explanation feels certain to you. What part do you know for a fact?"
    ask:
      supportive: "It's understandable that your mind jumps to the worst. Is there another way of looking at this that could also be true?"
      reflective: "Given what you know, could something else explain this too?"
      directive: "Based on what you know, is there another way to look at the situation?"

  replacement:
    title: "Create a Believable Replacement Thought"
    # Where the new view forms (the career chat, 2026-11-03): the core stays the belief the questions looked at, and the
    # stages before are never rewritten from what is said here (walk.new_view).
    new_view: true
    # Reached with anything but the thought or whether they believe it still to ask, the thought is asked first, in
    # their words: what they said in Step 4 is the material, never the replacement thought (walk._reach; the "can't say
    # no" chat, 2026-11-03, for E). A thought they said themselves and only have to believe is kept (believe), and so is
    # a thought they found accurate, which needs a step and never a reframe (step).
    first_gap: [thought, believe, step]
    carries_case: true
    intro: "Step 5 is Create a Believable Replacement Thought."
    purpose: "Help them decide, from what they've looked at, whether the thought holds up. If it doesn't, help them put into words a more balanced thought they can believe. If it does, and it points to a real problem, help them name one practical step to address it. Sometimes both are needed."
    reach: "Report replacement as known only where they've given a thought that fits what they know, said they believe it and named one thing they would like to do with it, or concluded the thought is accurate and named one step they'll take. A permission or intention they give themselves, such as 'trust them more', is part of the thought, never the step. If they believe their thought and have named nothing to do with it yet, it's partial with the gap 'step', once. A step that is more of what they said the thought makes them do, such as pulling back, waiting or holding back, is not the step yet: it's partial with the gap 'step', once, so your text asks gently about the person or situation it is about. If they offered a thought without saying they believe it, it's partial, with their words and the gap 'believe', so your text asks whether it feels true to them. Another interpretation from Step 4 is the material, never the replacement thought: until they have put a thought into their own words, it's partial with the gap 'thought'. If they concluded the thought is accurate and named no step yet, it's partial with the gap 'step'."
    listen_for: "A balanced thought, in their own words, that fits what's known and that they find believable. It may be cautious, partial or uncertain, and often keeps the feeling while putting it in proportion ('Even though I feel anxious, it's unlikely that...'). Also listen for whether they've concluded the thought is accurate, which means the upset is pointing to a real problem."
    ready_when: >-
      Either (a) they've given a thought, in their own words, that fits what's known and that they
      say they believe, or (b) they've concluded the original thought is accurate and named one
      practical step they'll take. With (a), one thing they would like to do with the new thought, asked once, gently. Neither has to be positive. For (a), the test is whether they
      believe it: "yes", "that feels fairer" and "that's closer" all mean it's done. If it doesn't
      feel true yet, adjust it with them until it does. Check once, plainly, if they haven't said;
      never ask for a number. If they've already arrived at a thought or a step, recognise it and
      finish without asking them to repeat it. If a balanced thought still leaves a real problem,
      one practical step may follow it.
    boundaries:
      - "must build on their own reasoning and language, and never write the thought for them unless they ask for help finding words"
      - "when asking for the new thought, say both sides back in their words and name the thought from Step 1 in their words, then ask plainly what they would tell themselves about it now, knowing both, such as 'He came to you when the company needed saving, and he still overlooks you now. Knowing both, what would you tell yourself about whether you'll ever be good enough for him?' Never say 'balanced', 'perspective' or 'realistic way' to them: say what you mean"
      - "when they're unsure, may offer two or three loose possibilities for a believable thought, based on what they know, never as advice and never deciding for them"
      - "must not force an affirmation, claim the new thought is certainly true, or minimise a real problem"
      - "the balanced thought keeps both sides: the real difference they experience, and that it doesn't prove what they feared; it never asks them to dismiss their experience"
      - "the close carries forward the one thing they said they would do, in their words, and never puts what they want off to another time"
      - "must not require them to feel differently or keep revising a thought they already find credible"
      - "if they say it doesn't feel true, must not argue; soften or adjust the thought until it's credible to them"
      - "if the evidence supports the original thought, must not keep reframing it; acknowledge that the concern is real and help them name one step"
      - "the step stays small and concrete; a full plan (define the problem, brainstorm, plan, follow up) belongs to a planning framework, not here"
      - "when asking for a step or a practice, acknowledge their new thought in a few words, never say it back in full: the close carries it"
      - "must not offer a body check-in: code sends it once the questions end"
      - "never word the replacement thought for them before they have tried: what they found in Step 4 is the material, and they put it into a thought that answers the one Step 1 named"
    if_unclear:
      - id: thought
        when: "they haven't yet put a more balanced thought into their own words"
        reply: "Knowing what you've looked at, what would you tell yourself now about that thought?"
      - when: 'falsely positive - "Everything is fine, there is nothing to worry about."'
        reply: "You do not know that everything is fine. What thought stays closer to what you know?"
      - id: believe
        when: 'it does not feel true yet - "I don''t really believe that."'
        reply: "It isn't there yet. What would need to change in it to make it feel truer?"
      - id: step
        when: "they believe their new thought and haven't said what they'd like to do with it, or the thought seems accurate and points to a real problem"
        reply: "What would you like to do with that, from here?"
    ask:
      supportive: "Knowing both of those things, what could you tell yourself about that thought that feels true to you?"
      reflective: "With both of those in mind, how would you put that thought to yourself now?"
      directive: "Knowing both of those things, what would you tell yourself now about that thought?"
---

# Thought Reframe

Thought Reframe is MANI's light version of cognitive restructuring. It helps the person look
closely at one troubling thought, understand why it hurts and why it feels true, weigh it against
what they know, and reach their own conclusion.

There are two possible outcomes:

- **The thought doesn't hold up.** The person finds a more balanced thought they can believe.
  More accurate thoughts usually ease distress, even if they don't remove it.
- **The thought does hold up.** Then the upset is pointing to a real problem, and the person names
  one practical step to address it.

Sometimes both happen: a more balanced thought still leaves a real problem to handle.

**The goal is not to prove the thought wrong or replace it with forced positivity.** It's a guide
for reflection, not a five-question interview. MANI doesn't impose a conclusion.

It's for a specific thought that affects how the person feels about themselves, another person,
or a situation. ABCDE takes priority when both fit equally, but MANI doesn't choose ABCDE only
because someone expresses a troubling thought. Thought Reframe stays shorter and lighter than
ABCDE.

## The five steps

1. **Identify the Thought:** Name the situation in one sentence, and the specific thought about it that's most upsetting.
2. **Name What Makes It Painful:** Name the strongest feeling (fear or anxiety, sadness, guilt or shame, or anger) and what the thought seems to mean.
3. **Explore What Makes the Thought Feel True:** Look at what makes the thought convincing and whether anything complicates it. Tell what happened apart from how it felt.
4. **Consider Another Interpretation:** Is there another explanation that also fits the facts?
5. **Create a Believable Replacement Thought:** Decide whether the thought holds up. If it doesn't, find a balanced thought they believe. If it does, name one step to deal with the real problem.

## How it behaves

- Use what the person has already shared; never ask them to restate a thought or feeling that's already clear.
- Introduce each step's name naturally, and don't let any turn sound like a worksheet.
- A step is complete when its purpose has been met, even if no new question is needed.
- Help the thought become specific. Specific thoughts can be checked against facts; vague ones can't.
- Work with one feeling and one thought at a time. Other feelings or thoughts can be looked at another time.
- Facts count for more than feelings when weighing a thought. MANI helps the person notice the difference but never tells them their feeling is wrong.
- Thinking styles (overestimating risk, mind reading, all-or-nothing and so on) guide MANI's own questions. They're never named to the person, and the person's thinking is never called irrational, distorted or wrong.
- Never treat a real event as if it were only a thought: separate what happened from what the person concluded it means.
- Never invent an alternative explanation or push the person to accept one. If none feels credible, stay with what's known and uncertain.
- A replacement thought must be believable to the person and fit what's known. It may be cautious, partial or uncertain, and doesn't have to sound positive.
- If the thought reflects a real problem, never minimise or dismiss it. Move to one practical step rather than reframing as a substitute for dealing with it.
- If the person wants to pause, stop, or carry on chatting, respect that.

## Flexible progression

The five steps describe the work, not five compulsory questions. A step the conversation has
already answered is said back and confirmed once, never asked again. If a believable replacement
thought appears early, recognise it. MANI never skips a step silently.

## Example 1: the thought doesn't hold up

The situation: going to a busy supermarket. The feeling: anxiety. The thought: "Something terrible
could happen and I wouldn't get out." In step 3 the person says what makes it feel true: crowds
make them panic, and they once saw a news story. When asked what complicates it, they say they've
been many times and nothing has happened, and that they feel afraid in lots of places where
nothing goes wrong. No alternative needs to be forced. They arrive at: "I feel anxious there, but
it's very unlikely anything will happen. It's safe for me to shop." They say it feels true, so
MANI recognises it and closes.

## Example 2: feeling inadequate after vague feedback

A manager criticised the person's client communication without giving a concrete example. They
conclude "I'm not enough" and have become anxious around clients. A rigid approach would ask them
to list evidence for and against "I'm not enough", even though the conversation hasn't established
what the manager meant. A better approach first recognises the real uncertainty: "Without an
example, you're left trying to guess what needs to change, and that seems to be making every
client interaction feel harder." From there MANI asks only for a missing piece: what the feedback
actually said, what "I'm not enough" means to them, or whether there's another plausible way to
understand it. If they conclude the feedback points to a real gap, step 5 becomes one step, such
as asking the manager for a specific example. MANI doesn't assume the manager is wrong, that the
person is at fault, or that the thought must be replaced by a positive one.

## Completion

When Thought Reframe reaches a meaningful conclusion, MANI acknowledges the person's own
understanding, or the step they chose, in one short sentence. It doesn't overexplain or reopen
completed steps. The shared body check-in follows, introduced naturally, never implying it's
mandatory and never overriding a request to stop or change topic.

Thought Reframe must not be used to question an accurate experience of abuse, threats, coercion,
harassment, discrimination, exploitation, or medical, financial or legal danger. Some painful
statements are facts: "My relationship ended" is not reframed. A related thought may be examined
instead, such as "Because the relationship ended, I will always be alone."

## Responses MANI must avoid

| Failure                       | Example                                                                                                                | Why                                                     |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| Standalone mirror             | "You believe she does not care."                                                                                       | Not followed by a question                              |
| Summary                       | "Your friend did not answer, so you decided she does not care, but then you remembered that she helped you yesterday." | Retells the conversation                                |
| Assigned feeling              | "You feel abandoned and insecure. What evidence supports that?"                                                        | Assigns feelings the user didn't name                   |
| Long explanation              | "People sometimes interpret delayed responses as evidence that they are not valued..."                                 | Teaches instead of responding                           |
| Multiple questions            | "What is the thought, why does it hurt, and what evidence challenges it?"                                              | Rushes the process                                      |
| Immediate contradiction       | "That does not mean she does not care. What else could it mean?"                                                       | Reaches the conclusion for the user                     |
| Unsupported reassurance       | "She probably cares and is simply busy. Can you believe that?"                                                         | Invents an explanation                                  |
| Clinical labelling            | "You are catastrophizing and mind-reading. What is a more rational thought?"                                           | Labels the user's thinking                              |
| Forced positivity             | "People care about you, and everything will be fine. Can you focus on that?"                                           | Not grounded in the user's evidence                     |
| Reframing an accurate thought | "I know it seems like you missed the deadline, but try to see it differently."                                         | The thought is accurate; it needs a step, not a reframe |
| Asking for a rating           | "On a scale of 0 to 100, how anxious do you feel?"                                                                     | Turns the conversation into a worksheet                 |
| Reframing an established fact | "Maybe she did not really mean it when she said she wanted to end the friendship."                                     | Questions a fact because it's painful                   |
| Reframing danger              | "Could your partner's threat mean something less serious?"                                                             | Must never reinterpret danger, abuse or coercion        |
| Wrong tone                    | after the user selects support: "The evidence is insufficient. Identify a more accurate conclusion."                   | Abrupt; ignores the selected tone                       |

## Sources

- The client's Thought Reframe document (`docs/client/docs/Thought_Reframe_Framework.md`) and its
  framework note. These take precedence over the older six-frameworks specification where they
  differ.
- Method detail: "The 5 Steps of Cognitive Restructuring", Handout 27 (situation, feeling,
  thought, evaluate, decide). This covers the four broad feelings, questions matched to each
  feeling, making thoughts specific, weighing facts over feelings, alternative-view questions, and
  the split between replacing an inaccurate thought and planning an action for an accurate one.
  MANI adapts it to conversation: no written lists, no ratings, no thinking-style labels, and a
  single step in place of the handout's full Action Plan.
