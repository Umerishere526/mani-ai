# ABOUTME: Checks the prompt still carries the clarification lines the code looks for in Mani's past replies.
# ABOUTME: Reads the authored prompt file directly, so no model call or database is needed.

from __future__ import annotations

import yaml

from mani.chat.greeting import CLARIFICATION_QUESTIONS
from scripts.seed import PROMPTS_DIR, parse_prompt


def test_the_clarification_lines_match_the_ones_the_code_looks_for():
    """context.clarification_used finds these lines in Mani's past replies to know the check was
    asked. A reworded line is never found, so the check would be offered again and again."""
    body = parse_prompt(PROMPTS_DIR / "response_format.md")["content"]
    entry = yaml.safe_load(body)["ctx"]["clarification_available"].lower()
    assert [line for line in CLARIFICATION_QUESTIONS if line not in entry] == []
