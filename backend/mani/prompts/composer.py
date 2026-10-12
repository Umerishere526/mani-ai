# ABOUTME: Assembles the system prompt from its layers, in a fixed order.
# ABOUTME: The summary is a layer here rather than a string appended by the caller.

from __future__ import annotations

from dataclasses import dataclass, field

from mani.chat.techniques import Registry
from mani.config import get_settings
from mani.llm.schema import Memory
from mani.models.rows import Profile, ThreadSummary
from mani.prompts.cache import Config, style_prompt

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


def framework_index(registry: Registry, style: str) -> str | None:
    """The catalogue of frameworks, built from the registry rather than written by hand.

    Every line here already exists as data on `admin.frameworks`, seeded from the framework
    files - a prose copy beside it is a second source of truth that drifts silently the
    first time somebody edits one and not the other. Generating it means adding a framework
    is a content change with no prompt edit, which is what the registry already claims.

    Static across users and turns in one style, so it sits in the cached prefix after that
    style's layer. Only that style's offer and Keep chatting wording is listed.
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

    # The client's description of each is added by the backend when they ask to hear more, so
    # it is not listed here: a model given the text copied it, and offers showed it twice.
    lines += [
        "", "When you offer one, say its name, as written above. Its description is added for "
        "you if they ask to hear more. Never its id.",
    ]

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

    # What each one needs to know before it is the right offer, listened for rather than asked:
    # static, so it sits in the cached prefix with the rest of the index.
    to_find_out = [
        f"- **{framework.name}**: {'; '.join(items)}"
        for framework in present
        for items in [(framework.activation or {}).get("to_find_out") or []]
        if items
    ]
    if to_find_out:
        lines += [
            "", "## Finding the fit", "",
            "What each one needs before it is the right offer. Listen for these in what they tell "
            "you; your questions follow their feeling, never this list:", "",
        ] + to_find_out

    # The client's own offer wording in this style. Mani writes its part of an offer in that
    # pattern and changes only what is in angle brackets, so it reads as a whole sentence.
    patterns = _offering_lines(present, "offer", style)
    keep_chatting = _offering_lines(present, "keep_chatting", style)
    if patterns:
        lines += [
            "", "## How to word an offer", "",
            "Write your part of an offer in this pattern. Keep every word as written, the whole "
            "pattern and never shortened. Change only what is in angle brackets, to fit what they told "
            "you, so the whole sentence reads naturally. The permission question is added after "
            "your part.", "",
        ] + patterns
    if keep_chatting:
        lines += [
            "", "## When they choose Keep chatting", "",
            "Carry on the conversation with this question, keeping its words and changing only what "
            "is in angle brackets to fit what they said. Offer nothing in that reply.", "",
        ] + keep_chatting

    return "\n".join(lines)


def _offering_lines(frameworks: list, key: str, style: str) -> list[str]:
    """Each framework's offering wording under `key`, in one style, headed by its name."""
    return [
        f"**{framework.name}**\n{' '.join(str(text).split())}"
        for framework in frameworks
        for text in [(((framework.stages or {}).get("offering") or {}).get(key) or {}).get(style)]
        if text
    ]


def user_context(profile: Profile | None) -> str | None:
    """What Mani knows about the person, from onboarding.

    The previous version read only the nickname out of auth user_metadata and ignored the
    topics it had collected, so onboarding shaped nothing.

    The support style is deliberately absent. It is resolved per turn from the conversation
    first and the profile second, and composed as its own layer. A second copy here would be
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
        "These have already been offered in this conversation:\n"
        f"{listed}\n\n"
        "One they said no to may be offered again once `offer_window` is open, if it still "
        "fits best - or a different one, if what they have said since has changed what fits. "
        "One they have just finished may not be offered again."
    )


def summary_layer(summary: ThreadSummary | None) -> str | None:
    """Earlier conversation, compressed. Absent until a thread is long enough to have one."""
    if summary is None:
        return None

    lines = []
    if summary.current_issue:
        lines.append(f"**Current issue:** {summary.current_issue}")
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
    style: str,
    should_generate_title: bool = False,
    offered: list[str] | None = None,
    summary: ThreadSummary | None = None,
    memory: Memory | None = None,
) -> SystemPrompt:
    """Build the system prompt for one turn.

    Order is fixed and identical every turn, which is what lets the provider cache the
    static prefix: one shared by every style, then one per style. `style` is the conversation
    style resolved for this turn; only its own layer is sent.
    """
    settings = get_settings()

    candidates: list[tuple[str, str | None]] = [
        # Who Mani is and how a conversation runs, then what a reply must satisfy: identical
        # for every user and style. Then the chosen style and the catalogue in its wording,
        # identical for every conversation in that style.
        ("mani_base", config.require("mani_base").content),
        ("response_format", config.require("response_format").content),
        ("style", config.require(style_prompt(style)).content),
        ("framework_index", framework_index(config.registry, style)),
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
