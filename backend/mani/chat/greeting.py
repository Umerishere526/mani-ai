# ABOUTME: Builds the conversation's opening line and its style buttons from the `replies` row,
# ABOUTME: and names the two choices a framework's ending hands over.

from mani.prompts.replies import Replies


def greeting(replies: Replies, nickname: str | None, returning: bool) -> str:
    text = replies.greeting.returning if returning else replies.greeting.new
    name = nickname or replies.greeting.default_name
    return f"{text.format(name=name)} {replies.style_question}"


def style_options(replies: Replies) -> list[dict[str, str]]:
    """The greeting's buttons, in the order `style_labels` lists them. `style` is read back by
    the backend when one is tapped; the client only ever sends the label, exactly as it does for
    every other button."""
    return [{"label": label, "style": style} for style, label in replies.style_labels.items()]


# The two choices every framework ends on - the client's cadence: "Framework completes ->
# Somatic check-in -> Chat More OR Go to Library".
CHAT_MORE_LABEL = "Chat More"
GO_TO_LIBRARY_LABEL = "Go to Library"
