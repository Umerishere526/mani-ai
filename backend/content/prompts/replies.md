---
id: 10000000-0000-0000-0000-000000000015
name: replies
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
  direct: Directive
  supportive: Supportive
  reflective: Reflective
# What Mani says once a style is tapped.
openers:
  direct: How can I help you today?
  supportive: How can I support you today?
  reflective: What's on your mind today?
# Asked in this order, one per reply, once a framework has finished and the person carries on with
# the same issue - the client's "three forward-moving reflective questions".
# Sent inside one [ctx] line, so no line may hold a newline, " | ", "[" or "]".
after_framework_questions:
  - What feels most important about this now?
  - What do you think you need to do differently from here?
  - How could you take one small step toward that?
# The offer the code writes when the model offers a set, filled from that framework's row: {name} is
# its name and {description} its summary, the only two fields allowed, and both are required.
# Wording from muhammad (2026-10-08) and the client's intro document in docs/client-share-docs/.
offer:
  text: "We'll go through a few focused questions. By the end, you will have turned a problem that feels unclear or overwhelming into a practical next step. Would it help to work through it together?\n\nFramework: {name}\n\n{description}"
  # What a tap on Tell me more gets until the client gives its own wording.
  more_text: "Framework: {name}\n\n{description}"
  # The three buttons, in this order. A tap is matched to its label ignoring case, so no two may match.
  labels:
    accept: "Yes, let's try it"
    more: Tell me more
    decline: I want to keep talking
