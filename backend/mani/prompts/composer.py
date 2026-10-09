# ABOUTME: Assembles the system prompt from its layers, in a fixed order.
# ABOUTME: The summary is a layer here rather than a string appended by the caller.

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from mani.chat.techniques import Registry
from mani.config import get_settings
from mani.llm.schema import Memory
from mani.models.rows import Profile, TechniqueTried, ThreadSummary
from mani.prompts.cache import Config

logger = logging.getLogger(__name__)

# The heading of every layer the code writes. What each holds is said once, in
# response_format.md's `layers` section, and a test ties the two together in both directions,
# so the code sends headings and data and never a sentence of instruction.
LAYER_HEADINGS = {
    "framework_index": "# Framework Index",
    "user_context": "## User Context",
    "user_memory": "## Memory",
    "techniques_used": "## Techniques Already Offered",
    "summary": "## Conversation Context",
}


@dataclass(frozen=True)
class SystemPrompt:
    text: str
    # Which layers were included and how long each was, for the prompt-size question that
    # otherwise only shows up on the bill.
    layers: list[tuple[str, int]] = field(default_factory=list)


def framework_index(registry: Registry) -> str | None:
    """The catalogue of frameworks, built from the registry rather than written by hand.

    Each framework's body is its seven model facing lines, seeded from the framework file and
    checked there, so they are rendered as they are. A prose copy beside them would be a second
    source of truth that drifts silently the first time somebody edits one and not the other,
    and adding a framework stays a content change with no prompt edit. The client's description
    of what the questions help with stands above the seven lines, read from the summary column.

    Static across users and turns, so it sits in the cached prefix with the other layers.
    """
    frameworks = [registry.get(fid) for fid in registry.ids]
    present = [f for f in frameworks if f is not None]
    if not present:
        return None

    lines = [LAYER_HEADINGS["framework_index"]]
    for framework in present:
        lines += ["", f"## {framework.name} (`{framework.id}`)"]
        if framework.description:
            lines.append(f"Description: {framework.description}")
        lines.append(framework.body)
    return "\n".join(lines)


def user_context(profile: Profile | None) -> str | None:
    """What Mani knows about the person, from onboarding.

    The previous version read only the nickname out of auth user_metadata and ignored the
    topics it had collected, so onboarding shaped nothing.

    The support style is deliberately absent. It is resolved per turn from the conversation
    first and the profile second, and named in the [ctx] block, which is where mani_base.md
    tells the model to read it. A second copy here would be the profile's answer contradicting
    a conversation that had chosen differently.
    """
    if profile is None:
        return None

    lines = []
    if profile.nickname:
        lines.append(f"nickname: {profile.nickname}")
    if profile.topics:
        lines.append(f"topics: {', '.join(profile.topics)}")

    return LAYER_HEADINGS["user_context"] + "\n" + "\n".join(lines) if lines else None


def user_memory(memory: Memory | None) -> str | None:
    """What this person has said about themselves across earlier chats, as patterns.

    Never the earlier conversations themselves: a new chat starts with none of their
    messages. This is what lets Mani choose how to respond without making them repeat it.
    """
    if memory is None:
        return None
    # Keyed by the Memory field names, in the order a reply would use them.
    parts = [
        f"{field}: " + "; ".join(entries)
        for field in Memory.model_fields
        if (entries := getattr(memory, field))
    ]
    if not parts:
        return None
    return LAYER_HEADINGS["user_memory"] + "\n" + "\n".join(parts)


def techniques_used(offered: list[str]) -> str | None:
    """Frequency limiting: the ids of what has already been offered in this conversation."""
    if not offered:
        return None
    return LAYER_HEADINGS["techniques_used"] + "\n" + "\n".join(f"- {fid}" for fid in offered)


def tried_line(techniques: list[TechniqueTried]) -> str:
    """What was tried and whether it helped, the one way every prompt is shown it."""
    return ", ".join(
        f"{t.name} ({'helpful' if t.helpful else 'not_helpful'})" for t in techniques
    )


def summary_layer(summary: ThreadSummary | None) -> str | None:
    """Earlier conversation, compressed. Absent until a thread is long enough to have one."""
    if summary is None:
        return None

    lines = []
    if summary.current_issue:
        lines.append(f"current_issue: {summary.current_issue}")
    if summary.summary:
        lines.append(f"summary: {summary.summary}")
    if summary.techniques_tried:
        lines.append(f"techniques_tried: {tried_line(summary.techniques_tried)}")

    return LAYER_HEADINGS["summary"] + "\n" + "\n".join(lines) if lines else None


def debug_layer(config: Config) -> str | None:
    """The debug instruction, from its own row, only when debug mode is on."""
    if not get_settings().ai_debug_mode:
        return None
    row = config.prompt("debug")
    if row is None:
        logger.warning("AI_DEBUG_MODE is on but the debug prompt is missing or inactive")
        return None
    return row.content


def compose(
    config: Config,
    profile: Profile | None,
    *,
    should_generate_title: bool = False,
    offered: list[str] | None = None,
    summary: ThreadSummary | None = None,
    memory: Memory | None = None,
) -> SystemPrompt:
    """Build the system prompt for one turn.

    Order is fixed and identical every turn, which is what lets the provider cache the
    static prefix - identity and the technique library are by far the largest layers and
    never vary.
    """
    candidates: list[tuple[str, str | None]] = [
        # Two authored layers with the generated catalogue between them: who Mani is and
        # how a conversation runs, then what may be offered, then what a reply must
        # satisfy. All three are identical for every user and every turn, which is what
        # lets the provider cache the prefix.
        ("mani_base", config.require("mani_base").content),
        ("framework_index", framework_index(config.registry)),
        ("response_format", config.require("response_format").content),
        ("user_context", user_context(profile)),
        ("user_memory", user_memory(memory)),
    ]

    if should_generate_title:
        title = config.prompt("title_generation")
        candidates.append(("title_generation", title.content if title else None))

    candidates += [
        ("techniques_used", techniques_used(offered or [])),
        ("debug", debug_layer(config)),
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
