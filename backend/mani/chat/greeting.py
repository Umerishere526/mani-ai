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


# The three buttons under an offer, and the two it comes back with after "Tell me about this"
# (muhammad, 2026-09-24). Mani never calls what it offers a framework: it is a sequence of
# questions.
TRY_IT_LABEL = "Try it"
KEEP_CHATTING_LABEL = "Keep chatting"
TELL_ME_ABOUT_THIS_LABEL = "Tell me about this"
# The older label, still recognised as the same tap if a reply ever carries it.
EXPLAIN_LABELS = {TELL_ME_ABOUT_THIS_LABEL.lower(), "tell me more"}

# What Mani says on "Tell me about this" for an offer whose framework has no description of its
# own - the client's per-style explanations. The description is what is normally shown.
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
