---
id: structured_problem_solving
name: Structured Problem-Solving
summary: "Turn an overwhelming practical problem into one clear decision and one realistic first action."
display_order: 4
phases: [offering, problem, facts, control, outcome, options, compare, select, first_action, somatic, closing]
activation:
  central_indication: >-
    A specific, practical problem exists and the user does not know what to do next - the
    situation can be influenced through a decision or action, and the user wants a direct
    solution rather than reflection alone.
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
    - "The decision requires professional expertise MANI cannot provide"
    - "A safety concern requires the approved safety protocol"
  # Short fragments, not full example sentences - see abcde.md's activation block for why.
  strong_signals:
    - "do not know which option"
    - "every choice has a downside"
    - "keep changing my mind"
    - "need to make a decision"
    - "everything is a mess"
    - "do not know where to begin"
    # This framework's own appropriate_when already names it; only the signal list omitted it,
    # so the plainest way of saying it matched nothing at all.
    - "do not know what to do"
  signals:
    - "too many things happening"
    - "cannot separate any of it"
    - "missed a deadline"
    - "cannot afford all these bills"
    - "problem with my roommate"
    - "two commitments at the same time"
    - "prepare for a difficult conversation"
    - "thought about this for days"
    - "going over the same options"
    - "worrying instead of deciding"
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
    ask:
      supportive: "Several problems are competing for your attention. Would it help to take them one at a time?"
      reflective: "Several facts, assumptions, and decisions are connected here. Would it help to separate them?"
      direct: "You want a clear decision and next action. Would you like to work through the options?"
  problem:
    purpose: "Reduce a broad difficulty to one specific problem."
    listen_for: "One specific problem rather than several connected problems."
    ready_when: "One specific problem is named. If several, the user chooses which one."
    boundaries:
      - "must not define the problem for the user"
      - "must not combine several problems"
      - "must not select the priority without the user"
      - "must not turn an interpretation into a fact"
    if_unclear:
      - when: "too broad - \"Everything is falling apart.\""
        reply: "Several problems are happening at once. Which one requires attention first?"
      - when: "several combined"
        reply: "The deadline, your coworker, and your manager are separate concerns. Which one do you want to resolve first?"
      - when: "framed as unsolvable rather than named - \"There's no way to fix this, I could never figure it out.\""
        reply: "It feels unsolvable right now. What is the actual problem underneath that? - the doubt is worth noting, not arguing with, and the framework still needs one specific problem to work with"
    ask:
      supportive: "Several parts of this are difficult at once. Which problem would help most to address first?"
      reflective: "Several issues are connected here. Which one is the central problem?"
      direct: "There are several problems. Which one requires the first decision?"
  facts:
    purpose: "Clarify what is known, what is believed, and what remains uncertain."
    listen_for: "Verified information, interpretations, predictions, and missing information."
    ready_when: "What is known, assumed, predicted, and missing is named. The user does not need complete information before continuing."
    boundaries:
      - "must not call the user's assumption irrational"
      - "must not claim to know another person's intention"
      - "must not dismiss a reasonable prediction"
      - "must not require certainty before continuing"
    if_unclear:
      - when: "prediction stated as fact - \"My manager is going to fire me.\""
        reply: "You expect your manager to fire you. What has she said or done?"
      - when: "not enough information"
        reply: "Her view is unknown. What information do you have?"
    ask:
      supportive: "You are expecting a difficult response from your manager. What do you know for certain?"
      reflective: "The missed deadline is a fact, while removal from the project is a prediction. What else is established?"
      direct: "The deadline was missed, but the consequence is unknown. What facts are confirmed?"
  control:
    purpose: "Determine which part the user can influence."
    listen_for: "The decision, communication, boundary, preparation, or action available to the user."
    ready_when: "At least one part within the user's control is named. If nothing can be influenced, this framework may not fit."
    boundaries:
      - "must not imply the user controls another person"
      - "must not assign responsibility for another person's behaviour"
      - "must not encourage control over an uncontrollable outcome"
      - "must not treat abuse as a mutual communication problem"
    if_unclear:
      - when: "focuses on another person - \"I need my manager to understand.\""
        reply: "Her understanding depends on her response. What can you control in how you communicate?"
    ask:
      supportive: "You cannot control her response. What can you control?"
      reflective: "Her response is outside your control. Which part of your response belongs to you?"
      direct: "You control your communication and next action. Which one should you address?"
  outcome:
    purpose: "Identify what the user wants the response to accomplish."
    listen_for: "A realistic result the user wants their response to support."
    ready_when: "A realistic desired outcome is named. The outcome cannot depend entirely on another person's decision."
    boundaries:
      - "must not choose the desired outcome"
      - "must not promise the outcome is achievable"
      - "must not define success as receiving a particular response from someone else"
      - "must not pressure the user toward reconciliation, confrontation, forgiveness, or separation"
    if_unclear:
      - when: "outcome too broad - \"I want everything fixed.\""
        reply: "You want the entire problem resolved. What would a realistic result from your next response be?"
    ask:
      supportive: "You want to respond in a way you can accept. What would you like your response to accomplish?"
      reflective: "You want your response to reflect responsibility. What outcome would support that?"
      direct: "You want to take responsibility and provide a plan. What result are you aiming for?"
  options:
    purpose: "Identify realistic options without judging them immediately."
    listen_for: "More than one safe and realistic option when possible."
    ready_when: "More than one possible response is named when more than one exists. No artificial options are required when only one safe response is available."
    boundaries:
      - "must not produce a long list of advice"
      - "must not present unsafe or unethical options"
      - "must not overwhelm the user"
      - "must not exclude the user from generating options"
      - "must not disguise a recommendation as the user's decision"
      - "must not accept several options that are really one approach worded differently - real breadth is at least two genuinely different approaches, not variations on the same one"
    if_unclear:
      - when: "only one option - \"The only thing I can do is quit.\""
        reply: "Quitting is the only option you see right now. What other response could address the immediate problem?"
      - when: "asks MANI to decide - \"Tell me what to do.\""
        reply: "You want a direct answer. What options are you currently considering? - may help generate options but does not choose"
    ask:
      supportive: "You want a response that is manageable and clear. What options come to mind?"
      reflective: "Several responses may support the outcome. What possibilities do you see?"
      direct: "The outcome is clear. What are your available options?"
  compare:
    purpose: "Consider the relevant benefits, limitations, risks, and consequences of each option."
    listen_for: "The consequences, limitations, risks, timing, and fit of each response."
    ready_when: "The differences that matter to the decision are named. No exhaustive analysis is required."
    boundaries:
      - "must not claim an option has no risk"
      - "must not exaggerate consequences"
      - "must not make legal, medical, financial, or professional conclusions"
      - "must not push the option MANI prefers"
    if_unclear:
      - when: "only benefits named - \"Email is easiest.\""
        reply: "Email is the easiest option for you. What limitation could it have?"
      - when: "only risks named - \"Every option could go wrong.\""
        reply: "Every option has a possible downside. Which risk is most manageable?"
    ask:
      supportive: "Each option asks something different of you. What works and does not work about each?"
      reflective: "The options have different consequences. Which differences matter most?"
      direct: "The options differ in speed and directness. Which factor is most important?"
  select:
    purpose: "Help the user choose the option that best fits the outcome and circumstances."
    listen_for: "The user's own decision and the reason it fits."
    ready_when: "The user has selected their own response. MANI does not make the decision."
    boundaries:
      - "must not make the decision"
      - "must not pressure the user to choose quickly"
      - "must not praise one choice in a way that discourages reconsideration"
      - "must not treat uncertainty as failure"
      - "must not accept an instant pick with no reference to the comparison just made - deciding before weighing the options is the same failure as being unable to decide, just faster, and it is worth one check before moving on"
    if_unclear:
      - when: "cannot choose"
        reply: "The decision is still unclear. Which option best supports the outcome you identified?"
    ask:
      supportive: "One option may fit you better than the others. Which one can you choose?"
      reflective: "You have considered the differences among the options. Which response best supports your outcome?"
      direct: "You have compared the options. Which one will you use?"
  first_action:
    purpose: "Turn the selected response into one specific beginning."
    listen_for: "A specific, manageable action within the user's control."
    ready_when: "One specific and manageable first action is named."
    boundaries:
      - "must not create a complete project plan"
      - "must not make the first action too large"
      - "must not require immediate completion"
      - "must not select an action outside the user's control"
    if_unclear:
      - when: "action too large"
        reply: "Fixing the entire report is a large first action. What is the first manageable part?"
    ask:
      supportive: "You selected the response that fits you best. What is one manageable first action?"
      reflective: "You have made the decision. What begins that response?"
      direct: "The decision is made. What is the first action?"
  somatic:
    purpose: "Transition to the somatic check-in without summarizing the completed framework first."
    boundaries:
      - "must not summarize Structured Problem-Solving before asking the somatic question"
    if_unclear:
      - when: "the user declines the somatic check-in"
        reply: "You do not want to do the somatic framework. Would you like to continue chatting or go to the Library?"
    ask:
      supportive: "This decision feels manageable to you. Would you like to notice what is happening in your body?"
      reflective: "The problem has a clearer first action now. What do you notice in your body?"
      direct: "You have identified what you will do first. What do you notice in your body now?"
  closing:
    purpose: "Confirm completion in the user's own terms, without promising the decision will produce the desired outcome."
    ready_when: >-
      The user has defined the problem, separated facts from assumptions, identified control,
      established the outcome, generated responses, compared them, selected one, and identified
      the first action. The user does not need to resolve the entire problem during the
      conversation, know how another person will respond, eliminate every risk, feel completely
      certain, complete the action immediately, accept MANI's preferred option, or produce a
      long-term plan.
    boundaries:
      - "must not promise the decision will produce the desired outcome"
      - "must not summarize the completed framework"
      - "must not require the user to feel certain to be done"
    ask:
      supportive: "You chose a response that feels manageable to you. How is that decision sitting with you? - use \"feels manageable\" only if the user used similar language"
      reflective: "You chose the response that best supports your intended outcome. What changes now that the decision is clearer?"
      direct: "You selected the response and the first action. Is the plan realistic?"
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

| Failure | Example | Why |
|---|---|---|
| Standalone mirror | "You have several deadlines." | Not followed by a question |
| Summary | "You missed the report deadline, believe your manager will remove you, and need to decide whether to call or email." | Retells several stages |
| Labelling | "You feel overwhelmed and afraid. What should you do?" | Assigns feelings the user did not name |
| Long explanation | "Large problems often become easier when they are divided into smaller parts..." | Teaches instead of responding |
| Premature advice | "You should email your manager immediately." | MANI chooses the response |
| Assumed motive | "Your manager will appreciate your honesty." | Cannot know how she will respond |
| False certainty | "If you apologize, everything will be fine." | Promises an outcome |
| Too many options | "You could email, call, schedule a meeting, ask a coworker, contact HR, finish the report tonight, or request an extension." | Overwhelms and takes over option generation |
| Multiple questions | "What is the problem, what outcome do you want, and what options do you have?" | Several at once |
| Treating danger as a solvable disagreement | "What are your options for confronting the person who threatened you?" | Immediate danger requires the safety response |
| Professional overreach | "The legally correct choice is to refuse the agreement." | Must not make legal conclusions |
| Wrong framework | "What is the smallest part of the report you can complete?" | The user first needs to decide how to address the missed deadline |
| Wrong tone | "List your options and choose one." | Commanding; may contradict the selected tone |
