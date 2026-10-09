# ABOUTME: The `tuning` row: the numbers that shape a conversation, parsed and range checked.
# ABOUTME: Strict, so `true` or "2" is refused and a typo cannot reopen a cap or summarise every message.

from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StrictInt, StrictStr

from mani.models.rows import SupportStyle
from mani.prompts.yaml_row import parse_yaml_row


def _count(low: int, high: int):
    return Annotated[StrictInt, Field(ge=low, le=high)]


def _a_style(name: str) -> str:
    if name not in {style.value for style in SupportStyle}:
        raise ValueError("must be one of " + ", ".join(style.value for style in SupportStyle))
    return name


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class OfferTuning(_Strict):
    clear_offer_after: _count(1, 20)
    clear_cooldown_after_decline: _count(0, 200)
    cooldown_after_complete: _count(0, 200)
    default_style: Annotated[StrictStr, AfterValidator(_a_style)]


class WindowTuning(_Strict):
    context_window: _count(4, 100)
    style_window: _count(1, 50)
    recent_openers_words: _count(1, 10)
    recent_openers_window: _count(1, 10)
    title_after_messages: _count(1, 21)
    ending_turn_cap: _count(2, 50)
    stage_turn_cap: _count(2, 20)


class MemoryTuning(_Strict):
    max_entries: _count(1, 20)
    max_entry_chars: _count(1, 500)
    idle_after_hours: _count(1, 720)


class Tuning(_Strict):
    offers: OfferTuning
    windows: WindowTuning
    memory: MemoryTuning


def parse_tuning(content: str) -> Tuning:
    return parse_yaml_row(Tuning, "tuning", content)
