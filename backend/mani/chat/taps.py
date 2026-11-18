# ABOUTME: What a message means when it is a tap on a button Mani showed: a style, a step of an offer, or a closing
# ABOUTME: choice. A tap is a text match against the last reply's buttons, since no button id comes on the wire.

from __future__ import annotations

from dataclasses import dataclass

from mani.chat.greeting import (
    CLOSING_KEEP_CHATTING_LABEL, EXAMPLE_LABEL, FINISH_LABEL, LEAD_IN_LABELS, TALK_MORE_FIRST_LABEL,
)
from mani.chat.techniques import Registry, line_of, stages_of
from mani.llm.schema import SmartPrompt
from mani.models.rows import Framework, Message, MessageRole, SupportStyle, TechniqueState

LEAD_IN = {label.lower() for label in LEAD_IN_LABELS}
EXAMPLE = EXAMPLE_LABEL.lower()
TALK_MORE_FIRST = TALK_MORE_FIRST_LABEL.lower()
FINISH = FINISH_LABEL.lower()
KEEP_CHATTING = CLOSING_KEEP_CHATTING_LABEL.lower()


@dataclass(frozen=True)
class TapEvent:
    """What a tap means for this turn: the fact the reply is told, and what code does because of it."""

    fact: str | None = None
    starting: Framework | None = None
    explain: Framework | None = None
    example: Framework | None = None
    set_aside: bool = False


def find_tapped_prompt(history: list[Message], content: str) -> SmartPrompt | None:
    """The button this message taps, matched against the buttons under Mani's most recent message that carried any."""
    typed = content.strip().lower()
    if not typed:
        return None
    for option in _last_offered(history):
        label = str(option.get("label", "")).strip().lower()
        if label and label == typed:
            return SmartPrompt.model_validate(option)
    return None


def chosen_style(history: list[Message], content: str) -> SupportStyle | None:
    """The style this message picks, when it taps one of the greeting's style buttons. Read from the stored
    options, since `style` is a greeting-only key the model is never asked for."""
    typed = content.strip().lower()
    for option in _last_offered(history):
        if option.get("style") and str(option.get("label", "")).strip().lower() == typed:
            return SupportStyle(option["style"])
    return None


def _last_offered(history: list[Message]) -> list[dict]:
    """The buttons under Mani's most recent message, which may be none."""
    for message in reversed(history):
        if message.role is MessageRole.MANI:
            return message.prompt_options or []
    return []


def tap_event(tapped: SmartPrompt | None, registry: Registry, open_offer: TechniqueState | None) -> TapEvent:
    """What the tap means. Start starts only the framework whose offer is still open, so a tap on an old button
    from a lapsed offer starts nothing."""
    if tapped is None:
        return TapEvent()
    label = tapped.label.strip().lower()
    offered = registry.get(open_offer.framework_id) if open_offer is not None else None
    if tapped.technique:
        if offered is None or offered.id != tapped.technique:
            return TapEvent()
        first = stages_of(offered)[0]
        return TapEvent(starting=offered, fact=(
            f"They tapped to start {offered.name}. Your reply opens its first stage, `{first}`, with its line "
            f"\"{line_of(offered, first)}\" and that stage's question, even if the chat already touched it."
        ))
    if offered is not None and label in LEAD_IN:
        return TapEvent(explain=offered)
    if offered is not None and label == EXAMPLE:
        return TapEvent(example=offered)
    if offered is not None and label == TALK_MORE_FIRST:
        return TapEvent(set_aside=True, fact=(
            f"They chose to talk more before trying {offered.name}. Carry on with them; you may offer it again later "
            "when it fits."))
    if label == FINISH:
        return TapEvent(fact="They tapped Finish for Now. Say goodbye warmly in a sentence or two, and ask nothing.")
    if label == KEEP_CHATTING:
        return TapEvent(fact="They chose to keep chatting after the set of questions.")
    return TapEvent(fact=f'They tapped the button "{tapped.label}".')
