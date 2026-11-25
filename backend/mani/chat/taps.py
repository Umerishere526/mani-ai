# ABOUTME: What a message means when it is a tap on a button Mani showed: a style, a step of an offer, or a closing
# ABOUTME: choice. A tap is a text match against the last reply's buttons, since no button id comes on the wire.

from __future__ import annotations

from dataclasses import dataclass

from mani.chat.greeting import (
    CONTINUE_CHATTING_LABEL, EXAMPLE_LABEL, GIVE_ME_A_TOOL_LABEL, NOT_SURE_LABEL, SHOW_ME_HOW_LABEL,
    TALK_MORE_FIRST_LABEL,
)
from mani.chat.techniques import FIRST_STAGE_OPENING, Registry, line_of, stages_of
from mani.llm.schema import SmartPrompt
from mani.models.rows import Framework, Message, MessageRole, SupportStyle, TechniqueState

NOT_SURE = NOT_SURE_LABEL.lower()
SHOW_ME_HOW = SHOW_ME_HOW_LABEL.lower()
GIVE_ME_A_TOOL = GIVE_ME_A_TOOL_LABEL.lower()
EXAMPLE = EXAMPLE_LABEL.lower()
TALK_MORE_FIRST = TALK_MORE_FIRST_LABEL.lower()
CONTINUE_CHATTING = CONTINUE_CHATTING_LABEL.lower()


@dataclass(frozen=True)
class TapEvent:
    """What a tap means for this turn: the fact the reply is told, and what code does because of it."""

    fact: str | None = None
    starting: Framework | None = None
    explain: Framework | None = None
    example: Framework | None = None
    demonstrate: Framework | None = None
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
            f"They tapped to start {offered.name}. Your reply opens its first stage, `{first}`, with "
            f"{FIRST_STAGE_OPENING} (its line: \"{line_of(offered, first)}\"), even if the chat already touched it."
        ))
    if offered is not None and tapped.decline:
        # A Keep chatting button stored before the client's sequence (2026-11-18) meant no for now.
        return TapEvent(set_aside=True, fact=(
            f"They chose to keep talking instead of trying {offered.name}. Carry on with them; you may offer it again "
            "later when it fits."))
    if offered is not None and label == NOT_SURE:
        return TapEvent(explain=offered)
    if offered is not None and label == SHOW_ME_HOW:
        return TapEvent(demonstrate=offered, fact=(
            f"They tapped Show me how. Show briefly how {offered.name}'s five steps would go on their own situation: "
            "one short line for each step, in order, using only what they have told you, in their words. Where they "
            "have not said what a step needs, say that step is theirs to fill in instead of filling it in; never "
            "invent a detail, a belief or a feeling. This reply does not start the set: its question invites them to "
            "try it themselves, and the app shows the button to start."))
    if offered is not None and label == GIVE_ME_A_TOOL:
        first = stages_of(offered)[0]
        return TapEvent(starting=offered, fact=(
            f"They tapped Give me a tool, so {offered.name} starts now. Your reply opens its first stage, `{first}`, "
            f"with its line (\"{line_of(offered, first)}\"). If they have already told you what that stage asks, say it "
            "back in a sentence, in their words, and ask only whether it is right or what is missing; otherwise ask "
            "that stage's question."))
    if offered is not None and label == EXAMPLE:
        return TapEvent(example=offered)
    if offered is not None and label == TALK_MORE_FIRST:
        return TapEvent(set_aside=True, fact=(
            f"They chose to talk more before trying {offered.name}. Carry on with them; you may offer it again later "
            "when it fits."))
    if label == CONTINUE_CHATTING:
        return TapEvent(fact="They chose to continue chatting.")
    return TapEvent(fact=f'They tapped the button "{tapped.label}".')
