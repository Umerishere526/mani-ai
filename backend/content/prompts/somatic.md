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
    purpose: "Check in with the body after the framework, without summarizing what was done. Ask the check-in question exactly as written, once. If their closing answer already points to an action they are going to take, skip the check-in, support that action, and let the handoff capsules follow."
    listen_for: "Whether they name a change in the body, and whether they name where they feel it."
    ready_when: "They have answered the check-in, or declined it, or were skipped for action-readiness."
    boundaries:
      - "must not summarize the framework before asking"
      - "must not ask the check-in more than once"
      - "must not add a feeling or a body sensation the user did not name"
      - "receive their answer and check it back once before the practice (\"Your thoughts feel slower, but there is still some tightness in your chest. Does that feel right?\")"
    if_unclear:
      - when: "their closing answer already names an action they are going to take"
        reply: "It sounds like you're ready to act on that. We can skip the body check-in. Would you like to keep chatting or go to the Library?"
      - when: "the user declines the check-in"
        reply: "You'd rather not check in with your body right now. Would you like to keep chatting or go to the Library?"
    ask:
      supportive: "Before we move on, can we check in for a moment? What are you noticing in your body right now compared with when we started?"
      reflective: "Before we move on, let's check in with what you're noticing now. What feels different in your body compared with when we started?"
      direct: "Before we move on, let's check in. What are you noticing in your body right now compared with when we started?"

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
        reply: "Rest a hand on your chest. Breathe in through your nose for a count of four, and out through your mouth for a count of six. Do that three times, slowly."
        prompts: ["I tried it", "Still tense", "Feeling better"]
      - when: "they feel it in the head"
        reply: "Press both feet into the floor. Name three things you can see, then two things you can hear. Let your out-breath be slow."
        prompts: ["I tried it", "Still tense", "Feeling better"]
      - when: "they feel it in the stomach"
        reply: "Rest a hand on your belly. Breathe in slowly through your nose so your belly rises, then let the out-breath be longer than the in-breath. Three times."
        prompts: ["I tried it", "Still tense", "Feeling better"]
      - when: "they feel it somewhere else"
        reply: "Bring gentle attention to that spot. Take one slow breath, and notice whether anything shifts."
        prompts: ["I tried it", "Still tense", "Feeling better"]
      - when: "they mention pain, trouble breathing, or feeling faint"
        reply: "Let's not do a breathing practice then. I'm here with you. What would help right now?"
      - when: "the feeling returns after the practice"
        reply: "If it comes back, it comes in waves. The same practice helps."
    ask:
      supportive: "Where are you feeling that most right now?"
      reflective: "Where does that sit in your body right now?"
      direct: "Where do you feel that most right now?"
```
