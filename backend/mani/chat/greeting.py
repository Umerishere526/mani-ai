# ABOUTME: Mani's fixed, client-authored lines: the greeting, the style choice, each style's
# ABOUTME: opener, and the offer explanation. Written here rather than generated, so they cost nothing.

DEFAULT_NAME = "there"
# The greeting, the style they tapped, and that style's opener: a conversation's first three messages.
OPENING_MESSAGES = 3
# The style when neither the conversation nor the profile has chosen one. A thread's own choice wins over the profile's
# onboarding answer.
DEFAULT_STYLE = "supportive"

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

# What Mani opens a new conversation with, in place of the style's opener, while a pause that has run out still owes
# the question how things are (muhammad, 2026-11-16). Fixed, so the opening costs no model call; the wording is ours
# until the client supplies hers.
RETURN_OPENER = (
    "Before we start, I want to check in with you. I paused our chat earlier because I was worried about what you "
    "were facing. How are things with that right now?"
)


def openers(return_check_owed: bool) -> dict[str, str]:
    """Each style's opener, or the question about the pause for every style while one is owed."""
    return dict.fromkeys(OPENERS, RETURN_OPENER) if return_check_owed else OPENERS


def greeting(nickname: str | None, returning: bool) -> str:
    name = nickname or DEFAULT_NAME
    hello = f"Hi {name}, good to see you again." if returning else f"Hi {name}. It's MANI."
    return f"{hello} {STYLE_QUESTION}"


# What Mani says when their message is its own last reply sent back, most likely copied by mistake (muhammad,
# 2026-11-04: a pasted reply was taken as an answer and the offer followed). Fixed, so it costs no model call.
COPIED_BACK = "It looks like you've sent my last message back to me. What did you want to say?"

# The client's buttons at each step of an offer (her sequence document, 2026-11-18), always set by code. Any of the
# lead-in's three shows the five steps; Talk more first sets the offer aside for now.
LEAD_IN_LABELS = ("Not sure", "Show me how", "Give me a tool")
EXAMPLE_LABEL = "I need an example"
TALK_MORE_FIRST_LABEL = "Talk more first"
# How they feel after a framework's last stage, asked before the close (the client's sequence document, 2026-11-18).
FEELINGS_LABELS = ("Stronger", "More focused", "Still a bit tired")
# The three choices after a framework's last stage, in the client's words.
CLOSING_KEEP_CHATTING_LABEL = "Keep Chatting"
GO_TO_LIBRARY_LABEL = "Go to Library"
FINISH_LABEL = "Finish for Now"


def start_label(framework_name: str) -> str:
    """The button that starts a set after its five steps, such as "Start ABCDE"."""
    return f"Start {framework_name}"


def style_label(style: str) -> str:
    """The style's button label, which is also how Mani's facts name it."""
    return next((option["label"] for option in STYLE_OPTIONS if option["style"] == style), style)


def resolve_style(conversation_style: str | None, profile_style: str | None) -> str:
    """The style in force: the conversation's own choice, else the profile's onboarding answer, else the default."""
    return conversation_style or profile_style or DEFAULT_STYLE
