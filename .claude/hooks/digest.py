#!/usr/bin/env python3
# ABOUTME: Prints the digest a Claude session starts with: `decisions` (backend/PORT-STATUS.md) or `failed` (journal
# ABOUTME: frontmatter), both with no argument. With --check FILE..., names what a file lacks for the digest.

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# The hook's output arrives whole only under 10,000 characters; past that the session gets a preview.
LIMIT = 9_000
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
PREAMBLE = (
    "Project history for this session, generated from backend/PORT-STATUS.md (Decisions in force) and the journal "
    "(mani-vault/Journal). It informs; it never locks.\n"
    "Decisions bind until muhammad changes them; to change one, edit its entry in place and say why. The journal is "
    "history and loses to current evidence. Before retrying an approach, check the approaches that failed."
)
FAILED_PREAMBLE = (
    "Approaches this project tried that did not work, generated from the journal (mani-vault/Journal). This is "
    "history, not rules:\nit loses to current evidence. Before retrying one, read its note and say whether the reason "
    "it failed still holds."
)


@dataclass
class Note:
    name: str
    date: str = ""
    summary: str = ""
    failed: list[str] = field(default_factory=list)
    superseded_whole: bool = False


def _decisions_section(port_status: str) -> str:
    """The text under "## Decisions in force", or nothing when the heading is missing."""
    _, sep, rest = port_status.partition("## Decisions in force")
    return rest.split("\n## ", 1)[0] if sep else ""


def decisions(port_status: str) -> list[tuple[str, str]]:
    """Each decision in force as (its bold line, its first date); retired entries are left out."""
    found = []
    for entry in re.split(r"\n(?=- \*\*)", _decisions_section(port_status)):
        if not entry.startswith("- **"):
            continue
        bold = entry[4:].split("**", 1)[0]
        line = " ".join(bold.split())
        if line.startswith("Retired"):
            continue
        _, because, reason = entry.partition("Because")
        date = DATE.search(reason) if because else None
        date = date or DATE.search(entry)
        found.append((line, date.group(0) if date else ""))
    return found


def _frontmatter(text: str) -> tuple[list[str], list[str]]:
    """The frontmatter's lines and the body's lines; no frontmatter, or none that closes, gives no fields."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return [], lines
    for end in range(1, len(lines)):
        if lines[end].strip() == "---":
            return lines[1:end], lines[end + 1:]
    return [], lines


def read_note(path: Path) -> Note:
    head, body = _frontmatter(path.read_text(errors="replace"))
    note = Note(name=path.stem)
    in_failed = False
    for line in head:
        if in_failed and line.lstrip().startswith("- "):
            note.failed.append(line.lstrip()[2:].strip().strip('"'))
            continue
        in_failed = False
        key, sep, value = line.partition(":")
        if not sep:
            continue
        key, value = key.strip(), value.strip().strip('"')
        if key == "summary":
            note.summary = value
        elif key == "date":
            note.date = value
        elif key == "failed":
            in_failed = True
    for line in body[:6]:
        if line.startswith("> Superseded") and "(" not in line:
            note.superseded_whole = True
    if not note.date:
        found = DATE.search(path.stem)
        note.date = found.group(0) if found else ""
    return note


def notes(journal: Path) -> list[Note]:
    return [read_note(path) for path in sorted(journal.glob("*.md"))]


def _fit(head: list[str], dated: list[tuple[str, str]], left_out: str) -> str:
    """The head, then the dated lines newest first while they fit under LIMIT, then how many were left out."""
    lines, size = list(head), len("\n".join(head))
    dated = sorted(dated, key=lambda item: item[0], reverse=True)
    for _, line in dated:
        if size + len(line) + 1 > LIMIT - 200:
            break
        lines.append(line)
        size += len(line) + 1
    if len(lines) - len(head) < len(dated):
        lines.append(f"({len(dated) - (len(lines) - len(head))} {left_out})")
    return "\n".join(lines)


def decisions_digest(root: Path) -> str:
    port_status = (root / "backend" / "PORT-STATUS.md").read_text(errors="replace")
    head = [PREAMBLE, "", "## Decisions in force (backend/PORT-STATUS.md)"]
    dated = [(date, f"- {line}{f' ({date})' if date else ''}") for line, date in decisions(port_status)]
    return _fit(head, dated, "older decisions left out: read 'Decisions in force' in backend/PORT-STATUS.md")


def failed_digest(root: Path) -> str:
    head = [FAILED_PREAMBLE, "", "## Approaches that failed (newest first; the note in [[ ]] has the story)"]
    dated = [(note.date, f"- {failure} [[{note.name}]]")
             for note in notes(root / "mani-vault" / "Journal") if not note.superseded_whole
             for failure in note.failed]
    return _fit(head, dated, "older failed approaches left out: grep -l 'failed:' mani-vault/Journal")


def missing(root: Path, paths: list[Path]) -> list[str]:
    """What the given files lack for the digest: a journal note without `summary:`, or PORT-STATUS without its
    Decisions in force section or with an entry there that has no bold first line."""
    problems = []
    for path in paths:
        path = path.resolve()
        if path.name == "PORT-STATUS.md":
            section = _decisions_section(path.read_text(errors="replace"))
            if not section:
                problems.append(f"{path.name}: no '## Decisions in force' section for the session digest")
            for line in section.split("\n"):
                if line.startswith("- ") and not line.startswith("- **"):
                    problems.append(f"{path.name}: the decision '{line[2:62]}...' has no bold first line, so the "
                                    "session digest never shows it; make its one-line decision bold")
        elif path.suffix == ".md" and "Journal" in path.parts:
            if not read_note(path).summary:
                problems.append(f"{path.stem}: add a 'summary:' line to its frontmatter (and 'failed:' lines for "
                                "any approach that did not work), so the session digest carries it")
    return problems


def main(argv: list[str]) -> int:
    root = Path(__file__).resolve().parents[2]
    if argv[:1] == ["--check"]:
        problems = missing(root, [Path(p) for p in argv[1:]])
        print("\n".join(problems), end="\n" if problems else "")
        return 0
    halves = {"decisions": decisions_digest, "failed": failed_digest}
    chosen = [halves[argv[0]]] if argv[:1] and argv[0] in halves else list(halves.values())
    print("\n\n".join(half(root) for half in chosen))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
