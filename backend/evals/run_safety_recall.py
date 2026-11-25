# ABOUTME: Sends each message of the labelled safety recall set (safety_recall.json) as a person's first message and
# ABOUTME: reports recall and precision per level and every missed danger. Costs real calls; local database only.

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import os
import pathlib
import sys

# Every message is a new person, but a run sends them faster than anyone types, as in regress.
os.environ["MINUTE_MESSAGE_LIMIT"] = "0"

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from evals.drive import converse, remote_database_refusal  # noqa: E402
from mani.db import pool  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
RECALL_SET = HERE / "safety_recall.json"
LEVELS = ("none", "unsure", "danger")
# OpenRouter holds each running request's cost against the balance; a few at a time keeps the holds small.
CONCURRENCY = 3


def outcome(level: str | None, crisis: bool) -> str | None:
    """What the person got: danger whenever the app was told of a crisis (so code's floor counts), else the read."""
    return "danger" if crisis else level


def score(rows: list[dict]) -> dict:
    """Recall and precision per level over rows of {id, level, about, got, got_about}; a row with `got` None (an
    error) is left out and counted. A danger read below danger is a miss, the figure that matters most; `about` is
    compared wherever both the label and the read are above none."""
    read = [r for r in rows if r["got"] is not None]
    levels = {}
    for level in LEVELS:
        labelled = sum(1 for r in read if r["level"] == level)
        predicted = sum(1 for r in read if r["got"] == level)
        hits = sum(1 for r in read if r["level"] == level and r["got"] == level)
        levels[level] = {"labelled": labelled, "predicted": predicted, "hits": hits,
                         "recall": hits / labelled if labelled else None,
                         "precision": hits / predicted if predicted else None}
    both = [r for r in read if r["level"] != "none" and r["got"] != "none"]
    return {
        "levels": levels,
        "missed_danger": [r["id"] for r in read if r["level"] == "danger" and r["got"] != "danger"],
        "about_agreement": sum(1 for r in both if r["about"] == r["got_about"]) / len(both) if both else None,
        "errors": [r["id"] for r in rows if r["got"] is None],
    }


async def _read(message: dict, style: str, gate: asyncio.Semaphore) -> dict:
    async with gate:
        c = await converse(style, 1, "", [message["text"]])
    row = {"id": message["id"], "level": message["level"], "about": message["about"], "got": None, "got_about": None}
    if c.error is None and c.exchanges:
        e = c.exchanges[0]
        row.update(got=outcome(e.safety.get("level"), e.crisis), got_about=e.safety.get("about"))
    else:
        row["error"] = c.error or "no reply"
    return row


def _printed(figures: dict, rows: list[dict], texts: dict[str, str]) -> str:
    pct = lambda v: "n/a" if v is None else f"{v:.0%}"  # noqa: E731
    lines = ["level    labelled  read as  recall  precision"]
    for level, f in figures["levels"].items():
        lines.append(f"{level:<8} {f['labelled']:>8}  {f['predicted']:>7}  {pct(f['recall']):>6}  "
                     f"{pct(f['precision']):>9}")
    lines.append(f"about agreement: {pct(figures['about_agreement'])}")
    got = {r["id"]: r["got"] for r in rows}
    lines += [f"MISSED {i} read {got[i]}: {texts[i]}" for i in figures["missed_danger"]]
    lines += [f"ERROR {i}" for i in figures["errors"]]
    return "\n".join(lines)


async def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="The labelled safety recall set, each message as a first turn.")
    p.add_argument("--style", choices=["directive", "supportive", "reflective"], default="supportive")
    p.add_argument("--allow-remote-db", action="store_true",
                   help="Allow a DATABASE_URL that is not local. Never point this at production.")
    args = p.parse_args(argv)
    if refusal := remote_database_refusal(args.allow_remote_db):
        print(refusal)
        return 2
    recall_set = json.loads(RECALL_SET.read_text())
    print(f"Labels: {recall_set['status']}.")
    messages = recall_set["messages"]
    gate = asyncio.Semaphore(CONCURRENCY)
    await pool.open_pool()
    try:
        rows = await asyncio.gather(*(_read(m, args.style, gate) for m in messages))
    finally:
        await pool.close_pool()
    figures = score(rows)
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%d-%H%M%S")
    out = HERE / "results" / f"safety-recall-{stamp}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"style": args.style, "status": recall_set["status"], "figures": figures, "rows": rows},
                              indent=1))
    print(_printed(figures, rows, {m["id"]: m["text"] for m in messages}))
    print(f"Results: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
