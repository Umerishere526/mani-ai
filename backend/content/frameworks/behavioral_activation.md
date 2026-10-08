---
id: behavioral_activation
name: Behavioral Activation
summary: "These questions help you identify what you have stopped doing and choose one realistic activity you can begin. By the end, you will have a specific, manageable action that helps you start moving forward again."
display_order: 3
phases: [offering, stopped, matters, choose, manageable, begin, barrier, closing]
activation:
  # Said anywhere in the conversation, this framework is ruled out as an offer and named in [ctx]:
  # early grief is not the avoidance it treats. Whole phrases, matched as the signals are.
  never_offer_when_said:
    - "died"
    - "passed away"
    - "passed on"
    - "funeral"
    - "put to sleep"
    - "no longer with us"
    - "bereaved"
    - "bereavement"
    - "grieving"
    - "grief"
  # Short fragments, not full example sentences - see abcde.md's activation block for why.
  strong_signals:
    - "but i cannot start"
    - "but i cannot begin"
    - "in bed all day"
    - "stopped answering"
    - "keep avoiding the task"
    # The open fragment, so "cannot make myself start", "begin", "get up" and "do anything"
    # all match. The two specific forms it replaces left the commonest phrasing routing nowhere.
    - "cannot make myself"
  signals:
    - "stopped cooking"
    - "not been getting dressed"
    - "stopped going outside"
    - "kept up with anything"
    - "no structure anymore"
    - "ignored everyone's messages"
    - "keep canceling plans"
    - "speak to anyone"
    - "stopped calling my family"
    - "when i feel ready"
    - "waiting to want to"
    - "i have no motivation"
    - "i will start tomorrow"
  redirects:
    - signal: "I do not know what I should do."
      instead: structured_problem_solving
    - signal: "I know what to do, but I am certain I will fail."
      instead: thought_reframe
    - signal: "I am about to send an angry message."
      instead: dbt_stop
    - signal: "I cannot change the situation, but I need to decide how to respond."
      instead: act_choice_point
  # The router's distinction rules, preferring this framework over the ones in `over`. Not
  # standalone: "cannot begin" is also "cannot begin to tell you", so it only reorders.
  distinctions:
    - name: knows what to do but cannot begin
      priority: 3
      phrases:
        - "know what to do but"
        - "know what i need to do but"
        - "cannot make myself"
        - "cannot get myself to begin"
        - "cannot start"
        - "cannot begin"
        - "difficulty beginning"
        - "no motivation"
        - "when i feel ready"
      over: [structured_problem_solving]
---
Starts when: you have learned what they have stopped or avoid doing, that they know what they could do but cannot begin, and what gets in the way, with no physical cause or recent death behind it.
Sounds like: "but I cannot start", "in bed all day", "I stopped answering", "I cannot make myself", "waiting to feel ready", plans cancelled and days without structure.
Skip when: mourning a recent loss, tiredness with nothing avoided, crashes after exertion, a medical or physical limit, not knowing what to do (structured_problem_solving), or one troubling thought (thought_reframe).
Stages: stopped (what they stopped or avoid) > matters (why it matters to them) > choose (one activity) > manageable (small enough for today) > begin (when, or on what cue) > barrier (the likely obstacle and what they will do) > closing (how it sits now)
Ends when: they have one small, safe action and when to begin it; they need not feel motivated, and nothing promises it will work.
Offer: mirror what has stopped and that they want to begin again, in their words, then ask if they want to find one small step together.
Never: lecture about motivation, pressure or blame them, pick the activity for them, or make the step bigger than they can manage today.
Never: suggest an activity that could put them at risk, or tell them to push through a physical limit, an illness, or what may need a professional to assess.
