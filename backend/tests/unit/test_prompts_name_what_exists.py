# ABOUTME: Checks no prompt text names an index section or [ctx] line the code no longer sends.
# ABOUTME: Reads the prompt files and the string literals in mani/, so no model or database is needed.

from __future__ import annotations

import ast
import pathlib

import pytest

from scripts.seed import PROMPTS_DIR

MANI_DIR = pathlib.Path(__file__).resolve().parents[2] / "mani"

# Index sections and [ctx] lines a framework no longer has. A prompt that still names one tells
# the model to read something that is not there, and every other test stays green.
REMOVED = (
    "Use it when", "Telling them apart", "Never offer one when", "Finding the fit",
    "offer_ask", "offer_purpose", "offer_lines", "model question", "stage_note",
)


def _prompt_strings():
    for path in sorted(PROMPTS_DIR.glob("*.md")):
        yield path.name, path.read_text()
    for path in sorted(MANI_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text())
        docstrings = {
            id(node.body[0].value)
            for node in ast.walk(tree)
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and node.body and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
                yield f"{path.relative_to(MANI_DIR.parent)}:{node.lineno}", node.value


@pytest.mark.parametrize("name", REMOVED)
def test_no_prompt_text_names_what_the_model_no_longer_receives(name):
    found = [where for where, text in _prompt_strings() if name in text]
    assert found == [], f"{name!r} is named in {found}"
