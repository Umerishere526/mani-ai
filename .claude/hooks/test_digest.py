# ABOUTME: Checks the session digest: which decisions and failed approaches it carries, that it stays under the hook's
# ABOUTME: size limit, and that --check names a journal note without its summary. Run: python3 test_digest.py

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import digest  # noqa: E402

PORT_STATUS = """# Port status

## Decisions in force

- **One model call per turn: the model writes every word Mani says, and code keeps only
  the guarantees** (muhammad, 2026-11-17). Because the state machine failed (2026-11-17).
- **Retired 2026-11-17: the stage walk** (2026-10-13). Because the walk is gone (2026-11-17).
- **A turn held for safety moves nothing** (2026-11-18). Because the facts invited moves (2026-11-18).

## Before it takes real traffic

- **Not a decision** (2026-01-01).
"""


def note(body: str) -> str:
    return body


def make_repo(notes: dict[str, str], port_status: str = PORT_STATUS) -> pathlib.Path:
    root = pathlib.Path(tempfile.mkdtemp())
    (root / "backend").mkdir()
    (root / "backend" / "PORT-STATUS.md").write_text(port_status)
    journal = root / "mani-vault" / "Journal"
    journal.mkdir(parents=True)
    for name, text in notes.items():
        (journal / name).write_text(text)
    return root


GOOD = """---
type: journal
date: 2026-11-17
summary: Flat replies came from the model, not the prompt.
failed:
  - Tried three prompt variants on cheap models; failed because the gap was the model's ability.
---

# Flat replies
"""


def test_decisions_in_force_are_read_whole_and_retired_ones_left_out():
    found = digest.decisions(PORT_STATUS)
    assert [line for line, _ in found] == [
        "One model call per turn: the model writes every word Mani says, and code keeps only the guarantees",
        "A turn held for safety moves nothing",
    ]
    assert found[0][1] == "2026-11-17"


def test_a_note_superseded_whole_is_left_out_and_one_superseded_in_part_keeps_its_failures():
    whole = GOOD.replace("---\n\n# Flat", "---\n> Superseded 2026-11-18 — see [[other]]\n\n# Flat")
    part = GOOD.replace("---\n\n# Flat", "---\n> Superseded 2026-11-18 (the floor part) — see [[other]]\n\n# Flat")
    root = make_repo({"whole-2026-11-17.md": whole, "part-2026-11-17.md": part})
    text = digest.digest(root)
    assert text.count("Tried three prompt variants") == 1 and "part-2026-11-17" in text
    assert "whole-2026-11-17" not in text


def test_the_digest_says_it_is_history_and_stays_under_the_limit():
    many = {f"n{i:03d}-2026-10-{(i % 28) + 1:02d}.md": GOOD.replace("Tried three", f"Tried idea {i} with words " * 3)
            for i in range(200)}
    text = digest.digest(make_repo(many))
    assert len(text) < digest.LIMIT
    assert "history" in text.splitlines()[0].lower() or "history" in text.splitlines()[1].lower()
    assert "left out" in text.splitlines()[-1]


def test_malformed_frontmatter_yields_nothing_and_never_raises():
    root = make_repo({"broken-2026-11-01.md": "---\ntype: journal\nsummary: no closing line\n\n# Broken\n",
                      "colon-2026-11-02.md": GOOD.replace("summary: Flat", "summary: Flat: with a colon")})
    found = {n.name: n for n in digest.notes(root / "mani-vault" / "Journal")}
    assert found["broken-2026-11-01"].summary == ""
    assert found["colon-2026-11-02"].summary == "Flat: with a colon replies came from the model, not the prompt."


def test_check_names_a_note_without_its_summary():
    root = make_repo({"good-2026-11-17.md": GOOD, "bare-2026-11-17.md": "# No frontmatter\n"})
    journal = root / "mani-vault" / "Journal"
    problems = digest.missing(root, [journal / "good-2026-11-17.md", journal / "bare-2026-11-17.md"])
    assert len(problems) == 1 and "bare-2026-11-17" in problems[0]


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} passed")
