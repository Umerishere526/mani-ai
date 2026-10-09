---
id: somatic
name: somatic
description: Shared somatic route. seed.py appends these two stages to every framework's phases and stages (after `closing`). Not a prompt row, not a composer layer.
---

# Somatic route (seed-merge source)

seed.py appends `somatic_checkin` then `somatic_practice` to each framework's `phases`, and
merges the two stage blocks below into each framework's `stages`. The existing phase machine and
`_stage_lines` then handle them like any other stage. `is_final` lands on `somatic_practice`.
Capsules attach at the final phase as they already do.

The check-in question is a fixed per-style line. The practice is a verbatim instruction the model
selects by the place the user names, delivered through the `if_unclear` branches. Do not summarize
the framework at any point in this route.

```yaml
stages:
  somatic_checkin:
    purpose: "Check in with the body after the framework, without summarizing what was done. Ask the check-in question exactly as written, once; Mani's reflection of their last answer comes before it. If their closing answer already points to an action they are going to take, skip the check-in, support that action, and let the handoff capsules follow."
    listen_for: "Whether they name a change in the body, and whether they name where they feel it."
    ready_when: "They have answered the check-in, or declined it, or were skipped for action-readiness."
    boundaries:
      - "must not summarize the framework before asking"
      - "must not ask the check-in more than once"
      - "must not add a feeling or a body sensation the user did not name"
    if_unclear:
      - when: "their closing answer already names an action they are going to take"
        reply: "It sounds like you're ready to act on that. We can skip the body check-in. Would you like to keep chatting or go to the Library?"
      - when: "they agree to notice but have not said what they notice"
        reply: "What do you notice in your body?"
      - when: "the user declines the check-in"
        reply: "You'd rather not check in with your body right now. Would you like to keep chatting or go to the Library?"
    ask:
      supportive: "Would you like to notice what is happening in your body?"
      reflective: "What do you notice in your body?"
      direct: "What do you notice in your body now?"

  somatic_practice:
    purpose: "Offer one short grounding practice for where they feel it, then let the handoff capsules follow. Select the practice by the place the user names and deliver it word for word. Do not ask about the body a second time."
    listen_for: "Where in the body they feel it. If they already named a place in the check-in, use it and do not ask again."
    ready_when: "A practice has been offered for the place they named, or they were routed to the capsules by a skip, decline, or safety-out."
    boundaries:
      - "must not ask about the body a second time"
      - "must not give a practice if they mention pain, trouble breathing, or feeling faint - stay with them instead"
      - "must not summarize the framework"
      - "deliver the chosen practice exactly as written below; do not reword it"
    if_unclear:
      - when: "they have not said where they feel it"
        reply: "Where do you feel that most right now?"
        prompts: ["Chest", "Head", "Stomach", "Somewhere else"]
      - when: "they feel it in the chest"
        reply:
          supportive: "This makes sense given what you're dealing with. The chest is often where anxiety shows up when your body thinks something is at risk. Let's do something brief together. Place one hand on your chest. Breathe in through your nose for four. Breathe out slowly through your mouth for six. Do that three times. You do not need to change anything else. Just notice. How do you feel now?"
          direct: "The chest is often where anxiety shows up first. Let's do something brief together. Place one hand on your chest. Breathe in through your nose for four. Breathe out slowly through your mouth for six. Do that three times. Just notice the sensation. How do you feel now?"
          reflective: "When it shows up in your chest, that's often where the body reacts to perceived risk.\nLet's observe it for a moment.\nPlace one hand on your chest.\nBreathe in through your nose for four.\nBreathe out slowly through your mouth for six.\nDo that three times.\nJust notice.\nHow do you feel now?"
      - when: "they feel it in the head"
        reply:
          supportive: "When anxiety sits in the head, it usually shows up as racing or looping thoughts. Let's quiet that for a moment. Press your feet into the floor. Name three things you can see. Name two things you can hear. Take one slow breath out. You are not trying to stop your thoughts. You are giving your mind something real to focus on. How do you feel now?"
          direct: "When anxiety sits in the head, it usually shows up as looping thoughts. Let's quiet that for a moment. Press your feet into the floor. Name three things you can see. Name two things you can hear. Take one slow breath out. Give your mind something real to focus on. How do you feel now?"
          reflective: "When it shows up in your head, it often comes as racing or looping thoughts.\nPress your feet into the floor.\nName three things you can see.\nName two things you can hear.\nTake one slow breath out.\nNotice where your attention goes.\nHow do you feel now?"
      - when: "they feel it in the stomach"
        reply:
          supportive: "Anxiety in the stomach often shows up as knots, tightness, or a sinking feeling. Let's loosen that a bit. Place one hand on your stomach. Breathe in slowly through your nose. Let your belly rise. Breathe out longer than you breathed in. Do that three times. You are not forcing calm. You are giving your body a signal that it does not need to stay tense. How do you feel now?"
          direct: "Anxiety in the stomach often feels like knots or a sinking feeling. Let's loosen that. Place one hand on your stomach. Breathe in slowly through your nose and let your belly rise. Breathe out longer than you breathed in. Do that three times. This gives your body a signal that it doesn't need to stay tense. How do you feel now?"
          reflective: "When it shows up in your stomach, it often comes as knots, tightness, or a sinking feeling.\nPlace one hand on your stomach.\nBreathe in slowly through your nose.\nLet your belly rise.\nBreathe out longer than you breathed in.\nDo that three times.\nNotice what changes.\nHow do you feel now?"
      - when: "they feel it somewhere else"
        reply:
          supportive: "Wherever you feel it is fine. Let's bring gentle attention to that spot. Take one slow breath. You do not need to change anything. Just notice whether anything shifts. How do you feel now?"
          direct: "Bring gentle attention to that spot. Take one slow breath out. Notice whether anything shifts. How do you feel now?"
          reflective: "Wherever it sits is fine.\nBring gentle attention to that spot.\nTake one slow breath.\nNotice what shifts.\nHow do you feel now?"
      - when: "they mention pain, trouble breathing, or feeling faint"
        reply: "Let's not do a breathing practice then. I'm here with you. What would help right now?"
      - when: "the feeling returns after the practice"
        reply:
          supportive: "That is very common. Panic often comes in waves. Feeling it come back does not mean you are in danger or that this is failing. What matters is that you now know you can bring it down, even briefly. The next time it rises, do the same thing again. Short and simple. You are not alone in this. Just so you know, I have a whole library of tools that help with panic attacks, anytime and anywhere."
          direct: "That is very common. Panic often comes in waves. Feeling it return does not mean you are in danger. It just means you should do the same exercise again. You are not alone in this. I have a whole library of tools that help with panic anytime you need them."
          reflective: "I hear you noticing it calm for a moment and then come back. That's a common pattern with panic. You don't have to manage it on your own. I have a whole library of tools that help with panic attacks, anytime and anywhere."
    ask:
      supportive: "Where are you feeling that most right now?"
      reflective: "Where does that sit in your body right now?"
      direct: "Where do you feel that most right now?"
```
