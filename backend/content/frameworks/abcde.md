---
id: abcde
name: ABCDE
summary: "These questions help you separate what happened from what you told yourself about it, question what may not be serving you, and come away with a clearer and more useful way of seeing the situation."
display_order: 1
phases: [offering, activate, belief, consequence, examine, balanced, closing]
activation:
  # Short fragments, not the full example sentences from the spec. router.py matches these as
  # whole words against what the person actually typed - a real message practically never
  # contains a whole authored sentence verbatim, but it very often contains the three or four
  # words that carry the pattern ("so i must be", "proves i will never"). Confidence now also
  # requires corroboration (two fragments, or one repeated) before a framework is offered, so
  # shortening these to raise recall no longer trades away precision the way it would have
  # before that gate existed.
  strong_signals:
    - "so i must be"
    - "must mean i am"
  signals:
    - "this proves i"
    - "proves i will never"
    - "everyone must think i am"
    - "i always ruin everything"
    - "i will always be alone"
    - "i know i will fail again"
    - "nothing will ever improve"
    - "has no respect for me"
    - "because nobody likes me"
    - "terrible at my job"
    - "because i do not matter"
    - "i failed once"
    - "wants me to fail"
    - "want me to fail"
    - "wanted me to fail"
    - "embarrassed me"
    - "embarassed me"
    - "humiliated me"
  redirects:
    - signal: "Nobody cares about me, and I want a quick way to look at that thought."
      instead: thought_reframe
    - signal: "I know what happened, but I need to decide what to do."
      instead: structured_problem_solving
    - signal: "I cannot control what happened, but I do not want it directing my choices."
      instead: act_choice_point
---
Starts when: you have learned the event that set it off, what it came to mean about them, and how believing that shapes what they feel or do, and they want to look at it in depth.
Sounds like: "so I must be", "this proves I", "everyone must think I am", one setback read as a verdict on who they are.
Skip when: one quick thought (thought_reframe), a decision or plan (structured_problem_solving), a thought evidence cannot settle (act_choice_point), withdrawal (behavioral_activation), or they only want to be heard.
Stages: activate (what happened, as seen, not why) > belief (what it came to mean) > consequence (how believing it affected them) > examine (what supports it, then what challenges it) > balanced (a fairer belief in their words) > closing (how it sits now)
Ends when: they hold a belief that fits all the evidence and sounds like them; they need not feel better, forgive, act or agree.
Offer: mirror what the event came to mean to them, in their words, then ask if they want to look at it together.
Never: invent evidence, guess anyone's motive, name a feeling or effect they did not name, or decide the belief is false.
Never: question whether abuse, threats, coercion, harassment, discrimination, exploitation or danger was real or as serious as it felt, or recast it as harmless.
