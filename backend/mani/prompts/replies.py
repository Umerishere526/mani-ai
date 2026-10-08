# ABOUTME: The `replies` row: every line Mani sends without the model, parsed and checked.
# ABOUTME: Strict, so a bad edit is refused when it is written instead of breaking a turn.

from __future__ import annotations

from string import Formatter
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StrictStr, field_validator

from mani.models.rows import SupportStyle
from mani.prompts.yaml_row import parse_yaml_row

STYLES = [style.value for style in SupportStyle]


def _not_blank(text: str) -> str:
    if not text.strip():
        raise ValueError("must not be empty")
    return text


Text = Annotated[StrictStr, AfterValidator(_not_blank)]


def _sendable_in_one_ctx_line(text: str) -> str:
    """A line the model is shown inside one [ctx] line, joined to the others by ` | `."""
    if "\n" in text or "\r" in text or " | " in text or "[" in text or "]" in text:
        raise ValueError("must be one line with no ' | ', '[' or ']'")
    return _not_blank(text)


CtxLine = Annotated[StrictStr, AfterValidator(_sendable_in_one_ctx_line)]


def _only_the_name_field(template: str) -> str:
    try:
        parts = list(Formatter().parse(template))
    except ValueError:
        raise ValueError("braces must be balanced") from None
    for _, name, spec, conversion in parts:
        if name is not None and (name != "name" or spec or conversion):
            raise ValueError("the only field allowed is a plain {name}")
    return template


GreetingText = Annotated[Text, AfterValidator(_only_the_name_field)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Greeting(_Strict):
    new: GreetingText
    returning: GreetingText
    default_name: Text


class Replies(_Strict):
    greeting: Greeting
    style_question: Text
    # Both are keyed by SupportStyle value; the order of `style_labels` is the order of the buttons.
    style_labels: dict[str, Text]
    openers: dict[str, Text]
    clarification_lines: Annotated[list[CtxLine], Field(min_length=1)]
    after_framework_questions: Annotated[list[CtxLine], Field(min_length=1)]

    @field_validator("style_labels", "openers")
    @classmethod
    def _one_for_each_style(cls, by_style: dict[str, str]) -> dict[str, str]:
        if sorted(by_style) != sorted(STYLES):
            raise ValueError(f"keys must be exactly {', '.join(STYLES)}")
        return by_style

    @field_validator("style_labels")
    @classmethod
    def _labels_differ(cls, labels: dict[str, str]) -> dict[str, str]:
        # A tap on a style button is matched to its label ignoring case.
        if len({label.strip().lower() for label in labels.values()}) != len(labels):
            raise ValueError("two labels are the same ignoring case")
        return labels


def parse_replies(content: str) -> Replies:
    return parse_yaml_row(Replies, "replies", content)
