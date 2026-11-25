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


def greeting(nickname: str | None, returning: bool) -> str:
    name = nickname or DEFAULT_NAME
    hello = f"Hi {name}, good to see you again." if returning else f"Hi {name}. It's MANI."
    return f"{hello} {STYLE_QUESTION}"


# What Mani says when their message is its own last reply sent back, most likely copied by mistake (muhammad,
# 2026-11-04: a pasted reply was taken as an answer and the offer followed). Fixed, so it costs no model call.
COPIED_BACK = "It looks like you've sent my last message back to me. What did you want to say?"

# The client's buttons at each step of an offer (her sequence document, 2026-11-18), always set by code. The lead-in's
# three are three different experiences (Lolly, 2026-11-20): Not sure explains the five steps, Show me how walks them
# on the person's own situation, Give me a tool starts the first stage. Talk more first sets the offer aside for now.
NOT_SURE_LABEL = "Not sure"
SHOW_ME_HOW_LABEL = "Show me how"
GIVE_ME_A_TOOL_LABEL = "Give me a tool"
LEAD_IN_LABELS = (NOT_SURE_LABEL, SHOW_ME_HOW_LABEL, GIVE_ME_A_TOOL_LABEL)
TALK_MORE_FIRST_LABEL = "Talk more first"
# How they feel after a framework's last stage, asked before the close (the client's sequence document, 2026-11-18).
# muhammad's wording (2026-11-25), as on main; it overrules Lolly's 2026-11-23 ask that one option say it did not
# help (see docs/client/requirements.md, Conflicts): "I'm not sure yet" is the one that does not presume it helped.
FEELINGS_LABELS = ("Feel stronger", "Feel more focused", "I'm not sure yet")
# The close, in the client's words (Lolly, 2026-11-20: "CONTINUE CHATTING OR VISIT LIBRARY").
CONTINUE_CHATTING_LABEL = "Continue chatting"
VISIT_LIBRARY_LABEL = "Visit library"


def start_label(framework_name: str) -> str:
    """The button that starts a set after its five steps, such as "Start ABCDE"."""
    return f"Start {framework_name}"


def style_label(style: str) -> str:
    """The style's button label, which is also how Mani's facts name it."""
    return next((option["label"] for option in STYLE_OPTIONS if option["style"] == style), style)


def resolve_style(conversation_style: str | None, profile_style: str | None) -> str:
    """The style in force: the conversation's own choice, else the profile's onboarding answer, else the default."""
    return conversation_style or profile_style or DEFAULT_STYLE
