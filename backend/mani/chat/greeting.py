# ABOUTME: Mani's fixed, client-authored lines: the greeting, the style choice, each style's
# ABOUTME: opener, and the offer explanation. Written here rather than generated, so they cost nothing.

DEFAULT_NAME = "there"

# Wording from the client spec, docs/specs/conversational-styles.md "Conversation opening":
# every conversation starts by asking how the person wants to be spoken to.
STYLE_QUESTION = "How would you like me to speak with you today?"

# The greeting's buttons. `style` is read back by the backend when one is tapped; the client
# only ever sends the label, exactly as it does for every other button.
STYLE_OPTIONS = [
    {"label": "Directive", "style": "directive"},
    {"label": "Supportive", "style": "supportive"},
    {"label": "Reflective", "style": "reflective"},
]

# What Mani says once a style is chosen - fixed wording from the same spec.
OPENERS = {
    "directive": "How can I help you today?",
    "supportive": "How can I support you today?",
    "reflective": "What's on your mind today?",
}


def greeting(nickname: str | None, returning: bool) -> str:
    name = nickname or DEFAULT_NAME
    hello = f"Hi {name}, good to see you again." if returning else f"Hi {name}. It's MANI."
    return f"{hello} {STYLE_QUESTION}"


# What Mani says when their message is its own last reply sent back, most likely copied by mistake (muhammad,
# 2026-11-04: a pasted reply was taken as an answer and the offer followed). Fixed, so it costs no model call.
COPIED_BACK = "It looks like you've sent my last message back to me. What did you want to say?"

# The client's three buttons under an offer (muhammad, 2026-10-08), always set by code. Tell me
# more is the one that asks what the questions involve.
TRY_IT_LABEL = "Try it"
TELL_ME_MORE_LABEL = "Tell me more"
KEEP_CHATTING_LABEL = "Keep chatting"
TELL_ME_ABOUT_THIS_LABEL = "Tell me about this"
EXPLAIN_LABELS = {TELL_ME_ABOUT_THIS_LABEL.lower(), TELL_ME_MORE_LABEL.lower()}
