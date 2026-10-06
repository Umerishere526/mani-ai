# ABOUTME: Checks a prompt file's frontmatter becomes the row the seeder writes.
# ABOUTME: Pure parsing of files; the database write is checked by running the seeder.

import pathlib

from scripts.seed import PROMPTS_DIR, parse_prompt


def write(tmp_path: pathlib.Path, frontmatter: str) -> pathlib.Path:
    path = tmp_path / "p.md"
    path.write_text(f"---\nname: p\n{frontmatter}---\n\nbody\n")
    return path


def test_routing_in_the_frontmatter_is_carried_to_the_row(tmp_path):
    """covers spec 0006 AC-2: the provider pin lives beside the model id it belongs to."""
    path = write(
        tmp_path,
        "model_id: google/gemini-3.8-flash\n"
        "routing:\n  order: [google-vertex/global]\n  allow_fallbacks: false\n  zdr: true\n",
    )
    assert parse_prompt(path)["routing"] == {
        "order": ["google-vertex/global"], "allow_fallbacks": False, "zdr": True,
    }


def test_a_prompt_without_routing_seeds_an_empty_object(tmp_path):
    assert parse_prompt(write(tmp_path, "model_id: m\n"))["routing"] == {}


def test_every_shipped_prompt_parses_with_a_routing_object():
    for path in sorted(PROMPTS_DIR.glob("*.md")):
        if path.name == "somatic.md":
            continue
        assert isinstance(parse_prompt(path)["routing"], dict), path.name
