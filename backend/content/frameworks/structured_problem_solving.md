---
id: structured_problem_solving
name: Structured Problem-Solving
summary: "We look at the problem, what you know for sure, what you want to happen and the options you have, then pick a first step."
display_order: 4
phases:
  [
    offering,
    problem,
    facts,
    control,
    outcome,
    options,
    compare,
    select,
    first_action,
  ]
activation:
  central_indication: >-
    A specific, practical problem exists and the user does not know what to do next - the
    situation can be influenced through a decision or action, and the user wants a direct
    solution rather than reflection alone.
  # How a person actually talks when this framework fits. The semantic router embeds
  # these, not central_indication: clinical prose scored 2/7 on real messages where
  # these scored 11/11. Authored content - changing them changes which framework is
  # offered, so they need the same review the summary does.
  exemplars:
    - "I have an exam tomorrow and I don't know where to start."
    - "I have too much to do and no idea what to tackle first."
    - "I need to decide between two options and I'm stuck."
    - "I'm behind on everything and I don't know where to begin."
    - "I have to sort this out with my landlord and I don't know what to say."
    # How people actually open, in a few words. A short opener matched no long
    # exemplar closely enough to clear the bar, so the framework was never reached.
    - "I don't know what to do about this problem."
    - "I don't know where to start."
    - "Everything is piling up and I can't get on top of it."
  to_find_out:
    - "the practical problem, in one sentence"
    - "whether a decision or an action could change it"
    - "whether it is one problem or several"
    - "whether they do not know what to do, as opposed to knowing and not starting"
  # Documentation of the specification: nothing in mani/ reads appropriate_when or not_when.
  # The prompt reads central_indication, to_find_out, distinctions and contraindications; the
  # router reads never_offer_when_said and stuck_offer.
  appropriate_when:
    - "The user has a specific practical problem"
    - "The problem can be influenced through action"
    - "The user does not know what to do"
    - "Several options require consideration"
    - "The user needs to make a decision"
    - "Several problems need separating"
    - "The user needs a realistic plan"
    - "The user wants a direct solution"
    - "The issue has been clearly identified and the user has agreed"
  not_when:
    - "The user wants to continue chatting without a framework, or has not agreed"
    - "The issue has not been clearly identified"
    - "The user already knows what to do but cannot begin"
    - "The central issue is one painful thought"
    - "The user wants deeper examination of an event and belief"
    - "The situation cannot be changed or influenced"
    - "The user is close to acting impulsively"
    - "A safety concern requires the approved safety protocol"
  contraindications:
    - "The decision requires professional expertise MANI cannot provide - a medical treatment plan, a legal conclusion, an investment or financial decision. Mani may help the person work out who could advise them, and must not replace qualified judgment"
    - "The plan would be retaliation, deception, an unsafe confrontation, or harm to the person or someone else"
    - "The situation is abuse, a threat, or emergency danger - it is never a communication problem or an ordinary decision, and the safety protocol applies, not a plan"
  distinctions:
    behavioral_activation: >-
      Structured Problem-Solving when the user does not know what to do, options need
      generating or comparing, a decision is required. Behavioral Activation when they already
      know what they could do, beginning is the barrier, and they need one manageable action.
    act_choice_point: >-
      Structured Problem-Solving when the problem can be influenced through action. ACT when the
      outcome remains outside control, facts remain uncertain, no practical solution resolves
      the central difficulty, or the user needs to choose how to respond.
    thought_reframe: >-
      Structured Problem-Solving when the user needs a plan. Reframe when one interpretation is
      preventing the user from seeing the situation accurately.
    continued_conversation: >-
      Continue chatting when the user does not want a framework, the problem is unclear, they
      want to be heard rather than decide, or are not ready to consider action.
stages:
  offering:
    purpose: "Mirror the identified problem and ask one permission question, once the problem and the wish for a plan are understood."
    boundaries:
      - "must not define the problem without the user"
      - "must not decide what outcome the user should want"
    if_unclear:
      - when: "the user declines"
        reply: "You do not want to work through a plan right now. What would be most helpful to discuss?"
    ask:
      supportive: "Several parts of this problem are competing for your attention. Would it help to take them one at a time?"
      reflective: "The facts, assumptions, and possible decisions are connected right now. Would it help to separate them?"
      direct: "You want a clear decision and first action. Would you like to work through the options?"
  problem:
    purpose: "Reduce a broad difficulty to one specific problem."
    listen_for: "One specific problem rather than several connected problems."
    ready_when: >-
      One specific problem is named. If several, the user chooses which one. What they said before
      they accepted counts, including the problem the offer was built on: when it already gives
      this, the step is done and is not asked.
    boundaries:
      - "must not define the problem for the user"
      - "must not combine several problems"
      - "must not select the priority without the user"
      - "must not turn an interpretation into a fact"
    if_unclear:
      - when: 'too broad - "Everything is falling apart."'
        reply: "Several problems are happening at once. Which one requires attention first?"
        start_only: true
      - when: "several combined"
        reply: "The deadline, your coworker, and your manager are separate concerns. Which one do you want to resolve first?"
        start_only: true
      - when: 'framed as unsolvable rather than named - "There''s no way to fix this, I could never figure it out."'
        reply: "It feels unsolvable right now. What is the actual problem underneath that?"
        start_only: true
      - when: "what they describe is abuse, a threat, or emergency danger"
        reply: "What is happening sounds serious, and staying safe comes first. What would be most helpful to talk through?"
      - when: "the problem is a medical, legal, or financial decision that needs a qualified professional"
        reply: "That decision needs someone qualified to advise. Would it help to think through who could help you with it?"
      - when: "they have already described the problem before the stage began - do not ask them to confirm it"
        reply: "<their problem, in a clause, in their words>. What do you know for certain about it?"
        start_only: true
    ask:
      supportive: "What is the main problem you want to sort out?"
      reflective: "What is the main problem you want to sort out?"
      direct: "What is the main problem you want to sort out?"
  facts:
    purpose: "Clarify what is known, what is believed, and what remains uncertain."
    listen_for: "Verified information, interpretations, predictions, and missing information."
    boundaries:
      - "must not call the user's assumption irrational"
      - "must not claim to know another person's intention"
      - "must not dismiss a reasonable prediction"
      - "must not require certainty before continuing"
    if_unclear:
      - when: 'prediction stated as fact - "My manager is going to fire me."'
        reply: "You expect your manager to fire you. What has she said or done?"
      - when: "not enough information"
        reply: "Her view is unknown. What information do you have?"
      - when: "a time critical risk is still open - cards or accounts that can still be used, a deadline about to pass, something that gets worse by the hour"
        reply: "<the risk, in a clause>. Contacting <whoever can stop it, such as the bank or the police> is usually the first step. Have you been able to reach them?"
    ask:
      supportive: "What do you know for certain?"
      reflective: "What do you know for certain?"
      direct: "What do you know for certain?"
  control:
    purpose: "Determine which part the user can influence."
    listen_for: "The decision, communication, boundary, preparation, or action available to the user."
    boundaries:
      - "must not imply the user controls another person"
      - "must not assign responsibility for another person's behaviour"
      - "must not encourage control over an uncontrollable outcome"
      - "must not treat abuse as a mutual communication problem"
    if_unclear:
      - when: 'focuses on another person - "I need my manager to understand."'
        reply: "Her understanding depends on her response. What can you control in how you communicate?"
      - when: 'they cannot say what is theirs to do - "I don''t know."'
        reply: "<two or three things that are plausibly theirs to do, in plain words>. Which of those have you already done?"
    ask:
      supportive: "Which part can you do something about?"
      reflective: "Which part can you do something about?"
      direct: "Which part can you do something about?"
  outcome:
    purpose: "Identify what the user wants the response to accomplish."
    listen_for: "A realistic result the user wants their response to support."
    boundaries:
      - "must not choose the desired outcome"
      - "must not promise the outcome is achievable"
      - "must not define success as receiving a particular response from someone else"
      - "must not pressure the user toward reconciliation, confrontation, forgiveness, or separation"
    if_unclear:
      - when: 'outcome too broad - "I want everything fixed."'
        reply: "You want the entire problem resolved. What would a realistic result from your next response be?"
      - when: 'they cannot say what they want - "I don''t know."'
        reply: "I'd say the result you want is <a plain draft of the obvious result for their situation>. Is that right, or is it something else?"
    ask:
      supportive: "What do you want to come out of this?"
      reflective: "What do you want to come out of this?"
      direct: "What do you want to come out of this?"
  options:
    purpose: "Identify realistic options without judging them immediately."
    listen_for: "More than one safe and realistic option when possible."
    boundaries:
      - "must not produce a long list of advice"
      - "must not present unsafe or unethical options"
      - "must not overwhelm the user"
      - "must not exclude the user from generating options"
      - "must not disguise a recommendation as the user's decision"
      - "must not accept several options that are really one approach worded differently - real breadth is at least two genuinely different approaches, not variations on the same one"
    if_unclear:
      - when: 'only one option - "The only thing I can do is quit."'
        reply: "Quitting is the only option you see right now. What other response could address the immediate problem?"
      - when: 'asks MANI to decide, or cannot name any option - "Tell me what to do." / "I don''t know." Do not ask for their options again'
        reply: "You want a direct answer. <Two or three realistic ways to start, in plain words, the most urgent first>. Which one feels most doable?"
    ask:
      supportive: "What could you do about it?"
      reflective: "What could you do about it?"
      direct: "What could you do about it?"
  compare:
    purpose: "Consider the relevant benefits, limitations, risks, and consequences of each option."
    listen_for: "The consequences, limitations, risks, timing, and fit of each response."
    boundaries:
      - "must not claim an option has no risk"
      - "must not exaggerate consequences"
      - "must not make legal, medical, financial, or professional conclusions"
      - "must not push the option MANI prefers"
    if_unclear:
      - when: 'only benefits named - "Email is easiest."'
        reply: "Email is the easiest option for you. What limitation could it have?"
      - when: 'only risks named - "Every option could go wrong."'
        reply: "Every option has a possible downside. Which risk is most manageable?"
    ask:
      supportive: "What is good and not so good about each of those?"
      reflective: "What is good and not so good about each of those?"
      direct: "What is good and not so good about each of those?"
  select:
    purpose: "Help the user choose the option that best fits the outcome and circumstances."
    listen_for: "The user's own decision and the reason it fits."
    boundaries:
      - "must not make the decision"
      - "must not pressure the user to choose quickly"
      - "must not praise one choice in a way that discourages reconsideration"
      - "must not treat uncertainty as failure"
    ask:
      supportive: "Which of those fits best?"
      reflective: "Which of those fits best?"
      direct: "Which of those fits best?"
  first_action:
    purpose: "Turn the selected response into one specific beginning."
    listen_for: "A specific, manageable action within the user's control."
    boundaries:
      - "must not create a complete project plan"
      - "must not make the first action too large"
      - "must not require immediate completion"
      - "must not select an action outside the user's control"
    if_unclear:
      - when: "action too large"
        reply: "Fixing the entire report is a large first action. What is the first manageable part?"
      - when: 'they cannot name a first action - "I don''t know."'
        reply: "A small first step could be <one concrete step that follows from what they chose>. Does that feel doable?"
    ask:
      supportive: "What is the first thing you would do?"
      reflective: "What is the first thing you would do?"
      direct: "What is the first thing you would do?"
---

# Structured Problem-Solving

Helps the user move from a broad or overwhelming practical problem toward one clear decision and
one realistic first action. When a problem feels large, the user may combine several problems,
mix facts with assumptions, focus on what cannot be controlled, struggle to identify the desired
outcome, generate no options or too many, revisit the problem without deciding, or know the
options but remain unable to choose. This framework slows the decision process into stages:
define the exact problem, separate facts from assumptions, identify what is within control,
establish the desired outcome, generate possible responses, compare them, select one, identify
the first action. **The purpose is not to solve the problem for the user** - MANI helps the user
develop and choose their own response.

**MANI does not define the problem without the user.** MANI does not decide what outcome the
user should want. **MANI does not choose the solution.** MANI does not provide a long list of
advice or present one option as risk-free.

**Must not be used to:** create a medical treatment plan, provide legal conclusions, make
investment or financial decisions for the user, plan retaliation, facilitate deception, plan an
unsafe confrontation, help the user harm themselves or another person, treat abuse as a
communication problem, or present emergency danger as an ordinary decision. MANI may help
identify appropriate professional support; **it must not replace qualified professional
judgment.**

## Stage progression

Define the problem -> Separate facts and assumptions -> Identify control -> Establish the
outcome -> Generate responses -> Compare responses -> Select one response -> Identify the first
action -> Complete.

## Worked example - direct solution tone

```
User:  I missed the report deadline, and I do not know what to say to my manager.

Offer
MANI:  You need to address the missed deadline with your manager. Would you like to work
       through the options?
User:  Yes.

Problem
MANI:  What is the exact problem you need to resolve?
User:  I need to tell her the report is late and explain when I can finish it.

Facts
MANI:  You need to disclose the delay and provide a new completion date. What do you know for
       certain?
User:  It was due yesterday, and I can finish it by Thursday.
MANI:  The deadline was yesterday, and Thursday is realistic. What are you assuming?
User:  That she will remove me from the project.

Control
MANI:  You expect to be removed from the project. Which part is within your control?
User:  I can tell her now, take responsibility, and explain how I will finish.

Outcome
MANI:  You can communicate now, take responsibility, and provide a plan. What do you want that
       response to accomplish?
User:  I want her to know I am addressing it and not hiding the delay.

Options
MANI:  You want to address the delay directly. What are your possible responses?
User:  I could email, call, or request a meeting.

Compare
MANI:  You could email, call, or request a meeting. Which differences matter most?
User:  Email is immediate and gives her the details. A call is more direct, but she may not be
       available.

Select
MANI:  Email is immediate, while a call depends on her availability. Which response best fits
       your outcome?
User:  I will email now and offer to speak.

First action
MANI:  You will email now and offer to speak. What is the first action?
User:  Write the opening sentence and take responsibility for missing the deadline.

Closing
MANI:  The first action is an opening sentence that takes responsibility. Is that plan realistic?
User:  Yes. I can write it now.

Somatic
MANI:  You can begin the email now. What do you notice in your body?
```

## Responses MANI must avoid

| Failure                                    | Example                                                                                                                      | Why                                                               |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| Standalone mirror                          | "You have several deadlines."                                                                                                | Not followed by a question                                        |
| Summary                                    | "You missed the report deadline, believe your manager will remove you, and need to decide whether to call or email."         | Retells several stages                                            |
| Labelling                                  | "You feel overwhelmed and afraid. What should you do?"                                                                       | Assigns feelings the user did not name                            |
| Long explanation                           | "Large problems often become easier when they are divided into smaller parts..."                                             | Teaches instead of responding                                     |
| Premature advice                           | "You should email your manager immediately."                                                                                 | MANI chooses the response                                         |
| Assumed motive                             | "Your manager will appreciate your honesty."                                                                                 | Cannot know how she will respond                                  |
| False certainty                            | "If you apologize, everything will be fine."                                                                                 | Promises an outcome                                               |
| Too many options                           | "You could email, call, schedule a meeting, ask a coworker, contact HR, finish the report tonight, or request an extension." | Overwhelms and takes over option generation                       |
| Multiple questions                         | "What is the problem, what outcome do you want, and what options do you have?"                                               | Several at once                                                   |
| Treating danger as a solvable disagreement | "What are your options for confronting the person who threatened you?"                                                       | Immediate danger requires the safety response                     |
| Professional overreach                     | "The legally correct choice is to refuse the agreement."                                                                     | Must not make legal conclusions                                   |
| Wrong framework                            | "What is the smallest part of the report you can complete?"                                                                  | The user first needs to decide how to address the missed deadline |
| Wrong tone                                 | "List your options and choose one."                                                                                          | Commanding; may contradict the selected tone                      |
