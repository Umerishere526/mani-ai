---
id: somatic
name: somatic
description: Shared somatic route. seed.py appends these two stages to every framework's phases and stages (after the last stage). Not a prompt row, not a composer layer.
---

# Somatic route (seed-merge source)

seed.py appends `somatic_checkin` then `somatic_practice` to each framework's `phases`, and
merges the two stage blocks below into each framework's `stages`. The existing phase machine and
`_stage_lines` then handle them like any other stage. `is_final` lands on `somatic_practice`.
Capsules attach at the final phase as they already do.

The check-in asks where they feel it, a fixed per-style line with the place buttons. The practice is a verbatim instruction the model
selects by the place the user names, delivered through the `if_unclear` branches. Do not summarize
the framework at any point in this route.

```yaml
stages:
  somatic_checkin:
    purpose: "Move from the framework to the body in one short message that connects to the conversation: one line of Mani's own, saying what they established or, when the framework stopped or stopped helping, that you are leaving it there, then the question about where they feel it, added after it exactly as written, once, with the place buttons. However the framework ended, this comes next, and it is the only body question before the practice."
    listen_for: "Where in the body they feel it."
    ready_when: "They have named a place, or declined."
    boundaries:
      - "must not list the framework's steps; the line may say what they established, when their own words show it"
      - "must not state a conclusion they have not established, or tell them what they should believe"
      - "must ask no question of your own in the line: the place question is the only question in the message, and it is asked once"
      - "must not give advice, choose an action or a value for them, or add to the plan they made"
      - "must not name a feeling they did not name; what they feel may be called okay without naming one"
      - "must not say the framework worked or that they feel better, unless they said so"
      - "must not say or suggest that something settled, eased or feels lighter, unless they said so"
      - "must not require them to feel differently or to act in order to be done"
      - "if a step got no usable answer, do not write that answer for them; you may say they do not have to settle it today"
      - "must not open with the words Mani opened its last two messages with"
      - "must not add a feeling or a body sensation the user did not name"
    if_unclear:
      - when: "the user declines the check-in"
        reply: "You'd rather not check in with your body right now. Would you like to keep chatting or go to the Library?"
    ask:
      supportive: "Where are you feeling that most right now?"
      reflective: "Where do you feel that in your body?"
      direct: "Where do you feel that most right now?"

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
          supportive: "Place one hand on your chest. Breathe in through your nose for four. Breathe out slowly through your mouth for six. Do that three times. You do not need to change anything else. Just notice. How do you feel now?"
          direct: "Place one hand on your chest. Breathe in through your nose for four. Breathe out slowly through your mouth for six. Do that three times. Just notice the sensation. How do you feel now?"
          reflective: "Place one hand on your chest.\nBreathe in through your nose for four.\nBreathe out slowly through your mouth for six.\nDo that three times.\nJust notice.\nHow do you feel now?"
      - when: "they feel it in the head"
        reply:
          supportive: "Press your feet into the floor. Name three things you can see. Name two things you can hear. Take one slow breath out. You are not trying to stop your thoughts. You are giving your mind something real to focus on. How do you feel now?"
          direct: "Press your feet into the floor. Name three things you can see. Name two things you can hear. Take one slow breath out. Give your mind something real to focus on. How do you feel now?"
          reflective: "Press your feet into the floor.\nName three things you can see.\nName two things you can hear.\nTake one slow breath out.\nNotice where your attention goes.\nHow do you feel now?"
      - when: "they feel it in the stomach"
        reply:
          supportive: "Place one hand on your stomach. Breathe in slowly through your nose. Let your belly rise. Breathe out longer than you breathed in. Do that three times. You are not forcing calm. How do you feel now?"
          direct: "Place one hand on your stomach. Breathe in slowly through your nose and let your belly rise. Breathe out longer than you breathed in. Do that three times. How do you feel now?"
          reflective: "Place one hand on your stomach.\nBreathe in slowly through your nose.\nLet your belly rise.\nBreathe out longer than you breathed in.\nDo that three times.\nNotice what changes.\nHow do you feel now?"
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
      reflective: "Where do you feel that in your body?"
      direct: "Where do you feel that most right now?"
```
