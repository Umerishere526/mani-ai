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
    accept: Try It
    more: Tell Me More
    decline: Keep Chatting
  # A framework's own offer and Tell Me More, one per conversation style, sent instead of `text` and
  # `more_text` above. Literal: no {fields}. A framework listed here has all three styles, each with
  # both. The rest get the shared lines above until the client sends their wording.
  # Wording from the client's ABCDE Framework doc in docs/client-share-docs/, made general where it
  # quoted one person's words (muhammad, 2026-10-08).
  by_framework:
    abcde:
      direct:
        text: "There's a framework called ABCDE that helps you identify the thoughts behind how you're feeling, question whether they're true, and replace them with more realistic ones. Would you like to try it?"
        more_text: "The ABCDE framework has five steps:\n\n- A: Activating Event: What happened or what has been happening?\n- B: Belief: What did you start telling yourself about it?\n- C: Consequences: How did that thought affect how you felt or what you did?\n- D: Dispute: What makes you believe it's true, and what makes you question it?\n- E: Effective New Belief: What's a more realistic and helpful way to think about it?"
      supportive:
        text: "There's a framework called ABCDE that can help you understand the thoughts behind how you're feeling, see whether those thoughts are really true, and find a more helpful way to think about what's happening. Would you like to try it?"
        more_text: "The ABCDE framework has five steps. Each one helps you understand what happened, what you started believing about it, and how those thoughts may be affecting you.\n\n- A: Activating Event: What happened or what has been happening that brought up these feelings?\n- B: Belief: What did you begin telling yourself about the situation?\n- C: Consequences: How did that belief affect how you felt or what you did?\n- D: Dispute: What makes you believe that thought is true, and is there anything that might suggest otherwise?\n- E: Effective New Belief: What's a more realistic and helpful way to think about what happened?"
      reflective:
        text: "Sometimes the way we interpret what's happening can make a difficult situation feel even harder. There's a framework called ABCDE that helps you examine what you're telling yourself, understand how those thoughts affect you, and consider whether there's a more realistic way to see things. Would you like to try it?"
        more_text: "The ABCDE framework has five steps that help you examine how your interpretation of an experience influences what you believe and how you respond.\n\n- A: Activating Event: What happened or what has been happening that started these concerns?\n- B: Belief: What meaning did you give to what happened?\n- C: Consequences: How did that belief influence your feelings or actions?\n- D: Dispute: What supports your interpretation, and what might suggest a different understanding?\n- E: Effective New Belief: What's a more accurate and helpful way to understand the situation?"
