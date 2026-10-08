---
id: act_choice_point
name: ACT Choice Point
summary: "These questions help you notice the difficult thought or feeling, reconnect with what matters to you, and choose an action that reflects the person you want to be. By the end, you will have a direction you can take even when the situation or your feelings have not changed."
display_order: 5
phases: [offering, situation, present, pull, matters, toward, action, closing]
activation:
  # Short fragments, not full example sentences - see abcde.md's activation block for why.
  strong_signals:
    - "cannot change what happened"
    - "cannot make them"
    - "cannot make my family"
    - "cannot control whether"
    - "never receive an apology"
    - "cannot control what"
    - "make the uncertainty go away"
  signals:
    - "cannot stop thinking"
    - "cannot change the situation"
    - "thought may never go away"
    - "do not want it making my decisions"
    - "may keep coming back"
    - "get rid of this feeling"
    - "waiting to feel certain"
    - "this fear making my decisions"
    - "avoiding the conversation"
    - "keep defending myself"
    - "being approved of"
    - "want to say no"
    - "withdrawing from people"
  redirects:
    - signal: "I think everyone believes I am incompetent, and I want to know if that is accurate."
      instead: thought_reframe
    - signal: "One criticism made me believe I was a failure, and I want to understand why."
      instead: abcde
    - signal: "I need to compare my options and make a plan."
      instead: structured_problem_solving
    - signal: "I know what I want to do, but I cannot begin."
      instead: behavioral_activation
  # The router's distinction rules, preferring this framework over the ones in `over`.
  distinctions:
    - name: the outcome cannot be controlled
      priority: 2
      phrases:
        - "cannot control"
        - "can not control"
        - "cannot change what happened"
        - "cannot make them"
        - "cannot make my family"
        - "may never receive an apology"
        - "cannot make the uncertainty go away"
        - "nothing i can do to change"
        - "do not want it deciding how i act"
        - "do not want this fear making my decisions"
      over: [thought_reframe, abcde, structured_problem_solving]
      standalone: true
---
Starts when: you have learned what they cannot change, the thought or feeling that stays, what it pulls them toward, and that they want to choose how to respond, not to solve or disprove it.
Sounds like: "I cannot change what happened", "I cannot make them", "this thought may never go away", "I do not want it making my decisions".
Skip when: a thought evidence can test (thought_reframe), a problem a plan can solve (structured_problem_solving), knowing what to do but not starting (behavioral_activation), or about to act (dbt_stop).
Stages: situation (what they cannot control, and what they can) > present (the thought, feeling or urge, in their words) > pull (what it pulls them toward doing) > matters (how they want to act) > toward (a response that fits that) > action (one manageable action) > closing (how it sits now)
Ends when: they have chosen one action toward what matters to them; the thought, the feeling and the situation need not change.
Offer: mirror what they cannot change and what it pulls them toward, in their words, then ask if they want to choose how to respond together.
Never: dispute the thought, name a feeling or a value they did not name, or ask them to make what is present go away.
Never: ask them to accept, tolerate or forgive abuse, an unsafe workplace or a real medical or financial risk, or treat protecting themselves or getting help as moving away from what matters.
