# ABOUTME: Ties the keys and headings the code sends to the prompt sections that explain them.
# ABOUTME: Reads the authored prompt files directly, so no model call or database is needed.

from __future__ import annotations

import re

import pytest
import yaml
from langchain_core.utils.function_calling import convert_to_openai_function
from pydantic import BaseModel

from mani.chat.context import CTX_KEYS
from mani.llm import schema, tools
from mani.prompts.composer import LAYER_HEADINGS
from scripts.seed import PROMPTS_DIR, parse_prompt

# Entries of the `ctx` section that explain the block as a whole rather than one key.
CTX_NOT_KEYS = {"about", "facts", "stage_lines"}


def _section(name: str) -> dict:
    body = parse_prompt(PROMPTS_DIR / "response_format.md")["content"]
    return yaml.safe_load(body)[name]


def _named(word: str, text: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(word)}(?!\w)", text) is not None


def test_every_ctx_key_the_code_sends_is_explained_in_the_prompt():
    """A key the prompt never mentions reaches the model with no meaning attached."""
    explained = yaml.safe_dump(_section("ctx"), width=10_000)
    assert sorted(k for k in CTX_KEYS if not _named(k, explained)) == []


def test_every_key_the_prompt_explains_is_one_the_code_can_send():
    """A key explained but never sent tells the model to read something that is not there."""
    assert sorted(set(_section("ctx")) - CTX_NOT_KEYS - CTX_KEYS) == []


def test_every_layer_heading_the_code_writes_is_explained_in_the_prompt_and_no_other():
    """The `layers` section is keyed by each heading's title, and only the code writes them."""
    written = {heading.lstrip("# ") for heading in LAYER_HEADINGS.values()}
    assert set(_section("layers")) == written


def _descriptions(node: object) -> list[str]:
    if isinstance(node, dict):
        found = [node["description"]] if isinstance(node.get("description"), str) else []
        return found + [d for value in node.values() for d in _descriptions(value)]
    if isinstance(node, list):
        return [d for value in node for d in _descriptions(value)]
    return []


@pytest.mark.parametrize(
    "model", [schema.Reply, schema.Extraction, schema.Memory, tools.StartExercise],
    ids=lambda m: m.__name__,
)
def test_the_schemas_sent_to_the_model_carry_no_description(model: type[BaseModel]):
    """A field's meaning lives once, in its call's prompt. LangChain always writes a top level
    `description` key on the function, empty when the class has no docstring, so an empty one
    is the only kind allowed."""
    assert _descriptions(model.model_json_schema()) == []
    assert [d for d in _descriptions(convert_to_openai_function(model)) if d] == []


def test_every_reply_field_and_library_section_is_explained_in_the_prompt():
    fields = _section("fields")
    assert set(schema.Reply.model_fields) <= set(fields)
    nested = {
        "prompts": schema.SmartPrompt, "state": schema.TechniqueState,
        "crisis": schema.Crisis, "style": schema.Style,
    }
    unnamed = [
        f"{parent}.{name}"
        for parent, model in nested.items()
        for name in model.model_fields
        if not _named(name, fields[parent])
    ]
    assert unnamed == []
    assert [s.value for s in schema.LibrarySection if not _named(s.value, fields["prompts"])] == []
