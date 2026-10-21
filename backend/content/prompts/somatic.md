---
id: somatic
name: somatic
description: Shared somatic body check-in. seed.py appends these four stages to every framework's phases and stages (after the last content stage). Not a prompt row, not a composer layer.
---

# Somatic body check-in (seed-merge source)

The client's document "SOMATIC SECTION OF MANI" (2026-10-16, `docs/client/docs/`), sent word for word in one voice
for all three styles. Code owns the order and sends these texts; the model only reads a typed answer into one closed
`body` value and writes words where the document gives none (asking where, offering the closest exercise, a clarifying
question, Keep Chatting and Finish for Now). Buttons carry an `id` (what a tap or an answer means to code) and the
client's `label`. The exercises are unreviewed: a change to any line is a reseed, not a code change.

The buttons for the places a Somewhere Else answer can name are not in the document; they are ours. Step 1 follows the
framework's last stage directly, and No Tension is the way out for someone who does not want the check in.

seed.py appends `somatic_check`, `somatic_body`, `somatic_practice`, `somatic_effect` and `somatic_closing` to each
framework's `phases` and merges the five blocks below into its `stages`.

`somatic_check` is ours, not the client's: after a framework's last stage, when what Mani found before it (the
feelings they named and the feeling underneath) holds a word from `places`, Step 1 asks whether that feeling is still
felt in its place instead of the general question, with Yes and No. Yes is the exercise for that place; No is the
general question with its five buttons. Never during chat or inside a framework.

```yaml
stages:
  somatic_check:
    purpose: "Before Step 1, when a feeling they named usually sits in a place: asks whether it is still felt there. Ours, not the client's. Send the text; the model only reads a typed answer."
    script:
      text: "Earlier you mentioned feeling {feeling}, and that's often felt in the {place}. Is that still the case for you right now?"
      buttons:
        - {id: "yes", label: "Yes"}
        - {id: "no", label: "No"}
      places:
        chest: {place: chest, feelings: {anxious: anxious, anxiety: anxious, nervous: nervous}}
        head: {place: head, feelings: {stress: stressed, stressed: stressed, stressful: stressed}}
  somatic_body:
    purpose: "Step 1: the mind-body introduction and the place of any tension. Send the client's text; the model only reads a typed place."
    script:
      text: |-
        Now that we've worked through your thoughts, let's check in with your body.

        You may not realize it, but our emotions affect our bodies, too. When we're stressed or upset, we might feel tightness in our chest, discomfort in our stomach, or tension in our head.

        And even when we begin to feel clearer about what's bothering us, some of that physical tension can remain.

        That's why it's important to pay attention to how your body is feeling, too.

        Where are you noticing any tension or discomfort right now?
      question: "Where are you noticing any tension or discomfort right now?"
      buttons:
        - {id: chest, label: Chest}
        - {id: stomach, label: Stomach}
        - {id: head, label: Head}
        - {id: other, label: Somewhere Else}
        - {id: none, label: No Tension}
      other_buttons:
        - {id: jaw_face, label: Jaw or Face}
        - {id: hands, label: Hands or Fingers}
        - {id: eyes, label: Eyes}
        - {id: feet, label: Feet}
        - {id: toes, label: Toes}
        - {id: arms, label: Arms or Wrists}
      nearest_buttons:
        - {id: "yes", label: "Yes"}
        - {id: "no", label: No thanks}
      no_tension: |-
        That's good to hear. It sounds like your body is feeling comfortable right now. Before we finish, I'd love to know one thing. Thinking back to what brought you here today, do you feel this conversation helped you?
      no_tension_buttons:
        - {id: helped, label: "Yes, it helped"}
        - {id: somewhat, label: Somewhat}
        - {id: not_really, label: "No, not really"}
      no_tension_replies:
        helped: |-
          I'm glad our conversation was helpful. You can always come back whenever you need to talk something through.
        somewhat: |-
          I'm glad some of our conversation was helpful, even if it didn't address everything you needed.
        not_really: |-
          Thank you for telling me. I understand this conversation didn't give you the help you were looking for. I hope I can do better next time. I hope you'll come back.
      pain: "Let's not do a breathing practice then. I'm here with you. What would help right now?"
  somatic_practice:
    purpose: "Steps 2 and 3: one guided exercise for the place, then the check for physical change. The model never chooses or invents an exercise."
    script:
      exercises:
        chest: |-
          Let's bring your attention to your chest for a moment.

          Notice how it feels right now. Maybe there's some tightness, a feeling of heaviness, or tension you hadn't noticed before.

          Let's see if we can help those muscles relax a little.

          Take a gentle breath in through your nose for three seconds. Feel your chest expand naturally, allowing your ribs to move outward.

          Now slowly breathe out for six seconds, or for as long as feels comfortable. As you exhale, imagine some of that tightness beginning to soften.

          Let's try that again.

          Breathe in gently, feeling your chest expand.

          Now slowly breathe out, allowing your shoulders to drop and your chest muscles to relax.

          Continue for a few more comfortable breaths. There's no need to force anything.

          Now return to your natural breathing.

          Take a moment and notice how your chest feels. Does it feel a little softer, a little more relaxed, or perhaps about the same? Whatever you notice is okay.
        head: |-
          Let's bring your attention to your head.

          Notice where you might be holding tension. Maybe it's around your temples, across your forehead, or somewhere along your scalp.

          Let's give those areas a little attention.

          Start by rubbing your hands together until they feel warm.

          Now place your fingertips gently against your scalp and begin moving them in small, slow circles.

          Take your time. Let your fingers move across the top of your head, then toward your temples and around the sides.

          Keep the pressure gentle and comfortable.

          Now take a slow breath in.

          As you breathe out, see if you can soften the muscles around your forehead and temples.

          Continue those little circles for another moment, breathing naturally as you go.

          When you're ready, slowly lower your hands.

          Notice how your head feels now. Maybe something has softened, or maybe you're simply more aware of where you've been holding tension.
        stomach: |-
          Let's bring your attention to your stomach.

          Notice how it feels right now. Maybe there's some tightness, a little uneasiness, or that familiar feeling of having a knot in your stomach.

          Let's see if we can help your body relax a little.

          Place one or both hands gently over your belly.

          Feel the warmth of your hands resting there.

          Now take a comfortable breath in and notice your belly moving gently beneath your hands.

          As you breathe out, make a soft, low 'vooo' sound, almost like a gentle hum.

          You might notice a little vibration as you make the sound.

          Let's try that again.

          Take another comfortable breath in, then slowly release it with a low, gentle 'vooo.'

          There's no need to make the sound loudly or force your breathing. Just do what feels comfortable.

          Now let your breathing return to normal, keeping your hands resting gently on your stomach.

          Take a moment to notice what you feel beneath your hands. Maybe there's a little warmth, some movement, or a softening of the muscles.
        jaw_face: |-
          Let's bring your attention to your face, especially your jaw.

          Notice if your teeth are pressed together or if the muscles around your mouth feel tight.

          Sometimes we clench our jaws without even realizing we're doing it.

          Let's give those muscles a chance to relax.

          Start by allowing a little space between your upper and lower teeth.

          Now slowly open your mouth, almost as though you're beginning a gentle yawn.

          Feel the muscles around your jaw stretch a little, without forcing them.

          Let your mouth close naturally.

          Now take a comfortable breath in through your nose.

          As you breathe out, open your mouth slightly and release a long, gentle 'ahhh.'

          Let your jaw hang loosely as the sound comes out.

          Let's try that once more.

          Breathe in gently, then let another soft 'ahhh' carry your breath out.

          As you finish, allow your cheeks, lips, and jaw to relax.

          Now let your face rest naturally.

          Notice how your jaw feels when you're no longer deliberately tightening those muscles.
        hands: |-
          Let's bring your attention to your hands.

          Notice how they're feeling. Maybe your fingers are stiff, your palms feel tight, or you've been holding your hands in little fists without realizing it.

          Let's try something that helps you feel the difference between holding tension and releasing it.

          Slowly curl your fingers inward and make two gentle fists.

          As you breathe in, tighten your hands just enough to feel the muscles working.

          Hold that feeling for five seconds.

          Now breathe out and slowly open your hands, spreading your fingers and letting them relax.

          Notice the difference between how your hands felt when they were tight and how they feel now.

          Let's do that one more time.

          Gently close your hands as you breathe in.

          Hold for a moment.

          Now exhale and open your fingers, allowing your hands to relax completely.

          Let your hands rest comfortably in your lap or by your sides.

          Take a moment to notice any change in your fingers, palms, or the way your hands are resting.
        eyes: |-
          Let's bring your attention to your eyes.

          Notice how they feel right now. Maybe you've been staring at something for a long time, squinting, or holding tension around your eyes without realizing it.

          Let's give your eyes a chance to relax.

          Begin by slowly looking around the room.

          There's no need to turn your head very much. Just allow your eyes to move gently and comfortably.

          Find something that feels pleasant or neutral to look at.

          Let your eyes rest there for a moment.

          Notice its color, its shape, or something small about it.

          Now slowly move your eyes toward something else in the room.

          Take a comfortable breath in and out as you look at it.

          Find one more thing that catches your attention, something simple that you can look at without effort.

          Let your eyes rest there for another moment.

          Now allow your gaze to soften.

          Notice how the muscles around your eyes and forehead feel. You don't need to change anything. Just notice.
        feet: |-
          Let's bring your attention down to your feet.

          Notice how they're resting right now.

          If you're sitting, place both feet comfortably on the floor.

          Feel the ground beneath them.

          Let's begin with your heels.

          Gently press your heels into the floor and notice the contact beneath them.

          Now bring your attention to the balls of your feet, and then to your toes.

          Take a comfortable breath in as you gently press your feet a little more firmly against the floor.

          As you breathe out, release that pressure, allowing your feet to relax while keeping them resting on the ground.

          Let's try that again.

          Breathe in and gently press your feet downward.

          Now breathe out and let that pressure go.

          Notice how the floor continues to support your feet even when you're no longer pressing against it.

          Let your feet rest naturally.

          Take a moment to notice how they feel now, from your heels all the way to your toes.
        toes: |-
          Let's bring your attention all the way down to your toes.

          Notice how they feel right now. Maybe they're a little stiff, curled, or holding tension without you realizing it.

          Let's give those small muscles some attention.

          Start by gently curling your toes downward, almost as though you're trying to grip the floor.

          As you curl them, take a comfortable breath in.

          Hold that gentle curl for five seconds.

          Now slowly breathe out and release your toes, allowing them to relax completely.

          Notice the difference between holding them tightly and letting them go.

          Let's try that again.

          Gently curl your toes as you breathe in.

          Hold for a moment.

          Now breathe out and slowly uncurl them, allowing each toe to relax.

          If it feels comfortable, gently spread your toes apart and then let them rest naturally.

          Take one more easy breath.

          Notice how your toes and feet feel now. Maybe there's a little less tightness, or maybe you're simply more aware of those muscles than you were before.
        arms: |-
          Let's bring your attention to your arms and wrists.

          Notice how you're holding them right now. Maybe your arms feel heavy, your forearms are tight, or your wrists feel stiff.

          Let's give those muscles a chance to relax.

          Start by resting your arms comfortably in your lap or by your sides.

          Now slowly lift your forearms a little, keeping your elbows relaxed.

          Gently turn your palms upward, then slowly turn them downward.

          Notice how your wrists and forearms move as you do this.

          Let's try that again.

          Take a comfortable breath in as you turn your palms upward.

          Now breathe out as you slowly turn them downward.

          Keep the movement small and easy. There's no need to stretch beyond what feels comfortable.

          Now let your arms rest again.

          If it feels good, give your hands and wrists a little shake, as though you're gently shaking off a few drops of water.

          Then allow your arms to become loose and relaxed.

          Take a moment to notice how your arms and wrists feel now. Maybe they're a little less tense, or perhaps they simply feel different from when you started.
      check: |-
        Take a moment and notice how your body feels now. Has anything changed, even a little? It's okay if it hasn't.
      buttons:
        - {id: better, label: Feel Better}
        - {id: same, label: Feel the Same}
        - {id: worse, label: Feel Worse}
      replies:
        better: |-
          I'm glad you're feeling some relief. Sometimes giving your body a little attention can make a difference.
        same: |-
          That's okay. Sometimes our bodies need a little more time to relax. You can always come back to this exercise whenever you'd like. There's no need to force anything.
        worse: |-
          Thank you for telling me. Let's stop here. You don't need to continue anything that makes you uncomfortable. I hope you're feeling okay.
  somatic_effect:
    purpose: "Step 5: whether the whole conversation helped with what brought them. The physical response and this are recorded apart."
    script:
      question: |-
        Before we finish, I'd love to know one thing. Thinking back to what brought you here today, do you feel our conversation helped you?
      buttons:
        - {id: helped, label: "Yes, It Helped"}
        - {id: somewhat, label: Somewhat}
        - {id: not_really, label: "No, Not Really"}
      replies:
        helped: |-
          I'm glad our conversation was helpful. You can always come back whenever you need to talk something through.
        somewhat: |-
          I'm glad some of our conversation helped, even if we didn't work through everything. You're always welcome to come back and continue.
        not_really: |-
          Thank you for telling me. I understand this conversation didn't give you the help you were looking for. I hope I can do better next time. I hope you'll come back.
  somatic_closing:
    purpose: "Step 6: a natural closing with three choices. Keep Chatting continues from what Mani knows and repeats nothing answered; Go to Library opens the Library and picks no exercise; Finish for Now ends warmly with no question."
    script:
      buttons:
        - {id: keep_chatting, label: Keep Chatting}
        - {id: library, label: Go to Library}
        - {id: finish, label: Finish for Now}
```
