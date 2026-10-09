# ABOUTME: Builds an offer of a set of questions, and the reply to Tell me more, from the `replies`
# ABOUTME: row and the offered framework's row, so every word of them is seeded content.

from mani.models.rows import Framework
from mani.prompts.replies import Replies, StyledOffer


def _filled(template: str, framework: Framework) -> str:
    return template.format(name=framework.name, description=framework.description)


def _styled(replies: Replies, framework: Framework, style: str) -> StyledOffer | None:
    """The framework's own wording in this conversation style, when the row has it."""
    return replies.offer.by_framework.get(framework.id, {}).get(style)


def offer(replies: Replies, framework: Framework, style: str) -> tuple[str, list[dict]]:
    """The offer's text and its three buttons, in order. `more` is read back by the backend when
    Tell me more is tapped; like the greeting's `style`, it is never part of the model's reply."""
    labels = replies.offer.labels
    styled = _styled(replies, framework, style)
    text = styled.text if styled else _filled(replies.offer.text, framework)
    return text, [
        {"label": labels.accept, "technique": framework.id},
        {"label": labels.more, "more": True},
        {"label": labels.decline, "decline": True},
    ]


def told_more(replies: Replies, framework: Framework, style: str) -> tuple[str, list[dict]]:
    """The reply to Tell me more and the two buttons that still answer the offer."""
    labels = replies.offer.labels
    styled = _styled(replies, framework, style)
    text = styled.more_text if styled else _filled(replies.offer.more_text, framework)
    return text, [
        {"label": labels.accept, "technique": framework.id},
        {"label": labels.decline, "decline": True},
    ]
