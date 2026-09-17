# ABOUTME: Assembles the system prompt from its layers, in a fixed order.
# ABOUTME: The summary is a layer here rather than a string appended by the caller.

from __future__ import annotations

from dataclasses import dataclass, field

from mani.config import get_settings
from mani.models.rows import Profile, ThreadSummary
from mani.prompts.cache import Config

DEBUG_LAYER = (
    "# Debug\n"
    "For every response also fill the reasoning field with why you responded that way "
    "and which part of the prompt influenced it."
)


@dataclass(frozen=True)
class SystemPrompt:
    text: str
    # Which layers were included and how long each was, for the prompt-size question that
    # otherwise only shows up on the bill.
    layers: list[tuple[str, int]] = field(default_factory=list)

    @property
    def length(self) -> int:
        return len(self.text)


def user_context(profile: Profile | None) -> str | None:
    """What Mani knows about the person, from onboarding.

    The previous version read only the nickname out of auth user_metadata and ignored the
    topics and support style it had collected, so onboarding shaped nothing.
    """
    if profile is None:
        return None

    lines = []
    if profile.nickname:
        lines.append(f'The user prefers to be called "{profile.nickname}".')
    if profile.topics:
        lines.append(f"Topics they came here for: {', '.join(profile.topics)}.")
    if profile.support_style:
        lines.append(f"They asked for a {profile.support_style} style of support.")

    return "## User Context\n" + "\n".join(lines) if lines else None


def techniques_used(offered: list[str]) -> str | None:
    """Frequency limiting: what has already been offered in this conversation."""
    if not offered:
        return None
    listed = "\n".join(f"- {name}" for name in offered)
    return (
        "## Techniques Already Used\n"
        "The user has already tried these techniques in this conversation. Do NOT offer "
        "them again unless the user explicitly asks to revisit one:\n"
        f"{listed}\n\n"
        "Instead, try different approaches or go deeper on what has already been discussed."
    )


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


def compose(
    config: Config,
    profile: Profile | None,
    *,
    should_generate_title: bool = False,
    offered: list[str] | None = None,
    summary: ThreadSummary | None = None,
) -> SystemPrompt:
    """Build the system prompt for one turn.

    Order is fixed and identical every turn, which is what lets the provider cache the
    static prefix - identity and the technique library are by far the largest layers and
    never vary.
    """
    settings = get_settings()

    candidates: list[tuple[str, str | None]] = [
        ("mani_base", config.require("mani_base").content),
        ("framework_index", config.require("framework_index").content),
        ("post_framework", config.require("post_framework").content),
        ("user_context", user_context(profile)),
    ]

    if should_generate_title:
        title = config.prompt("title_generation")
        candidates.append(("title_generation", title.content if title else None))

    candidates += [
        ("techniques_used", techniques_used(offered or [])),
        ("response_format", config.require("response_format").content),
        ("debug", DEBUG_LAYER if settings.ai_debug_mode else None),
        ("summary", summary_layer(summary)),
    ]

    present = [(name, body) for name, body in candidates if body]
    return SystemPrompt(
        text="\n\n".join(body for _, body in present),
        layers=[(name, len(body)) for name, body in present],
    )


def model_settings(config: Config) -> tuple[str, dict, dict]:
    """The model id, parameters and routing for a chat turn.

    Taken from the mani_base prompt row, so the model is editable as configuration while
    the key it authenticates with stays in the environment.
    """
    prompt = config.require("mani_base")
    settings = get_settings()
    return (
        prompt.model_id or settings.default_chat_model,
        prompt.model_parameters,
        prompt.routing,
    )
