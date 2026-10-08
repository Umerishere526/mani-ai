# ABOUTME: Checks no prompt text names an index section or [ctx] line the code no longer sends.
# ABOUTME: Reads the prompt files and the string literals in mani/, so no model or database is needed.

from __future__ import annotations

import ast
import pathlib
import re

import pytest

from scripts.seed import PROMPTS_DIR

BACKEND_DIR = pathlib.Path(__file__).resolve().parents[2]
MANI_DIR = BACKEND_DIR / "mani"

# Index sections and [ctx] lines a framework no longer has. A prompt that still names one tells
# the model to read something that is not there, and every other test stays green.
REMOVED = (
    "Use it when", "Telling them apart", "Never offer one when", "Finding the fit",
    "offer_ask", "offer_purpose", "offer_lines", "model question", "stage_note", "closest_fit",
    "offer_fit", "stage_purpose", "stage_listen_for", "stage_ready_when", "stage_boundaries",
    "stage_if_unclear", "stage_ask", "next_stage",
    "their_last", "clarification_available", "after_framework_question", "framework_shortlist",
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
    # Whole words, so `after_framework_question` is not found in `after_framework_questions`.
    named = re.compile(rf"(?<!\w){re.escape(name)}(?!\w)")
    found = [where for where, text in _prompt_strings() if named.search(text)]
    assert found == [], f"{name!r} is named in {found}"


# Lines Mani sends and numbers a conversation runs on used to be constants here; they live in the
# `replies` and `tuning` rows now, and a module that binds one again has put a second home back.
REMOVED_NAMES = (
    "DEFAULT_NAME", "STYLE_QUESTION", "STYLE_OPTIONS", "OPENERS", "AFTER_FRAMEWORK_QUESTIONS",
    "CLARIFICATION_QUESTIONS", "TELL_ME_ABOUT_THIS_LABEL", "EXPLAIN_LABELS",
    "_VAGUE_REPLIES", "_HEARD_PHRASES", "_CORRECTION_PHRASES", "classify_reply", "clarification_used",
    "CLEAR_OFFER_AFTER", "CLEAR_COOLDOWN_AFTER_DECLINE", "COOLDOWN_AFTER_COMPLETE", "DEFAULT_STYLE",
    "RECENT_OPENERS_WORDS", "RECENT_OPENERS_WINDOW",
    "RECENCY_WEIGHTS", "STRONG_WEIGHT", "SIGNAL_WEIGHT", "PROMOTED_FLOOR", "ROUTER_MIN_EXCHANGES",
    "CONTEXT_WINDOW", "SUMMARY_THRESHOLD", "STYLE_WINDOW", "TITLE_AFTER_MESSAGES",
    "ENDING_TURN_CAP",
    "MAX_ENTRIES", "MAX_ENTRY_CHARS", "IDLE_AFTER",
)


def _module_level_names(source: str) -> set[str]:
    names: set[str] = set()
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
    return names


def _bound_at_module_level(*directories: pathlib.Path) -> list[str]:
    return [
        f"{path.relative_to(directory.parent)}: {name}"
        for directory in directories
        for path in sorted(directory.rglob("*.py"))
        for name in sorted(_module_level_names(path.read_text()) & set(REMOVED_NAMES))
    ]


def test_no_module_binds_a_name_whose_value_moved_into_the_replies_or_tuning_rows():
    assert _bound_at_module_level(MANI_DIR, BACKEND_DIR / "scripts") == []


def test_a_module_that_binds_a_removed_name_is_found(tmp_path):
    (tmp_path / "back.py").write_text(
        'OPENERS = {}\nSTYLE_WINDOW: int = 7\nfine = 1\n\ndef classify_reply(text):\n    return None\n'
    )

    assert [found.split(": ")[1] for found in _bound_at_module_level(tmp_path)] == [
        "OPENERS", "STYLE_WINDOW", "classify_reply"
    ]
