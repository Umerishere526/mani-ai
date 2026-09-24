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


# What Mani says when the person taps "Tell me more" on an offer, word for word from the same
# spec ("Tell me more" explanations, by style). It is followed by the offer again, with two
# buttons: try it, or keep talking.
TELL_ME_MORE = {
    "direct": (
        "It gives us a clear way to work through what is happening one step at a time. I'll ask "
        "you focused questions, help you look at what is driving the reaction, and guide you "
        "through the process without rushing you. You stay in control of what you want to share."
    ),
    "supportive": (
        "Of course. It gives us a way to slow things down and work through what is happening one "
        "step at a time. I'll ask you some questions, we'll look at what is coming up for you, and "
        "we'll work through it together. You can share as much or as little as feels comfortable."
    ),
    "reflective": (
        "Of course. We'll slow things down and look at what is happening one part at a time. I'll "
        "reflect back what I'm understanding, ask questions to help you look more closely at what "
        "is coming up, and check with you along the way to make sure I'm understanding you "
        "correctly. You can always correct me or tell me when something does not fit."
    ),
}
TELL_ME_MORE_LABEL = "Tell me more"

# The two choices every framework ends on - the client's cadence: "Framework completes ->
# Somatic check-in -> Chat More OR Go to Library".
CHAT_MORE_LABEL = "Chat More"
GO_TO_LIBRARY_LABEL = "Go to Library"
