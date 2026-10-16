---
id: somatic
name: somatic
description: Shared somatic cadence. seed.py appends these four stages to every framework's phases and stages (after the framework's closing stage). Not a prompt row, not a composer layer.
---

# Somatic cadence (seed-merge source)

Lolly's SOMATIC SECTION OF MANI document of 2026-10-16
([transcription](../../../docs/client/messages/2026-10-16-somatic-cadence.md)), one voice for every
style: the mind-body introduction and where they notice tension (Chest, Stomach, Head, Somewhere Else,
No Tension), one exercise for that place, how their body feels now (Feel Better, Feel the Same, Feel
Worse), whether the conversation helped (Yes, It Helped, Somewhat, No, Not Really), then Keep Chatting,
Go to Library and Finish for Now. The body answer and the conversation answer are recorded apart
(`thread_technique_state.body_response`, `conversation_helped`). No Tension goes straight to whether the
conversation helped.

seed.py appends `somatic_checkin`, `somatic_practice`, `somatic_physical` then `somatic_helped` to each
framework's `phases`, and merges the blocks below into its `stages`. `is_final` lands on
`somatic_helped`. Each `if_unclear` branch has an `id`: a button tap or the reply's `body` names the
branch, and code sends its text word for word. Ours, not in her document, still to be shown to her:
`ask_known` (a sensation named earlier in the chat), `clarify`, `acting`, `declined`, `asked`,
`moved_on`, `eased`, `elsewhere`, `pain` and `no_place`'s question.

```yaml
stages:
  somatic_checkin:
    purpose: After the framework, introduce the mind-body connection and ask where they notice tension, without summarizing what was done. The check-in is sent word for word by code, with five choices under it; Mani's reflection of their last answer comes before it. If their closing answer already points to an action they are going to take, skip the check-in, support that action, and let the closing choices follow.
    listen_for: Where in the body they notice tension, that they notice none, or a sensation whose meaning is unclear.
    ready_when: They have named a place, said they notice no tension, declined, or were skipped for action-readiness.
    boundaries:
    - must not summarize the framework before asking
    - must not add a feeling or a body sensation the user did not name
    - 'must not decide what an unclear sensation means: burning eyes may be irritation, tiredness or tears'
    if_unclear:
    - id: no_tension
      when: they notice no tension or discomfort
      reply: That's good to hear. It sounds like your body is feeling comfortable right now. Before we finish, I'd love to know one thing. Thinking back to what brought you here today, do you feel this conversation helped you?
    - id: clarify
      when: they name a sensation that could mean more than one thing, such as burning eyes (irritation, tiredness or tears) or a heavy head (tired or tense). Ask in your text, in one question, what it is like for them; no exercise yet
    - id: acting
      when: their closing answer already names an action they are going to take
      reply: It sounds like you're ready to act on that. We can skip the body check-in.
    - id: declined
      when: the user declines the check-in
      reply: You'd rather not check in with your body right now. That's okay.
    - id: asked
      when: they ask about the check-in, or what it is for, instead of answering it. Answer them plainly in your text; the question is asked once more after it
    - id: moved_on
      when: they bring up something else instead, such as a new problem. Follow them in your text; the closing choices come under it
    - id: eased
      when: they say what they felt in their body has gone or eased. Say so in your text, no question; the closing choices come under it
    ask: 'Now that we''ve worked through your thoughts, let''s check in with your body.


      You may not realize it, but our emotions affect our bodies, too. When we''re stressed or upset, we might feel tightness in our chest, discomfort in our stomach, or tension in our head.


      And even when we begin to feel clearer about what''s bothering us, some of that physical tension can remain.


      That''s why it''s important to pay attention to how your body is feeling, too.


      Where are you noticing any tension or discomfort right now?'
    ask_known: 'Now that we''ve worked through your thoughts, let''s check in with your body.


      You may not realize it, but our emotions affect our bodies, too. When we''re stressed or upset, we might feel tightness in our chest, discomfort in our stomach, or tension in our head.


      And even when we begin to feel clearer about what''s bothering us, some of that physical tension can remain.


      That''s why it''s important to pay attention to how your body is feeling, too.


      Earlier you mentioned <body_said>. Where are you noticing any tension or discomfort right now?'
    ask_again: Where are you noticing any tension or discomfort right now?
  somatic_practice:
    purpose: Guide one exercise for the place they named, slowly, then ask whether anything changed. Code sends the exercise word for word. Never assume tension has been released.
    listen_for: Where in the body they feel it, when they chose Somewhere Else.
    ready_when: One exercise has been given for the place they named, or they were routed on by a decline or a safety-out.
    boundaries:
    - must not give an exercise if they mention pain, trouble breathing, or feeling faint - stay with them instead
    - must not summarize the framework
    if_unclear:
    - id: no_place
      when: they chose Somewhere Else or have not said where they feel it
      reply: Where in your body do you feel it?
    - id: chest
      when: they feel it in the chest
      reply: 'Let''s bring your attention to your chest for a moment.


        Notice how it feels right now. Maybe there''s some tightness, a feeling of heaviness, or tension you hadn''t noticed before.


        Let''s see if we can help those muscles relax a little.


        Take a gentle breath in through your nose for three seconds. Feel your chest expand naturally, allowing your ribs to move outward.


        Now slowly breathe out for six seconds, or for as long as feels comfortable. As you exhale, imagine some of that tightness beginning to soften.


        Let''s try that again.


        Breathe in gently, feeling your chest expand.


        Now slowly breathe out, allowing your shoulders to drop and your chest muscles to relax.


        Continue for a few more comfortable breaths. There''s no need to force anything.


        Now return to your natural breathing.


        Take a moment and notice how your chest feels. Does it feel a little softer, a little more relaxed, or perhaps about the same? Whatever you notice is okay.'
    - id: head
      when: they feel it in the head, temples, forehead or scalp
      reply: 'Let''s bring your attention to your head.


        Notice where you might be holding tension. Maybe it''s around your temples, across your forehead, or somewhere along your scalp.


        Let''s give those areas a little attention.


        Start by rubbing your hands together until they feel warm.


        Now place your fingertips gently against your scalp and begin moving them in small, slow circles.


        Take your time. Let your fingers move across the top of your head, then toward your temples and around the sides.


        Keep the pressure gentle and comfortable.


        Now take a slow breath in.


        As you breathe out, see if you can soften the muscles around your forehead and temples.


        Continue those little circles for another moment, breathing naturally as you go.


        When you''re ready, slowly lower your hands.


        Notice how your head feels now. Maybe something has softened, or maybe you''re simply more aware of where you''ve been holding tension.'
    - id: stomach
      when: they feel it in the stomach or belly
      reply: 'Let''s bring your attention to your stomach.


        Notice how it feels right now. Maybe there''s some tightness, a little uneasiness, or that familiar feeling of having a knot in your stomach.


        Let''s see if we can help your body relax a little.


        Place one or both hands gently over your belly.


        Feel the warmth of your hands resting there.


        Now take a comfortable breath in and notice your belly moving gently beneath your hands.


        As you breathe out, make a soft, low ''vooo'' sound, almost like a gentle hum.


        You might notice a little vibration as you make the sound.


        Let''s try that again.


        Take another comfortable breath in, then slowly release it with a low, gentle ''vooo.''


        There''s no need to make the sound loudly or force your breathing. Just do what feels comfortable.


        Now let your breathing return to normal, keeping your hands resting gently on your stomach.


        Take a moment to notice what you feel beneath your hands. Maybe there''s a little warmth, some movement, or a softening of the muscles.'
    - id: jaw
      when: they feel it in the jaw or face, or are clenching their teeth
      reply: 'Let''s bring your attention to your face, especially your jaw.


        Notice if your teeth are pressed together or if the muscles around your mouth feel tight.


        Sometimes we clench our jaws without even realizing we''re doing it.


        Let''s give those muscles a chance to relax.


        Start by allowing a little space between your upper and lower teeth.


        Now slowly open your mouth, almost as though you''re beginning a gentle yawn.


        Feel the muscles around your jaw stretch a little, without forcing them.


        Let your mouth close naturally.


        Now take a comfortable breath in through your nose.


        As you breathe out, open your mouth slightly and release a long, gentle ''ahhh.''


        Let your jaw hang loosely as the sound comes out.


        Let''s try that once more.


        Breathe in gently, then let another soft ''ahhh'' carry your breath out.


        As you finish, allow your cheeks, lips, and jaw to relax.


        Now let your face rest naturally.


        Notice how your jaw feels when you''re no longer deliberately tightening those muscles.'
    - id: hands
      when: they feel it in the hands or fingers
      reply: 'Let''s bring your attention to your hands.


        Notice how they''re feeling. Maybe your fingers are stiff, your palms feel tight, or you''ve been holding your hands in little fists without realizing it.


        Let''s try something that helps you feel the difference between holding tension and releasing it.


        Slowly curl your fingers inward and make two gentle fists.


        As you breathe in, tighten your hands just enough to feel the muscles working.


        Hold that feeling for five seconds.


        Now breathe out and slowly open your hands, spreading your fingers and letting them relax.


        Notice the difference between how your hands felt when they were tight and how they feel now.


        Let''s do that one more time.


        Gently close your hands as you breathe in.


        Hold for a moment.


        Now exhale and open your fingers, allowing your hands to relax completely.


        Let your hands rest comfortably in your lap or by your sides.


        Take a moment to notice any change in your fingers, palms, or the way your hands are resting.'
    - id: eyes
      when: they feel tension around the eyes, from staring or squinting, and have said it is tension rather than tears, tiredness or irritation
      reply: 'Let''s bring your attention to your eyes.


        Notice how they feel right now. Maybe you''ve been staring at something for a long time, squinting, or holding tension around your eyes without realizing it.


        Let''s give your eyes a chance to relax.


        Begin by slowly looking around the room.


        There''s no need to turn your head very much. Just allow your eyes to move gently and comfortably.


        Find something that feels pleasant or neutral to look at.


        Let your eyes rest there for a moment.


        Notice its color, its shape, or something small about it.


        Now slowly move your eyes toward something else in the room.


        Take a comfortable breath in and out as you look at it.


        Find one more thing that catches your attention, something simple that you can look at without effort.


        Let your eyes rest there for another moment.


        Now allow your gaze to soften.


        Notice how the muscles around your eyes and forehead feel. You don''t need to change anything. Just notice.'
    - id: feet
      when: they feel it in the feet
      reply: 'Let''s bring your attention down to your feet.


        Notice how they''re resting right now.


        If you''re sitting, place both feet comfortably on the floor.


        Feel the ground beneath them.


        Let''s begin with your heels.


        Gently press your heels into the floor and notice the contact beneath them.


        Now bring your attention to the balls of your feet, and then to your toes.


        Take a comfortable breath in as you gently press your feet a little more firmly against the floor.


        As you breathe out, release that pressure, allowing your feet to relax while keeping them resting on the ground.


        Let''s try that again.


        Breathe in and gently press your feet downward.


        Now breathe out and let that pressure go.


        Notice how the floor continues to support your feet even when you''re no longer pressing against it.


        Let your feet rest naturally.


        Take a moment to notice how they feel now, from your heels all the way to your toes.'
    - id: toes
      when: they feel it in the toes
      reply: 'Let''s bring your attention all the way down to your toes.


        Notice how they feel right now. Maybe they''re a little stiff, curled, or holding tension without you realizing it.


        Let''s give those small muscles some attention.


        Start by gently curling your toes downward, almost as though you''re trying to grip the floor.


        As you curl them, take a comfortable breath in.


        Hold that gentle curl for five seconds.


        Now slowly breathe out and release your toes, allowing them to relax completely.


        Notice the difference between holding them tightly and letting them go.


        Let''s try that again.


        Gently curl your toes as you breathe in.


        Hold for a moment.


        Now breathe out and slowly uncurl them, allowing each toe to relax.


        If it feels comfortable, gently spread your toes apart and then let them rest naturally.


        Take one more easy breath.


        Notice how your toes and feet feel now. Maybe there''s a little less tightness, or maybe you''re simply more aware of those muscles than you were before.'
    - id: arms
      when: they feel it in the arms or wrists
      reply: 'Let''s bring your attention to your arms and wrists.


        Notice how you''re holding them right now. Maybe your arms feel heavy, your forearms are tight, or your wrists feel stiff.


        Let''s give those muscles a chance to relax.


        Start by resting your arms comfortably in your lap or by your sides.


        Now slowly lift your forearms a little, keeping your elbows relaxed.


        Gently turn your palms upward, then slowly turn them downward.


        Notice how your wrists and forearms move as you do this.


        Let''s try that again.


        Take a comfortable breath in as you turn your palms upward.


        Now breathe out as you slowly turn them downward.


        Keep the movement small and easy. There''s no need to stretch beyond what feels comfortable.


        Now let your arms rest again.


        If it feels good, give your hands and wrists a little shake, as though you''re gently shaking off a few drops of water.


        Then allow your arms to become loose and relaxed.


        Take a moment to notice how your arms and wrists feel now. Maybe they''re a little less tense, or perhaps they simply feel different from when you started.'
    - id: elsewhere
      when: they feel it somewhere none of the other places names, such as the back or the neck
      reply: 'Let''s bring your attention to that spot.


        Notice how it feels right now, without trying to change it.


        Take a comfortable breath in.


        As you breathe out, see if the muscles there can soften, even a little.


        Let''s try that once more.


        Breathe in gently, and as you breathe out, let that area rest.


        Now let your breathing return to normal and notice how that spot feels.'
    - id: pain
      when: they mention pain, trouble breathing, or feeling faint
      reply: Let's not do a physical exercise then. I'm here with you. What would help right now?
    ask: Where in your body do you feel it?
  somatic_physical:
    purpose: 'After the exercise: how their body feels now. Code sends the client''s reply for their answer, then the question whether the conversation helped. Never repeat the exercise, never push through discomfort, never another physical exercise.'
    listen_for: Whether they feel better, the same, or worse.
    ready_when: They said how their body feels now.
    if_unclear:
    - id: better
      when: they feel better, lighter or calmer in their body
      reply: I'm glad you're feeling some relief. Sometimes giving your body a little attention can make a difference.
    - id: same
      when: they feel about the same, or nothing changed
      reply: That's okay. Sometimes our bodies need a little more time to relax. You can always come back to this exercise whenever you'd like. There's no need to force anything.
    - id: worse
      when: they feel worse, more uncomfortable, or the exercise hurt
      reply: Thank you for telling me. Let's stop here. You don't need to continue anything that makes you uncomfortable. I hope you're feeling okay.
    ask: Take a moment and notice how your body feels now. Has anything changed, even a little? It's okay if it hasn't.
  somatic_helped:
    purpose: Whether the whole conversation helped with what brought them here, recorded apart from how their body feels. Code sends the client's reply for their answer, then Keep Chatting, Go to Library and Finish for Now. No defensiveness, no repetition, no further question.
    listen_for: Whether they feel the conversation helped, somewhat helped, or did not.
    ready_when: They said whether the conversation helped.
    if_unclear:
    - id: helped
      when: they say the conversation helped
      reply: I'm glad our conversation was helpful. You can always come back whenever you need to talk something through.
    - id: somewhat
      when: they say it helped somewhat, or partly
      reply: I'm glad some of our conversation helped, even if we didn't work through everything. You're always welcome to come back and continue.
    - id: not_helped
      when: they say it did not really help
      reply: Thank you for telling me. I understand this conversation didn't give you the help you were looking for. I hope I can do better next time. I hope you'll come back.
    ask: Before we finish, I'd love to know one thing. Thinking back to what brought you here today, do you feel our conversation helped you?
```
