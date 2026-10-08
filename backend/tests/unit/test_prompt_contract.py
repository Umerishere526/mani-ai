# ABOUTME: Ties the keys and headings the code sends to the prompt sections that explain them.
# ABOUTME: Reads the authored prompt files directly, so no model call or database is needed.

from __future__ import annotations

import re

import yaml

from mani.chat.context import CTX_KEYS
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
