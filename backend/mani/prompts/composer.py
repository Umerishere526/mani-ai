# ABOUTME: Assembles the system prompt from its layers, in a fixed order.
# ABOUTME: The summary is a layer here rather than a string appended by the caller.

from __future__ import annotations

from dataclasses import dataclass, field

from mani.chat.techniques import Registry
from mani.config import get_settings
from mani.llm.schema import Memory
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


def framework_index(registry: Registry) -> str | None:
    """The catalogue of frameworks, built from the registry rather than written by hand.

    Every line here already exists as data on `admin.frameworks`, seeded from the framework
    files - a prose copy beside it is a second source of truth that drifts silently the
    first time somebody edits one and not the other. Generating it means adding a framework
    is a content change with no prompt edit, which is what the registry already claims.

    Static across users and turns, so it sits in the cached prefix with the other layers.
    """
    frameworks = [registry.get(fid) for fid in registry.ids]
    present = [f for f in frameworks if f is not None]
    if not present:
        return None

    lines = [
        "# Framework Index",
        "",
        "The frameworks available to offer, and what each one is for. The `[ctx]` block "
        "carries the stage guidance for whichever is running.",
        "",
        "| Framework | Id | Use it when |",
        "|---|---|---|",
    ]
    for framework in present:
        indication = (framework.activation or {}).get("central_indication", "")
        lines.append(
            f"| {framework.name} | `{framework.id}` | {' '.join(indication.split())} |"
        )

    known = set(registry.ids)
    # Each distinction is written from both sides in the framework files - ABCDE explains
    # itself against Thought Reframe and Thought Reframe explains itself against ABCDE - and
    # the ones about not using a framework at all are written five times over. Both are
    # right in a file a clinician reads and pure waste in a prompt paid for every turn, so
    # a pair is emitted once and a non-framework comparison only the first time.
    seen: set[frozenset[str] | str] = set()
    rendered: list[str] = []
    for framework in present:
        for other, text in ((framework.activation or {}).get("distinctions") or {}).items():
            key = frozenset({framework.id, other}) if other in known else other
            if key in seen:
                continue
            seen.add(key)
            label = registry.get(other).name if other in known else other.replace("_", " ")
            rendered.append(f"- **{framework.name} or {label}** — {' '.join(text.split())}")

    if rendered:
        lines += ["", "## Telling them apart", ""] + rendered

    # Only the contraindications, not every not_when line: most of those name a different
    # framework to use instead, which "Telling them apart" already says. These name a
    # situation where offering any of it would harm the person.
    never = [
        f"- **{framework.name}**: {' '.join(text.split())}"
        for framework in present
        for text in (framework.activation or {}).get("contraindications") or []
    ]
    if never:
        lines += ["", "## Never offer one when", ""] + never

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
        lines.append(f'The user prefers to be called "{profile.nickname}".')
    if profile.topics:
        lines.append(f"Topics they came here for: {', '.join(profile.topics)}.")

    return "## User Context\n" + "\n".join(lines) if lines else None


# Headings for each part of the memory, in the order a reply would use them.
_MEMORY_HEADINGS = (
    ("themes", "Keeps coming back to"),
    ("low_times", "Feels low when"),
    ("better_times", "Feels better when"),
    ("what_helps", "What has helped"),
    ("what_doesnt", "What has not helped"),
    ("how_they_talk", "How they like the conversation to go"),
)


def user_memory(memory: Memory | None) -> str | None:
    """What this person has said about themselves across earlier chats, as patterns.

    Never the earlier conversations themselves: a new chat starts with none of their
    messages. This is what lets Mani choose how to respond without making them repeat it.
    """
    if memory is None:
        return None
    parts = [
        f"- **{heading}:** " + "; ".join(getattr(memory, field))
        for field, heading in _MEMORY_HEADINGS
        if getattr(memory, field)
    ]
    if not parts:
        return None
    return (
        "## What you know about them from earlier conversations\n"
        "Patterns they have described, in their words. Use them to choose how you respond: "
        "what to ask about, what to offer, what to avoid. Never quote them, never say you "
        "remember, and never mention an earlier conversation. If they bring something up, "
        "respond to what they say now.\n\n" + "\n".join(parts)
    )


def techniques_used(offered: list[str]) -> str | None:
    """Frequency limiting: what has already been offered in this conversation."""
    if not offered:
        return None
    listed = "\n".join(f"- {name}" for name in offered)
    return (
        "## Techniques Already Offered\n"
        "These have already been offered in this conversation, whether or not the user "
        "took them up. Do NOT offer them again:\n"
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
    memory: Memory | None = None,
) -> SystemPrompt:
    """Build the system prompt for one turn.

    Order is fixed and identical every turn, which is what lets the provider cache the
    static prefix - identity and the technique library are by far the largest layers and
    never vary.
    """
    settings = get_settings()

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
