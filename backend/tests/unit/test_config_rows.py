# ABOUTME: Checks the `replies` and `tuning` rows are refused when broken: at parse, at seed and at cache load.
# ABOUTME: Each refusal names the key and the rule and never echoes the value written.

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager

import pytest
import yaml

from mani.errors import ErrorCategory, ServiceError
from mani.models.rows import Prompt
from mani.prompts import cache
from mani.prompts.checks import content_problem
from scripts import seed

SEEDED = {p["name"]: p["content"] for p in seed.load_prompts()}


def edited(name: str, change) -> str:
    """The seeded row's content after `change` has been applied to its parsed YAML."""
    body = yaml.safe_load(SEEDED[name])
    change(body)
    return yaml.safe_dump(body, sort_keys=False)


def test_the_seeded_files_are_accepted():
    assert [content_problem(name, SEEDED[name]) for name in ("mani_base", "replies", "tuning")] == [None] * 3


def test_a_name_nothing_reads_the_content_of_is_not_checked():
    assert content_problem("title_generation", "{ not yaml") is None


@pytest.mark.parametrize("content", ["- a\n- b\n", "just words", "{ unclosed", ""])
def test_a_body_that_is_not_a_yaml_map_is_refused(content):
    assert "replies" in content_problem("replies", content)
    assert "tuning" in content_problem("tuning", content)


REPLIES_REFUSED = {
    "an unknown key": lambda b: b.update(extra="x"),
    "a missing key": lambda b: b.pop("style_question"),
    "an empty line": lambda b: b.update(style_question="   "),
    "an empty list": lambda b: b.update(after_framework_questions=[]),
    "a greeting field that is not name": lambda b: b["greeting"].update(new="Hi {nickname}"),
    "a positional greeting field": lambda b: b["greeting"].update(new="Hi {}"),
    "a conversion": lambda b: b["greeting"].update(new="Hi {name!r}"),
    "a format spec": lambda b: b["greeting"].update(new="Hi {name:x}"),
    "an unbalanced brace": lambda b: b["greeting"].update(returning="Hi {name"),
    "a missing style": lambda b: b["style_labels"].pop("reflective"),
    "an unknown style": lambda b: b["openers"].update(neutral="Hello"),
    "two labels equal ignoring case": lambda b: b["style_labels"].update(direct="SUPPORTIVE"),
    "a pipe in an after question": lambda b: b.update(after_framework_questions=["a | b"]),
    "a bracket in an after question": lambda b: b.update(after_framework_questions=["a [b]"]),
    "a newline in an after question": lambda b: b.update(after_framework_questions=["a\nb"]),
    "the check lines left in the row": lambda b: b.update(clarification_lines=["Do I have this right?"]),
    "a missing offer": lambda b: b.pop("offer"),
    "an offer without its description": lambda b: b["offer"].update(text="Framework: {name}"),
    "a tell me more without its name": lambda b: b["offer"].update(more_text="{description}"),
    "an offer field that is not name or description": lambda b: b["offer"].update(
        text="{name} {description} {other}"
    ),
    "a positional offer field": lambda b: b["offer"].update(more_text="{name} {description} {}"),
    "a blank offer label": lambda b: b["offer"]["labels"].update(more="   "),
    "a missing offer label": lambda b: b["offer"]["labels"].pop("decline"),
    "two offer labels equal ignoring case": lambda b: b["offer"]["labels"].update(
        more="I WANT TO KEEP TALKING"
    ),
}


@pytest.mark.parametrize("change", REPLIES_REFUSED.values(), ids=REPLIES_REFUSED)
def test_a_replies_row_that_would_break_a_turn_is_refused(change):
    assert content_problem("replies", edited("replies", change))


def test_a_refusal_names_the_key_and_never_the_value_written():
    problem = content_problem(
        "replies", edited("replies", lambda b: b["greeting"].update(new="Hi {secretword}"))
    )

    assert "greeting.new" in problem
    assert "secretword" not in problem


TUNING_REFUSED = {
    "an unknown key": lambda b: b["offers"].update(extra=1),
    "a missing group": lambda b: b.pop("memory"),
    "a context window of 3": lambda b: b["windows"].update(context_window=3),
    "a context window of 101": lambda b: b["windows"].update(context_window=101),
    "max_entry_chars 501": lambda b: b["memory"].update(max_entry_chars=501),
    "a count written as a string": lambda b: b["offers"].update(clear_offer_after="2"),
    "a count written as a boolean": lambda b: b["offers"].update(clear_offer_after=True),
    "a router block left in the row": lambda b: b.update(router={"router_min_exchanges": 2}),
    "an unknown default style": lambda b: b["offers"].update(default_style="neutral"),
}


@pytest.mark.parametrize("change", TUNING_REFUSED.values(), ids=TUNING_REFUSED)
def test_a_tuning_row_with_a_bad_number_is_refused(change):
    assert content_problem("tuning", edited("tuning", change))


def test_a_prompt_directory_with_no_replies_file_stops_the_seed(tmp_path):
    for path in seed.PROMPTS_DIR.glob("*.md"):
        if path.name != "replies.md":
            (tmp_path / path.name).write_text(path.read_text())

    with pytest.raises(ValueError, match="required row replies"):
        seed.load_prompts(tmp_path)


def test_a_prompt_file_with_a_broken_row_stops_the_seed_naming_the_file(tmp_path):
    for path in seed.PROMPTS_DIR.glob("*.md"):
        (tmp_path / path.name).write_text(path.read_text())
    broken = (tmp_path / "tuning.md")
    broken.write_text(broken.read_text().replace("context_window: 20", "context_window: 3"))

    with pytest.raises(ValueError, match=r"tuning.md: tuning is not valid: windows.context_window"):
        seed.load_prompts(tmp_path)


def rows(**content) -> list[Prompt]:
    return [
        Prompt(id=uuid.uuid4(), name=name, content=content.get(name, text))
        for name, text in SEEDED.items()
    ]


@pytest.fixture
def load_with(monkeypatch):
    """Runs the cache's load against these rows, with `snapshot` standing as the earlier one."""

    async def load(prompts: list[Prompt], snapshot=None):
        @asynccontextmanager
        async def admin():
            yield None

        async def active_prompts(_):
            return prompts

        async def active_frameworks(_):
            return []

        monkeypatch.setattr(cache.pool, "as_admin", admin)
        monkeypatch.setattr(cache.config_tables, "list_active_prompts", active_prompts)
        monkeypatch.setattr(cache.config_tables, "list_active_frameworks", active_frameworks)
        monkeypatch.setattr(cache, "_config", snapshot)
        return await cache.load()

    return load


async def test_the_cache_holds_the_parsed_rows(load_with):
    config = await load_with(rows())

    assert config.replies.openers["direct"] == "How can I help you today?"
    assert config.tuning.windows.context_window == 20


@pytest.mark.parametrize("name", ["replies", "tuning"])
async def test_a_missing_required_row_fails_the_load_even_with_an_earlier_snapshot(load_with, name):
    good = await load_with(rows())
    stale = type(good)(**{**good.__dict__, "loaded_at": time.monotonic() - 10_000})

    with pytest.raises(ServiceError) as refused:
        await load_with([p for p in rows() if p.name != name], snapshot=stale)

    assert refused.value.category is ErrorCategory.CONFIG_ERROR


@pytest.mark.parametrize("name", ["replies", "tuning"])
async def test_a_broken_required_row_fails_the_load_even_with_an_earlier_snapshot(load_with, name):
    good = await load_with(rows())
    stale = type(good)(**{**good.__dict__, "loaded_at": time.monotonic() - 10_000})

    with pytest.raises(ServiceError) as refused:
        await load_with(rows(**{name: "not: [valid"}), snapshot=stale)

    assert refused.value.category is ErrorCategory.CONFIG_ERROR
    assert name in str(refused.value)
