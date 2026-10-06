# ABOUTME: Runs the client's four style conversations in all three styles against the real model.
# ABOUTME: Saves every transcript and prints the counts per run, to compare before and after a change.

from __future__ import annotations

import argparse
import asyncio
import datetime
import json
import pathlib
import statistics
import sys
from dataclasses import asdict

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from mani.db import pool  # noqa: E402
from mani.models.rows import SupportStyle  # noqa: E402
from scripts.client_style_counts import (  # noqa: E402
    QUESTION_RULES, STYLE_READ_CONVERSATION, ConversationCounts, Turn, count_conversation, figures,
    framework_descriptions, restating_read, short_message_turns, shuffled_for_reading, style_read_replies,
)
from scripts.eval_replies import Exchange, _fresh_user, _remove_users, _run_one  # noqa: E402
from scripts.model_trial import instructions_in_force  # noqa: E402

CONVERSATIONS = pathlib.Path(__file__).with_name("client_style_conversations.yaml")
DEFAULT_OUT = pathlib.Path(__file__).resolve().parent.parent / ".eval" / "client_style"
RUNS = 3


def _turns(script: list[str], no_answer_line: str, extra_turns: int) -> list[str]:
    """The client's lines in order. After the first, each one taps the offer if the last reply
    made one, so the conversation reaches the offer the way the client's cadence does."""
    first, *rest = script
    return [first, *(f"@accept|{line}" for line in rest), *[f"@accept|{no_answer_line}"] * extra_turns]


def _turns_of(exchanges: list[Exchange], scripted_turns: int) -> list[Turn]:
    """The exchanges as saved turns. The first `scripted_turns` of them are the client's own
    lines, which answer the client's Mani and not the one that was just asked."""
    return [
        Turn(e.message, e.reply, offered=e.offered, tapped=e.tapped, scripted=i < scripted_turns)
        for i, e in enumerate(exchanges)
    ]


def _transcript_block(exchanges: list[Exchange], counts: ConversationCounts, style: str) -> str:
    lines = [f"#### {style}", ""]
    for exchange in exchanges:
        lines.append(f"- **Person:** {exchange.message}{'  _(tapped)_' if exchange.tapped else ''}")
        lines.append(f"- **Mani:** {exchange.reply}")
        if exchange.offered:
            lines.append(f"  - _offered a framework: {' | '.join(exchange.buttons)}_")
    lines += [
        "",
        f"_questions {counts.questions} ({counts.own_questions} in Mani's own words), stock phrases "
        f"{counts.stock_phrases} in Mani's own words ({counts.all_stock_phrases} in every reply), repeated openers {counts.repeated_openers}, dashes {counts.dashes}, "
        f"feelings never used {len(counts.unused_feelings)}, replies over three sentences "
        f"{counts.long_replies}, offer at {counts.offer_at or 'never'}_",
        "",
    ]
    return "\n".join(lines)


def _mean(values: list[int]) -> str:
    return f"{statistics.fmean(values):.1f}"


def _summary(records: list[dict]) -> str:
    """Means over the runs for each conversation and style, then over every conversation."""
    header = (
        f"{'conversation':<28}{'style':<12}{'replies':>8}{'questions':>10}{'with ?':>8}"
        f"{'stock':>7}{'openers':>9}{'dashes':>8}  offer at (per run)"
    )
    rows = [header]
    styles = [s.value for s in SupportStyle]
    names = list(dict.fromkeys(r["conversation"] for r in records))
    for name in [*names, "all"]:
        for style in styles:
            chosen = [r for r in records if r["style"] == style and name in (r["conversation"], "all")]
            counts = [r["counts"] for r in chosen]
            offers = " ".join(str(c.offer_at or "-") for c in counts) if name != "all" else ""
            rows.append(
                f"{name:<28}{style:<12}{_mean([len(c.replies) for c in counts]):>8}"
                f"{_mean([c.questions for c in counts]):>10}"
                f"{_mean([c.replies_with_a_question for c in counts]):>8}"
                f"{_mean([c.stock_phrases for c in counts]):>7}"
                f"{_mean([c.repeated_openers for c in counts]):>9}"
                f"{_mean([c.dashes for c in counts]):>8}  {offers}"
            )
    return "\n".join(rows)


def _figures(records: list[dict]) -> str:
    """The numbers specification 0002's acceptance criteria are judged on, over the whole check."""
    f = figures([(r["style"], r["run"], r["counts"]) for r in records])
    styles = sorted({r["style"] for r in records})

    def per_style(key: str) -> str:
        return "  ".join(f"{s} {f[f'{key}_{s}']:.2f}" for s in styles)

    return "\n".join([
        f"questions per reply, Mani's own words (AC-6, lower than the baseline's 0.59): {f['questions_per_reply_own']:.2f}"
        f"   all replies: {f['questions_per_reply_all']:.2f}",
        f"replies with two questions (AC-6, none): {f['replies_with_two_questions']:.0f}",
        f"stock phrases per conversation, Mani's own words (AC-7, below the baseline 1.08 / 1.92 / 2.17): "
        f"{per_style('stock_phrases_per_conversation')}",
        f"   all replies: {per_style('stock_phrases_all_per_conversation')}",
        f"stock phrases said twice in one conversation (AC-7, none): {f['phrases_said_twice']:.0f}",
        f"repeated openers per conversation (AC-7, no worse than baseline): "
        f"{per_style('repeated_openers_per_conversation')}",
        f"feelings never used (AC-8, none): {f['unused_feelings']:.0f}",
        f"offered: {f['offered']:.0f} of {f['conversations']:.0f}, at exchange 2 to 4: "
        f"{f['offered_at_2_to_4']:.0f} (AC-10, 33 or more)",
        f"dashes (AC-10, no more than baseline): {f['dashes']:.0f}",
        f"replies over three sentences (AC-12, no more than baseline): {f['long_replies']:.0f}",
        f"questions opening on a lead clause: {f['lead_clauses']:.0f}",
    ])


def _short_replies(records: list[dict]) -> str:
    """Every Mani reply that follows a message of three words or fewer that was not a button tap,
    for a person to read against the question it answered (AC-5)."""
    lines = ["# Replies after a short message", "",
             "Read each against the Mani message above it. `scripted` marks a line from the client's "
             "document, which answered the client's Mani and not necessarily this one.", ""]
    for r in records:
        shown = short_message_turns(r["turns"])
        if not shown:
            continue
        lines += [f"## {r['conversation']} · {r['style']} · run {r['run']}", ""]
        for i in shown:
            turn = r["turns"][i]
            before = r["turns"][i - 1].reply if i else "(the opener)"
            lines += [f"- **Mani before:** {before}", f"  - **Person:** {turn.message}"
                      f"{'  _(scripted)_' if turn.scripted else ''}", f"  - **Mani:** {turn.reply}", ""]
    return "\n".join(lines)


def _style_read(records: list[dict], descriptions: frozenset[str]) -> str:
    """The replies to the first two messages of the panic conversation, every style and run,
    shuffled with the style hidden, for a person to mark against the AC-9 rubric."""
    entries = [
        (f"{r['style']} · run {r['run']} · message {point}", reply)
        for r in records if r["conversation"] == STYLE_READ_CONVERSATION
        for point, reply in enumerate(style_read_replies(r["turns"], descriptions), 1)
    ]
    intro = ("# Style read\n\nMark each \"own style\", \"another style\" or \"none\" against the rubric in "
             "specification 0002 (AC-9). Mani's own words only: the description and permission question "
             "the code adds to an offer are left out.\n")
    return f"{intro}\n{shuffled_for_reading(entries)}"


def _save(
    out_dir: pathlib.Path, meta: dict, records: list[dict], summary: str, descriptions: frozenset[str],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    transcripts = [f"# Client style conversations\n\n{json.dumps(meta, indent=2)}\n"]
    for name in dict.fromkeys(r["conversation"] for r in records):
        transcripts.append(f"## {name}\n")
        for run in sorted({r["run"] for r in records}):
            transcripts.append(f"### Run {run}\n")
            for style in SupportStyle:
                match = next(
                    (r for r in records
                     if (r["conversation"], r["run"], r["style"]) == (name, run, style.value)), None,
                )
                if match:
                    transcripts.append(_transcript_block(match["exchanges"], match["counts"], style.value))
    (out_dir / "transcripts.md").write_text("\n".join(transcripts))
    (out_dir / "summary.txt").write_text(summary + "\n")
    (out_dir / "short_replies.md").write_text(_short_replies(records) + "\n")
    (out_dir / "style_read.md").write_text(_style_read(records, descriptions))
    transcripts_json = [
        {
            "conversation": r["conversation"], "style": r["style"], "run": r["run"],
            "turns": [
                {**asdict(t), "buttons": e.buttons, "framework": e.framework}
                for t, e in zip(r["turns"], r["exchanges"], strict=True)
            ],
        }
        for r in records
    ]
    (out_dir / "transcripts.json").write_text(json.dumps(transcripts_json, indent=2) + "\n")
    counts_json = {
        "meta": meta,
        "conversations": [
            {
                "conversation": r["conversation"], "style": r["style"], "run": r["run"],
                "questions": r["counts"].questions, "own_questions": r["counts"].own_questions,
                "own_replies": r["counts"].own_replies, "stock_phrases": r["counts"].stock_phrases,
                "all_stock_phrases": r["counts"].all_stock_phrases,
                "own_phrases": r["counts"].own_phrases,
                "phrases_said_twice": r["counts"].phrases_said_twice,
                "repeated_openers": r["counts"].repeated_openers, "dashes": r["counts"].dashes,
                "double_question_replies": r["counts"].double_question_replies,
                "long_replies": r["counts"].long_replies,
                "unused_feelings": r["counts"].unused_feelings,
                **{name: getattr(r["counts"], name) for name in QUESTION_RULES.values()},
                "offer_at": r["counts"].offer_at,
                "replies": [asdict(c) for c in r["counts"].replies],
            }
            for r in records
        ],
    }
    (out_dir / "counts.json").write_text(json.dumps(counts_json, indent=2) + "\n")


def _write_restating_read(folders: list[pathlib.Path], out_dir: pathlib.Path) -> pathlib.Path:
    """Build the restating read from the saved checks in `folders`, labelled by folder name."""
    sources = {f.name: json.loads((f / "transcripts.json").read_text()) for f in folders}
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "restating_read.md"
    path.write_text(restating_read(sources, framework_descriptions()))
    return path


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--restating-read", nargs="+", type=pathlib.Path, metavar="CHECK_DIR",
        help="write the file for the restating read from these saved checks, run 1 of each, and stop",
    )
    parser.add_argument("--runs", type=int, default=RUNS, help="how many times to run every conversation")
    parser.add_argument("--conversation", help="run only the conversation with this name")
    parser.add_argument("--out", type=pathlib.Path, help="where to save the transcripts and counts")
    args = parser.parse_args()

    if args.restating_read:
        print(_write_restating_read(args.restating_read, args.out or DEFAULT_OUT / "read-files"))
        return 0

    config = yaml.safe_load(CONVERSATIONS.read_text())
    conversations = [c for c in config["conversations"] if args.conversation in (None, c["name"])]
    out_dir = args.out or DEFAULT_OUT / datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H%M%SZ")

    descriptions = framework_descriptions()
    await pool.open_pool()
    created: list[str] = []
    records: list[dict] = []
    try:
        meta = {**await instructions_in_force(), "runs": str(args.runs)}
        for run in range(1, args.runs + 1):
            for conversation in conversations:
                for style in SupportStyle:
                    user_id = await _fresh_user(f"client-style-{conversation['name']}-r{run}", style)
                    created.append(user_id)
                    script = conversation["turns"][style.value]
                    turns = _turns(script, config["no_answer_line"], config["extra_turns"])
                    exchanges = await _run_one(user_id, style, turns)
                    saved = _turns_of(exchanges, scripted_turns=len(script))
                    counts = count_conversation(saved, descriptions)
                    records.append({
                        "conversation": conversation["name"], "style": style.value, "run": run,
                        "exchanges": exchanges, "turns": saved, "counts": counts,
                    })
                    print(f"run {run}  {conversation['name']:<28}{style.value:<12}"
                          f"questions {counts.questions}  offer at {counts.offer_at or 'never'}", flush=True)
    finally:
        await _remove_users(created)
        await pool.close_pool()

    summary = f"{_summary(records)}\n\n{_figures(records)}"
    _save(out_dir, meta, records, summary, descriptions)
    print(f"\n{json.dumps(meta)}\n\n{summary}\n\nsaved to {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
