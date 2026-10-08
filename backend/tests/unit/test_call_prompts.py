# ABOUTME: Checks every model call names its thinking level in its own prompt row.
# ABOUTME: The same check refuses a bad row at seed, at an admin edit and before a call goes out.

from __future__ import annotations

import shutil
import uuid

import pytest

from mani.errors import ErrorCategory, ServiceError
from mani.models.rows import Prompt
from mani.prompts import cache
from mani.prompts.calls import CALL_PROMPTS, EFFORTS, effort_for, effort_problem
from mani.prompts.checks import parse_reply_shapes
from scripts import seed


@pytest.fixture
def prompts_dir(tmp_path):
    """A copy of the authored prompt files, for a test to break one of."""
    for path in seed.PROMPTS_DIR.glob("*.md"):
        shutil.copy(path, tmp_path / path.name)
    return tmp_path


def without_line(path, line: str) -> None:
    text = path.read_text()
    assert line in text
    path.write_text(text.replace(line, ""))


def test_every_model_call_has_an_authored_row_with_a_level():
    """Each call reads its level from its own row, so each needs a file the seed accepts."""
    loaded = {p["name"]: p for p in seed.load_prompts()}

    assert CALL_PROMPTS <= loaded.keys()
    for name in CALL_PROMPTS:
        assert loaded[name]["model_parameters"]["reasoning_effort"] in EFFORTS, name
    # A layer is text added to another call's prompt, so it runs at that call's level.
    assert "reasoning_effort" not in loaded["response_format"]["model_parameters"]


@pytest.mark.parametrize("level", [None, "extreme"])
def test_a_call_row_without_a_known_level_stops_the_seed(prompts_dir, level):
    without_line(prompts_dir / "memory_fold.md", "  reasoning_effort: high\n")
    if level is not None:
        path = prompts_dir / "memory_fold.md"
        path.write_text(path.read_text().replace("model_parameters:\n", (
            f"model_parameters:\n  reasoning_effort: {level}\n"
        )))

    with pytest.raises(ValueError, match="memory_fold.md"):
        seed.load_prompts(prompts_dir)


def test_a_model_call_with_no_file_stops_the_seed(prompts_dir):
    (prompts_dir / "voice_translation.md").unlink()

    with pytest.raises(ValueError, match="voice_translation"):
        seed.load_prompts(prompts_dir)


async def test_a_refused_file_stops_the_seed_before_it_connects(prompts_dir, monkeypatch):
    """Nothing is written, not even the frameworks the run would otherwise have upserted."""
    without_line(prompts_dir / "summarization.md", "  reasoning_effort: high\n")
    monkeypatch.setattr(seed, "PROMPTS_DIR", prompts_dir)

    async def connect(*args, **kwargs):
        raise AssertionError("the seed connected to the database")

    monkeypatch.setattr(seed.asyncpg, "connect", connect)

    with pytest.raises(ValueError, match="summarization.md"):
        await seed.seed()


@pytest.mark.parametrize(
    "parameters",
    [{}, {"reasoning_effort": "extreme"}, {"reasoning_effort": ["high"]}, None, "high"],
)
def test_bad_portal_input_is_a_reason_never_a_crash(parameters):
    """The admin routes turn the reason into a 422; a TypeError here would be a 500."""
    assert "memory_fold" in effort_problem("memory_fold", parameters)


def test_a_layer_row_needs_no_level():
    assert effort_problem("response_format", {}) is None


def test_a_call_from_a_row_with_no_level_is_a_config_error():
    row = Prompt(id=uuid.uuid4(), name="mani_base", content="", model_parameters={})

    with pytest.raises(ServiceError) as refused:
        effort_for(row, "mani_base")

    assert refused.value.category is ErrorCategory.CONFIG_ERROR
    assert effort_for(row.model_copy(update={
        "model_parameters": {"reasoning_effort": "low"}
    }), "mani_base") == "low"


def test_a_base_prompt_that_teaches_no_reply_shapes_is_refused(prompts_dir):
    """The guard keeps a reply's shape to the ones mani_base teaches, so seeding none would
    drop every shape the model reports."""
    base = prompts_dir / "mani_base.md"
    text = base.read_text()
    start = text.index("reply_shapes:\n")
    end = text.index("\nstyles:")
    base.write_text(text[:start] + text[end + 1:])

    with pytest.raises(ValueError, match="mani_base.md: mani_base has no non empty reply_shapes map"):
        seed.load_prompts(prompts_dir)


def test_the_shapes_are_read_from_the_base_prompt_trimmed_and_lowercased():
    assert parse_reply_shapes("reply_shapes:\n  Warmth Lead : a\n  presence only: b\n") == {
        "warmth lead", "presence only",
    }


def test_a_base_prompt_whose_shapes_do_not_parse_empties_the_set_and_says_so(caplog):
    with caplog.at_level("ERROR", logger="mani.prompts.cache"):
        assert cache._reply_shapes("identity: [unclosed") == frozenset()
    assert [r.getMessage().split(":")[0] for r in caplog.records] == [
        "reply shapes unreadable, every shape will be dropped"
    ]
