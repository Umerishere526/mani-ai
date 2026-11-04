# ABOUTME: Compares two scenario_check runs saved with --save: behaviour that should stay the same, language that
# ABOUTME: should improve. Reads only the two JSON files; never calls the model or the database.

"""Compare a baseline and an updated scenario_check run.

    .venv/bin/python scripts/compare_runs.py baseline.json updated.json

Behaviour (should match): the framework offered, the person's message the check came after, the order stages were
reached, flags about stages and offers, and whether the body check-in started. A difference is marked !! and read by
a person in the transcripts: one run is noise, so a difference is a reason to look, not a verdict.

Language (should improve): em dashes, figures of speech, words per reply, replies that open without a question,
solution-in-chat flags and the chat's reply shapes.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter

BODY = re.compile(r"\bbody\b", re.IGNORECASE)
WORD = re.compile(r"[A-Za-z']+")
FIRST_SENTENCE = re.compile(r"^.*?(?:[.!?](?=\s|$)|$)", re.S)
# Flags about what a reply says rather than what the conversation did.
LANGUAGE_FLAGS = ("em dash", "solution in chat", "explains people", "announces a question", "talks about them",
                  "insight repeats", "reflect two in a row", "small idea", "shape ",
                  "window on what they ruled out")


def _behaviour(exchanges: list[dict]) -> dict:
    stages: list[str] = []
    for e in exchanges:
        asking = next((row["stage"] for row in e.get("trace") or [] if row.get("asking")), None)
        if asking and (not stages or stages[-1] != asking):
            stages.append(asking)
    checked = next((n for n, e in enumerate(exchanges, start=1) if e.get("checked")), None)
    flags = [f for e in exchanges for f in e.get("flags") or [] if not f.startswith(LANGUAGE_FLAGS)]
    return {
        "offered": next((e["offered"] for e in exchanges if e.get("offered")), None),
        "check after message": checked,
        "stages reached": " > ".join(stages) or "-",
        "body check-in": any(BODY.search(e.get("reply") or "") for e in exchanges),
        "stage and offer flags": len(flags),
    }


def _language(exchanges: list[dict]) -> dict:
    replies = [e.get("reply") or "" for e in exchanges]
    chat = [e for e in exchanges if not e.get("trace")]
    firsts = [FIRST_SENTENCE.match(r.strip()).group(0) for r in replies if r.strip()]
    shapes = Counter(((e.get("thinking") or {}).get("shape") or "-") for e in chat)
    return {
        "em dashes": sum(r.count("—") for r in replies),
        "figures of speech": sum(c.startswith("figure of speech") for e in exchanges for c in e.get("checks") or []),
        "words per reply": round(sum(len(WORD.findall(r)) for r in replies) / max(len(replies), 1)),
        "open without a question": f"{sum('?' not in f for f in firsts)}/{len(firsts)}",
        "solution in chat": sum(f.startswith("solution in chat") for e in exchanges for f in e.get("flags") or []),
        "chat shapes": ", ".join(f"{k} {v}" for k, v in sorted(shapes.items())) or "-",
    }


def _rows(title: str, before: dict, after: dict, *, mark: bool) -> list[str]:
    lines = [f"    {title}"]
    for key in before:
        changed = before[key] != after[key]
        lines.append(f"      {'!! ' if mark and changed else '   '}{key}: {before[key]}  ->  {after[key]}")
    return lines


def compare(baseline: dict, updated: dict) -> tuple[list[str], int]:
    lines: list[str] = []
    differences = 0
    for name in sorted(set(baseline) | set(updated)):
        for style in sorted(set(baseline.get(name, {})) | set(updated.get(name, {}))):
            old, new = baseline.get(name, {}).get(style), updated.get(name, {}).get(style)
            lines.append(f"\n=== {name} / {style} ===")
            if old is None or new is None:
                lines.append(f"    !! only in the {'updated' if old is None else 'baseline'} run")
                differences += 1
                continue
            before, after = _behaviour(old), _behaviour(new)
            differences += sum(before[k] != after[k] for k in before)
            lines += _rows("behaviour (should match)", before, after, mark=True)
            lines += _rows("language (should improve)", _language(old), _language(new), mark=False)
    return lines, differences


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    with open(sys.argv[1]) as a, open(sys.argv[2]) as b:
        lines, differences = compare(json.load(a), json.load(b))
    print("\n".join(lines))
    print(f"\n{differences} behaviour difference(s) to read in the transcripts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
