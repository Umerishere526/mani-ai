---
id: 10000000-0000-0000-0000-000000000015
name: replies
type: system
description: The lines Mani sends without the model, word for word. Never sent to a model.
---

# Wording from the client spec, docs/specs/conversational-styles.md "Conversation opening": every
# conversation starts by asking how the person wants to be spoken to.
# The greeting opens every new conversation. {name} is the only field allowed.
greeting:
  new: "Hi {name}. It's MANI."
  returning: "Hi {name}, good to see you again."
  default_name: there
style_question: How would you like me to speak with you today?
# One button each, in this order. A tap is matched to its label ignoring case, so no two may match.
style_labels:
  direct: Direct
  supportive: Supportive
  reflective: Reflective
# What Mani says once a style is tapped.
openers:
  direct: How can I help you today?
  supportive: How can I support you today?
  reflective: What's on your mind today?
# The client's own check, asked at most once per conversation when several things have come up and
# it is unclear which matters most (muhammad, 2026-09-24: "never a new loop").
# Sent inside one [ctx] line, so no line may hold a newline, " | ", "[" or "]".
clarification_lines:
  - Do I have this right?
  - What would you like us to focus on today?
# Asked in this order, one per reply, once a framework has finished and the person carries on with
# the same issue - the client's "three forward-moving reflective questions".
after_framework_questions:
  - What feels most important about this now?
  - What do you think you need to do differently from here?
  - How could you take one small step toward that?
