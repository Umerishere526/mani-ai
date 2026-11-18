# ABOUTME: What a turn's system prompt says about the person (onboarding, the summary), and which model, effort
# ABOUTME: and hosts a prompt row names. The prompt itself is facts.system_prompt.

from __future__ import annotations

from mani.config import get_settings
from mani.models.rows import Profile, ThreadSummary
from mani.prompts.cache import Config


def user_context(profile: Profile | None) -> str | None:
    """What Mani knows about the person, from onboarding: the name they prefer and the topics they came for.

    The support style is deliberately absent. It is resolved per turn from the conversation
    first and the profile second, and named in the turn's facts. A second copy here would be
    the profile's answer contradicting a conversation that had chosen differently.
    """
    if profile is None:
        return None

    lines = []
    if profile.nickname:
        lines.append(f'The user prefers to be called "{profile.nickname}".')
    if profile.topics:
        lines.append(f"Topics they came here for: {', '.join(profile.topics)}.")

    return "## User Context\n" + "\n".join(lines) if lines else None


def summary_layer(summary: ThreadSummary | None) -> str | None:
    """Earlier conversation, compressed. Absent until a thread is long enough to have one."""
    if summary is None:
        return None

    lines = []
    if summary.summary:
        lines.append(summary.summary)
    if summary.techniques_tried:
        tried = ", ".join(
            f"{t.name} ({'helpful' if t.helpful else 'not helpful'})"
            for t in summary.techniques_tried
        )
        lines.append(f"\n**Techniques discussed**: {tried}")

    return "## Conversation Context\n" + "\n".join(lines) if lines else None


def model_settings(config: Config, name: str) -> tuple[str, dict, dict]:
    """The model id, parameters and routing a prompt row names, so the model is configuration while the key it
    authenticates with stays in the environment."""
    prompt = config.require(name)
    return prompt.model_id or get_settings().default_chat_model, prompt.model_parameters, prompt.routing
