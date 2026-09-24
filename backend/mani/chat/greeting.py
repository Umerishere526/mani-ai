# ABOUTME: Mani's fixed, client-authored lines: the greeting, the style choice, each style's
# ABOUTME: opener, and the offer explanation. Written here rather than generated, so they cost nothing.

DEFAULT_NAME = "there"

# Wording from the client spec, docs/specs/conversational-styles.md "Conversation opening":
# every conversation starts by asking how the person wants to be spoken to.
STYLE_QUESTION = "How would you like me to speak with you today?"

# The greeting's buttons. `style` is read back by the backend when one is tapped; the client
# only ever sends the label, exactly as it does for every other button.
STYLE_OPTIONS = [
    {"label": "Direct", "style": "direct"},
    {"label": "Supportive", "style": "supportive"},
    {"label": "Reflective", "style": "reflective"},
]

# What Mani says once a style is chosen - fixed wording from the same spec.
OPENERS = {
    "direct": "How can I help you today?",
    "supportive": "How can I support you today?",
    "reflective": "What's on your mind today?",
}


def greeting(nickname: str | None, returning: bool) -> str:
    name = nickname or DEFAULT_NAME
    hello = f"Hi {name}, good to see you again." if returning else f"Hi {name}. It's MANI."
    return f"{hello} {STYLE_QUESTION}"


# Buttons asking what an offer involves. An offer carries two, Try it and Keep chatting
# (muhammad, 2026-09-24), and repairs drops one of these the model still adds, since the offer's
# own words say how the questions would help.
TELL_ME_ABOUT_THIS_LABEL = "Tell me about this"
EXPLAIN_LABELS = {TELL_ME_ABOUT_THIS_LABEL.lower(), "tell me more"}

# The two choices every framework ends on - the client's cadence: "Framework completes ->
# Somatic check-in -> Chat More OR Go to Library".
CHAT_MORE_LABEL = "Chat More"
GO_TO_LIBRARY_LABEL = "Go to Library"

# Asked in this order, one per reply, once a framework has finished and the person carries on
# with the same issue - the client's "three forward-moving reflective questions".
AFTER_FRAMEWORK_QUESTIONS = (
    "What feels most important about this now?",
    "What do you think you need to do differently from here?",
    "How could you take one small step toward that?",
)
