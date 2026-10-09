# ABOUTME: The `replies` row: every line Mani sends without the model, parsed and checked.
# ABOUTME: Strict, so a bad edit is refused when it is written instead of breaking a turn.

from __future__ import annotations

from string import Formatter
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StrictStr,
    field_validator,
    model_validator,
)

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


def _plain_fields(template: str) -> set[str]:
    """The fields a template fills, each a plain named field with no conversion or format."""
    try:
        parts = list(Formatter().parse(template))
    except ValueError:
        raise ValueError("braces must be balanced") from None
    fields: set[str] = set()
    for _, name, spec, conversion in parts:
        if name is None:
            continue
        if not name or spec or conversion:
            raise ValueError("a field must be a plain named field, such as {name}")
        fields.add(name)
    return fields


def _only_the_name_field(template: str) -> str:
    if _plain_fields(template) - {"name"}:
        raise ValueError("the only field allowed is a plain {name}")
    return template


def _the_name_and_the_description(template: str) -> str:
    if _plain_fields(template) != {"name", "description"}:
        raise ValueError("the fields must be exactly {name} and {description}")
    return template


def _differ_ignoring_case(labels: list[str]) -> None:
    # A tap on a button is matched to its label ignoring case.
    if len({label.strip().lower() for label in labels}) != len(labels):
        raise ValueError("two labels are the same ignoring case")


GreetingText = Annotated[Text, AfterValidator(_only_the_name_field)]
OfferText = Annotated[Text, AfterValidator(_the_name_and_the_description)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Greeting(_Strict):
    new: GreetingText
    returning: GreetingText
    default_name: Text


class OfferLabels(_Strict):
    accept: Text
    more: Text
    decline: Text

    @model_validator(mode="after")
    def _labels_differ(self) -> OfferLabels:
        _differ_ignoring_case([self.accept, self.more, self.decline])
        return self


class Offer(_Strict):
    """The offer the code writes when the model offers a set, and the reply to Tell me more."""

    text: OfferText
    more_text: OfferText
    labels: OfferLabels


class Replies(_Strict):
    greeting: Greeting
    style_question: Text
    # Both are keyed by SupportStyle value; the order of `style_labels` is the order of the buttons.
    style_labels: dict[str, Text]
    openers: dict[str, Text]
    after_framework_questions: Annotated[list[CtxLine], Field(min_length=1)]
    offer: Offer

    @field_validator("style_labels", "openers")
    @classmethod
    def _one_for_each_style(cls, by_style: dict[str, str]) -> dict[str, str]:
        if sorted(by_style) != sorted(STYLES):
            raise ValueError(f"keys must be exactly {', '.join(STYLES)}")
        return by_style

    @field_validator("style_labels")
    @classmethod
    def _labels_differ(cls, labels: dict[str, str]) -> dict[str, str]:
        _differ_ignoring_case(list(labels.values()))
        return labels


def parse_replies(content: str) -> Replies:
    return parse_yaml_row(Replies, "replies", content)
