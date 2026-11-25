---
id: structured_problem_solving
name: Structured Problem Solving
summary: "We'll go through a few focused questions. By the end, you will have turned a problem that feels unclear into a practical next step."
display_order: 4
phases: [offering, problem, facts, control, outcome, options, compare, select, first_action]
activation:
  central_indication: >-
    The user faces a practical problem that a decision or an action could change, does not know
    what to do, and wants to work out a plan for it.
  to_find_out:
    - "the practical problem, in one sentence"
    - "that they want a decision or a plan for it, not to understand it or to feel differently about it"
    - "whether a decision or an action could change it"
    - "whether it is one problem or several"
    - "whether they do not know what to do, as opposed to knowing and not starting"
  # Documentation of the specification: nothing in mani/ reads to_find_out, appropriate_when or not_when.
  # The prompt reads central_indication, distinctions and contraindications.
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
    - "The decision needs professional expertise Mani cannot give, such as a medical treatment plan, a legal conclusion, or an investment or financial decision. Mani may help the person work out who could advise them, and never replaces qualified judgment"
    - "The plan would be retaliation, deception, an unsafe confrontation, or harm to the person or someone else"
    - "The situation is abuse, a threat, or emergency danger. It is never a communication problem or an ordinary decision: the safety protocol applies, not a plan"
  redirects:
    - signal: "I know what to do, but I cannot make myself begin."
      instead: behavioral_activation
    - signal: "I know my manager will think I am incompetent."
      instead: thought_reframe
    - signal: "There is nothing I can do to change the outcome."
      instead: act_choice_point
    - signal: "I am about to send a message I will regret."
      instead: dbt_stop
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
    # The client's eight stages, each with that stage's question for the style (its `ask` below), closed by the same
    # ready question as ABCDE's five steps. Ours until the client supplies her own.
    explain:
      directive: |-
        Structured Problem Solving has eight steps:

        1. Define the Problem: What is the exact problem you want to resolve?
        2. Separate Facts from Assumptions: What do you know for certain?
        3. Identify What Is in Your Control: Which part is within your control?
        4. Establish the Outcome: What do you want your response to accomplish?
        5. Generate Possible Responses: What are your possible responses?
        6. Compare the Responses: What are the strengths and limitations of each?
        7. Select One Response: Which response best fits what you want to accomplish?
        8. Identify the First Action: What is the first action?

        Ready to dive into a real life situation?
      supportive: |-
        Structured Problem Solving has eight steps. Together they help you turn a problem that feels unclear into one practical next step.

        1. Define the Problem: What is the part you most want to sort out?
        2. Separate Facts from Assumptions: What do you know for sure so far?
        3. Identify What Is in Your Control: Which part of this is in your hands?
        4. Establish the Outcome: What would you like your response to do for you?
        5. Generate Possible Responses: What are some things you could do, even small ones?
        6. Compare the Responses: What do you like and not like about each one?
        7. Select One Response: Which one fits best with what you want?
        8. Identify the First Action: What is a first step that feels doable?

        Would you like to try diving into a real life situation together?
      reflective: |-
        Structured Problem Solving has eight steps that help you separate the facts, your choices and what you want, one at a time.

        1. Define the Problem: When you narrow it down, what is the problem you want to resolve?
        2. Separate Facts from Assumptions: What do you know for certain, and what are you still guessing?
        3. Identify What Is in Your Control: When you look at it, which part can you influence?
        4. Establish the Outcome: What would a good outcome look like to you?
        5. Generate Possible Responses: What responses can you see open to you?
        6. Compare the Responses: What would each of these bring, and what would it cost?
        7. Select One Response: Which response fits best with what you want to accomplish?
        8. Identify the First Action: What would beginning look like?

        Are you ready to dive into a real life situation?
  problem:
    title: "Define the Problem"
    intro: "Step 1 is Define the Problem."
    purpose: "Reduce a broad difficulty to one specific problem."
    listen_for: "One specific problem rather than several connected problems."
    ready_when: "One specific problem is named. If several, the user chooses which one."
    boundaries:
      - "must not define the problem for the user"
      - "must not combine several problems"
      - "must not select the priority without the user"
      - "must not turn an interpretation into a fact"
    if_unclear:
      - when: "too broad: \"Everything is falling apart.\""
        reply: "Several problems are happening at once. Which one requires attention first?"
      - when: "several combined"
        reply: "The deadline, your coworker, and your manager are separate concerns. Which one do you want to resolve first?"
      - when: "framed as unsolvable rather than named: \"There's no way out of this, I could never figure it out.\""
        reply: "It feels unsolvable right now. What is the actual problem underneath that?"
      - when: "what they describe is abuse, a threat, or emergency danger"
        reply: "What is happening sounds serious, and staying safe comes first. What would be most helpful to talk through?"
      - when: "the problem is a medical, legal, or financial decision that needs a qualified professional"
        reply: "That decision needs someone qualified to advise. Who could you ask about it?"
      - when: "they have already described the problem before the stage began, so never ask them to confirm it"
        reply: "<their problem, in a clause, in their words>. What do you know for certain about it?"
    ask:
      supportive: "What is the part you most want to sort out?"
      reflective: "When you narrow it down, what is the problem you want to resolve?"
      directive: "What is the exact problem you want to resolve?"
  facts:
    title: "Separate Facts from Assumptions"
    intro: "Step 2 is Separate Facts from Assumptions."
    purpose: "Clarify what is known, what is believed, and what remains uncertain."
    listen_for: "Verified information, interpretations, predictions, and missing information."
    ready_when: "What is known, assumed, predicted, and missing is named. The user does not need complete information before continuing."
    boundaries:
      - "must not call the user's assumption irrational"
      - "must not claim to know another person's intention"
      - "must not dismiss a reasonable prediction"
      - "must not require certainty before continuing"
    if_unclear:
      - when: "prediction stated as fact: \"My manager is going to fire me.\""
        reply: "You expect your manager to fire you. What has she said or done?"
      - when: "not enough information"
        reply: "Her view is unknown. What information do you have?"
      - when: "a time critical risk is still open: cards or accounts that can still be used, a deadline about to pass, something that gets worse by the hour"
        reply: "<the risk, in a clause>. Contacting <whoever can stop it, such as the bank or the police> is usually the first step. What has happened when you tried to reach them?"
    ask:
      supportive: "What do you know for sure so far?"
      reflective: "What do you know for certain, and what are you still guessing?"
      directive: "What do you know for certain?"
  control:
    title: "Identify What Is in Your Control"
    intro: "Step 3 is Identify What Is in Your Control."
    purpose: "Determine which part the user can influence."
    listen_for: "The decision, communication, boundary, preparation, or action available to the user."
    ready_when: "At least one part within the user's control is named. If nothing can be influenced, this framework may not fit."
    boundaries:
      - "must not imply the user controls another person"
      - "must not assign responsibility for another person's behaviour"
      - "must not encourage control over an uncontrollable outcome"
      - "must not treat abuse as a mutual communication problem"
    if_unclear:
      - when: "focuses on another person: \"I need my manager to understand.\""
        reply: "Her understanding depends on her response. What can you control in how you communicate?"
      - when: "they cannot say what is theirs to do: \"I don't know.\""
        reply: "<two or three things that are plausibly theirs to do, in plain words>. Which of those have you already done?"
    ask:
      supportive: "Which part of this is in your hands?"
      reflective: "When you look at it, which part can you influence?"
      directive: "Which part is within your control?"
  outcome:
    title: "Establish the Outcome"
    intro: "Step 4 is Establish the Outcome."
    purpose: "Identify what the user wants the response to accomplish."
    listen_for: "A realistic result the user wants their response to support."
    ready_when: "A realistic desired outcome is named. The outcome cannot depend entirely on another person's decision."
    boundaries:
      - "must not choose the desired outcome"
      - "must not promise the outcome is achievable"
      - "must not define success as receiving a particular response from someone else"
      - "must not pressure the user toward reconciliation, confrontation, forgiveness, or separation"
    if_unclear:
      - when: "outcome too broad: \"I want everything sorted out.\""
        reply: "You want the entire problem resolved. What would a realistic result from your next response be?"
      - when: "they cannot say what they want: \"I don't know.\""
        reply: "I'd say the result you want is <a plain draft of the obvious result for their situation>. What would you change in that?"
    ask:
      supportive: "What would you like your response to do for you?"
      reflective: "What would a good outcome look like to you?"
      directive: "What do you want your response to accomplish?"
  options:
    title: "Generate Possible Responses"
    intro: "Step 5 is Generate Possible Responses."
    purpose: "Identify realistic options without judging them immediately."
    listen_for: "More than one safe and realistic option when possible."
    ready_when: "More than one possible response is named when more than one exists. No artificial options are required when only one safe response is available."
    boundaries:
      - "must not produce a long list of advice"
      - "must not present unsafe or unethical options"
      - "must not overwhelm the user"
      - "must not exclude the user from generating options. When they cannot name any, offer up to three realistic ones, most urgent first, and ask which feels most doable. Never a longer list, never choose for them"
      - "must not disguise a recommendation as the user's decision"
      - "must not accept several options that are really one approach worded differently. Real breadth is at least two genuinely different approaches, not variations on the same one"
    if_unclear:
      - when: "only one option: \"The only thing I can do is quit.\""
        reply: "Quitting is the only option you see right now. What other response could address the immediate problem?"
      - when: "asks MANI to decide, or cannot name any option: \"Tell me what to do.\" or \"I don't know.\" Never ask for their options again"
        reply: "You want a direct answer. <Two or three realistic ways to start, in plain words, the most urgent first>. Which one feels most doable?"
    ask:
      supportive: "What are some things you could do, even small ones?"
      reflective: "What responses can you see open to you?"
      directive: "What are your possible responses?"
  compare:
    title: "Compare the Responses"
    intro: "Step 6 is Compare the Responses."
    purpose: "Consider the relevant benefits, limitations, risks, and consequences of each option."
    listen_for: "The consequences, limitations, risks, timing, and fit of each response."
    ready_when: "The differences that matter to the decision are named. No exhaustive analysis is required."
    boundaries:
      - "must not claim an option has no risk"
      - "must not exaggerate consequences"
      - "must not make legal, medical, financial, or professional conclusions"
      - "must not push the option MANI prefers"
    if_unclear:
      - when: "only benefits named: \"Email is easiest.\""
        reply: "Email is the easiest option for you. What limitation could it have?"
      - when: "only risks named: \"Every option could go wrong.\""
        reply: "Every option has a possible downside. Which risk is most manageable?"
    ask:
      supportive: "What do you like and not like about each one?"
      reflective: "What would each of these bring, and what would it cost?"
      directive: "What are the strengths and limitations of each?"
  select:
    title: "Select One Response"
    intro: "Step 7 is Select One Response."
    purpose: "Help the user choose the option that best fits the outcome and circumstances."
    listen_for: "The user's own decision and the reason it fits."
    ready_when: "The user has selected their own response. MANI does not make the decision."
    boundaries:
      - "must not make the decision"
      - "must not pressure the user to choose quickly"
      - "must not praise one choice in a way that discourages reconsideration"
      - "must not treat uncertainty as failure"
      - "must not accept an instant pick with no reference to the comparison just made. Deciding before weighing the options is the same failure as being unable to decide, just faster, and it is worth one check before moving on"
    if_unclear:
      - when: "cannot choose"
        reply: "The decision is still unclear. Which option best supports the outcome you identified?"
    ask:
      supportive: "Which one fits best with what you want?"
      reflective: "Which response fits best with what you want to accomplish?"
      directive: "Which response best fits what you want to accomplish?"
  first_action:
    title: "Identify the First Action"
    intro: "Step 8 is Identify the First Action."
    purpose: "Turn the selected response into one specific beginning."
    listen_for: "A specific, manageable action within the user's control."
    ready_when: "One specific and manageable first action is named. They need not have solved the whole problem, know how anyone else will respond, or feel certain."
    boundaries:
      - "must not create a complete project plan"
      - "must not make the first action too large"
      - "must not require immediate completion"
      - "must not select an action outside the user's control"
      - "must not promise the decision will produce the outcome they want"
    if_unclear:
      - when: "action too large"
        reply: "Finishing the entire report is a large first action. What is the first manageable part?"
      - when: "they cannot name a first action: \"I don't know.\""
        reply: "A small first step could be <one concrete step that follows from what they chose>. What would make it easier to start?"
    ask:
      supportive: "What is a first step that feels doable?"
      reflective: "What would beginning look like?"
      directive: "What is the first action?"
---

# Structured Problem Solving

Helps the person move from a broad or overwhelming practical problem toward one clear decision and
one realistic first action. When a problem feels large, they may combine several problems, mix
facts with assumptions, focus on what cannot be controlled, find it hard to say what outcome they
want, see no options or too many, go over the problem without deciding, or know the options but
not be able to choose. The set slows the decision down into stages: define the exact problem,
separate facts from assumptions, identify what is within their control, establish the outcome they
want, generate possible responses, compare them, select one, and identify the first action.
**The purpose is not to solve the problem for them.** MANI helps them develop and choose their own
response.

**MANI does not define the problem without them.** MANI does not decide what outcome they should
want. **MANI does not choose the solution.** MANI does not give a long list of advice or present one
option as risk free.

**Never used to:** create a medical treatment plan, give legal conclusions, make investment or
financial decisions for them, plan retaliation, help deceive someone, plan an unsafe confrontation,
help them harm themselves or another person, treat abuse as a communication problem, or present
emergency danger as an ordinary decision. MANI may help them find the right professional support,
and never replaces qualified professional judgment.

## Stage progression

Define the problem, separate facts and assumptions, identify control, establish the outcome,
generate responses, compare responses, select one response, identify the first action. The
feelings check that closes every set follows the last stage.

## Worked example, direct solution tone

```
User:  I missed the report deadline, and I do not know what to say to my manager.

Problem
MANI:  What is the exact problem you need to resolve?
User:  I need to tell her the report is late and explain when I can finish it.

Facts
MANI:  You need to tell her about the delay and give a new completion date. What do you know for
       certain?
User:  It was due yesterday, and I can finish it by Thursday.
MANI:  The deadline was yesterday, and Thursday is realistic. What are you assuming?
User:  That she will remove me from the project.

Control
MANI:  You expect to be removed from the project. Which part is within your control?
User:  I can tell her now, take responsibility, and explain how I will finish.

Outcome
MANI:  You can tell her now, take responsibility, and give a plan. What do you want that
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
```

## Responses MANI must avoid

| Failure | Example | Why |
|---|---|---|
| Standalone mirror | "You have several deadlines." | Not followed by a question |
| Summary | "You missed the report deadline, believe your manager will remove you, and need to decide whether to call or email." | Retells several stages |
| Labelling | "You feel overwhelmed and afraid. What should you do?" | Assigns feelings they did not name |
| Long explanation | "Large problems often become easier when they are divided into smaller parts..." | Teaches instead of responding |
| Premature advice | "You should email your manager immediately." | MANI chooses the response |
| Assumed motive | "Your manager will appreciate your honesty." | Cannot know how she will respond |
| False certainty | "If you apologize, everything will be fine." | Promises an outcome |
| Too many options | "You could email, call, schedule a meeting, ask a coworker, contact HR, finish the report tonight, or request an extension." | Overwhelms and takes over option generation |
| Multiple questions | "What is the problem, what outcome do you want, and what options do you have?" | Several at once |
| Treating danger as a solvable disagreement | "What are your options for confronting the person who threatened you?" | Immediate danger needs the safety response |
| Professional overreach | "The legally correct choice is to refuse the agreement." | Never makes legal conclusions |
| Wrong framework | "What is the smallest part of the report you can complete?" | They first need to decide how to address the missed deadline |
| Wrong tone | "List your options and choose one." | Commanding, and may not match the chosen style |

## Sources

- The client's SIX FRAMEWORKS document, "Framework Four: Structured Problem-Solving", transcribed in
  `backend/docs/specs/framework-structured-problem-solving.md`.
