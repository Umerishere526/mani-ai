# ABOUTME: Runs scripted conversations through the MVP's prompts and through ours, side by side.
# ABOUTME: The MVP is the bar the client remembers; a person reads the result and judges.

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from mani.db import llm_calls, pool  # noqa: E402
from mani.llm import client  # noqa: E402
from pydantic import Field  # noqa: E402

from mani.llm.schema import Reply, Style  # noqa: E402
from mani.models.rows import SupportStyle  # noqa: E402
from scripts.eval_replies import (  # noqa: E402
    EVAL_NICKNAME,
    SCENARIOS,
    Exchange,
    _fresh_user,
    _run_one,
)
from scripts.seed import parse_prompt  # noqa: E402

BACKEND = pathlib.Path(__file__).resolve().parent.parent
MVP_DIR = BACKEND / "docs" / "mvp-prompts"
OUT_DIR = BACKEND / ".eval"

# What the MVP's mani_base row named, so both sides answer on the same model and temperature.
MVP_MODEL = "google/gemini-3-flash-preview"
MVP_TEMPERATURE = 1.0
STYLE_WINDOW = 7


class MvpStyle(Style):
    """The style the MVP's prompt asks for: a shape and one of its five mirroring voices.

    Kept here, fixed, so the bar does not move when our schema does: without a place for the
    voice its prompt demands, the MVP's first turn ran to the length limit.
    """

    voice: str | None = Field(
        default=None,
        description=(
            "The mirroring voice you used, if you mirrored: naming, receiving, quoting, "
            "transitional, observing. Null if no mirroring."
        ),
    )


class MvpReply(Reply):
    # The wording the baseline runs were made with.
    style: MvpStyle | None = Field(
        default=None,
        description=(
            "Choose before writing text: the response shape and mirroring voice this reply "
            "will use. The shape may repeat; the voice must differ from the last entry in "
            "recent_styles in [ctx]."
        ),
    )

# Conversation before a framework runs: the only part the MVP's two techniques can be compared
# on, and where interrogating and offering too soon show up.
SCENARIO_NAMES = (
    "anxiety_free_chat", "disclosure_no_question_needed", "client_anxiety",
    "client_overthinking", "client_scrolling", "client_stress", "open_losing_someone",
)


def mvp_system_prompt(nickname: str | None, prompts_dir: pathlib.Path = MVP_DIR) -> str:
    """The MVP's system prompt: identity, technique library, user context, response format."""
    body = {name: parse_prompt(prompts_dir / f"{name}.md")["content"]
            for name in ("mani_base", "techniques", "response_format")}
    parts = [body["mani_base"], body["techniques"]]
    if nickname:
        parts.append(f'## User Context\nThe user prefers to be called "{nickname}".')
    parts.append(body["response_format"])
    return "\n\n".join(parts)


def mvp_ctx(recent_styles: list[tuple[str, str | None]]) -> str:
    """The MVP's [ctx] block for a turn before any technique: the cooldown and recent styles."""
    lines = ["cooldown_passed: yes"]
    if recent_styles:
        shown = recent_styles[-STYLE_WINDOW:]
        lines.append("recent_styles: " + " → ".join(f"{s} ({v})" if v else s for s, v in shown))
    return "[ctx]\n" + "\n".join(lines) + "\n[/ctx]\n\n"


async def run_mvp(turns: list[str], nickname: str) -> list[str]:
    """One conversation on the MVP's stack. Raw replies: the MVP regenerated, it did not repair.

    The history carries no [ctx] blocks, although the MVP stored them; that only removes noise
    the MVP itself was fighting. The reply schema's field descriptions are ours, the one part of
    the prompt surface the two sides share.
    """
    system = mvp_system_prompt(nickname)
    history: list[dict[str, str]] = []
    styles: list[tuple[str, str | None]] = []
    replies: list[str] = []
    for message in turns:
        call = await client.complete(
            [{"role": "system", "content": system}, *history,
             {"role": "user", "content": mvp_ctx(styles) + message}],
            MvpReply, model=MVP_MODEL, purpose=llm_calls.Purpose.CHAT, temperature=MVP_TEMPERATURE,
        )
        reply = call.value
        history += [{"role": "user", "content": message}, {"role": "assistant", "content": reply.text}]
        if reply.style is not None:
            styles.append((reply.style.shape, reply.style.voice))
        replies.append(reply.text)
    return replies


def render(name: str, turns: list[str], mvp: list[str], ours: dict[str, list[Exchange]]) -> str:
    """One scenario: each line the person said, then the MVP's reply and each style's under it."""
    lines = [f"## {name}", ""]
    for index, message in enumerate(turns):
        lines += [f"**Person:** {message}", "", f"- **MVP:** {mvp[index]}"]
        for style, exchanges in ours.items():
            exchange = exchanges[index]
            buttons = f"  `[{' / '.join(exchange.buttons)}]`" if exchange.buttons else ""
            lines.append(f"- **{style}:** {exchange.reply}{buttons}")
        lines.append("")
    return "\n".join(lines)


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="baseline", help="names the output file")
    parser.add_argument("--scenario", help="run only this scenario")
    args = parser.parse_args()

    scenarios = [
        s for s in yaml.safe_load(SCENARIOS.read_text())
        if s["name"] in SCENARIO_NAMES and (not args.scenario or s["name"] == args.scenario)
    ]
    await pool.open_pool()
    sections: list[str] = []
    try:
        for scenario in scenarios:
            turns = scenario["turns"]
            mvp = await run_mvp(turns, EVAL_NICKNAME)
            ours = {}
            for style in SupportStyle:
                user_id = await _fresh_user(scenario["name"], style)
                ours[style.value] = await _run_one(user_id, style, turns)
            sections.append(render(scenario["name"], turns, mvp, ours))
            print(f"done: {scenario['name']}")
    finally:
        await pool.close_pool()

    OUT_DIR.mkdir(exist_ok=True)
    path = OUT_DIR / f"{dt.datetime.now():%Y%m%d-%H%M%S}-{args.label}.md"
    path.write_text(f"# MVP vs now: {args.label}\n\n" + "\n\n".join(sections) + "\n")
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
