# ABOUTME: Loads the framework registry and the prompt markdown into the database.
# ABOUTME: Markdown is seed input; once seeded the database is the runtime source of truth.

import asyncio
import json
import pathlib
import re
import sys

import asyncpg
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from mani.chat.techniques import ENDING_PHASES  # noqa: E402
from mani.config import get_settings  # noqa: E402
from mani.prompts.calls import CALL_PROMPTS, effort_problem  # noqa: E402
from mani.prompts.checks import REQUIRED_PROMPTS, content_problem  # noqa: E402
from mani.prompts.replies import Replies, parse_replies  # noqa: E402
from mani.prompts.tuning import Tuning, parse_tuning  # noqa: E402

# Authored content, not code: markdown is the input this script loads, and once loaded the
# database is what the application reads. Kept outside the `mani` package for that reason -
# nothing in the running service ever opens these files.
CONTENT_DIR = pathlib.Path(__file__).resolve().parent.parent / "content"
PROMPTS_DIR = CONTENT_DIR / "prompts"
FRAMEWORKS_DIR = CONTENT_DIR / "frameworks"


def parse_prompt(path: pathlib.Path) -> dict:
    """Split a prompt file into its YAML frontmatter and its body."""
    raw = path.read_text()
    if not raw.startswith("---"):
        raise ValueError(f"{path.name} has no frontmatter")
    _, frontmatter, body = raw.split("---", 2)
    meta = yaml.safe_load(frontmatter) or {}
    if "name" not in meta:
        raise ValueError(f"{path.name} frontmatter has no name")
    return {
        "id": meta.get("id"),
        "name": meta["name"],
        "description": meta.get("description", ""),
        "content": body.strip(),
        "model_id": meta.get("model_id"),
        "model_parameters": meta.get("model_parameters") or {},
    }


def load_replies() -> Replies:
    """The `replies` row as the file holds it, for the evals and tests that need the lines."""
    return parse_replies(parse_prompt(PROMPTS_DIR / "replies.md")["content"])


def load_tuning() -> Tuning:
    """The `tuning` row as the file holds it."""
    return parse_tuning(parse_prompt(PROMPTS_DIR / "tuning.md")["content"])


def load_prompts(directory: pathlib.Path | None = None) -> list[dict]:
    """Every prompt row to seed, refused with the file named when a model call's row has no
    usable thinking level, when a model call or a required row has no file at all, or when a
    row's content is one the application could not run on.

    Matched by the frontmatter `name`, never the file name, because the name is what the code
    reads the row by.
    """
    directory = directory if directory is not None else PROMPTS_DIR
    files = sorted(directory.glob("*.md"))
    if not files:
        raise ValueError(f"no prompt files in {directory}")
    prompts = []
    for path in files:
        prompt = parse_prompt(path)
        if problem := effort_problem(prompt["name"], prompt["model_parameters"]):
            raise ValueError(f"{path.name}: {problem}")
        # The same check the portal's writes and the cache load make. For mani_base it keeps a
        # reply's shape to the list it teaches, so seeding none would drop them all.
        if problem := content_problem(prompt["name"], prompt["content"]):
            raise ValueError(f"{path.name}: {problem}")
        prompts.append(prompt)
    named = {p["name"] for p in prompts}
    if missing := sorted(CALL_PROMPTS - named):
        raise ValueError(f"no prompt file names the model call {', '.join(missing)}")
    if missing := [name for name in REQUIRED_PROMPTS if name not in named]:
        raise ValueError(f"no prompt file names the required row {', '.join(missing)}")
    return prompts


# A framework is eight lines the model reads, in this order, and nothing else: the client's long
# form lives in docs/specs/, and a file that grows past this would grow the cached prompt with it.
FRAMEWORK_LABELS = (
    "Starts when", "Sounds like", "Skip when", "Stages", "Ends when", "Offer", "Never", "Never",
)
MAX_LINE = 220
STAGES_DIVIDER = " | "
MAX_STAGES_LINE = 320
# Everything else in the frontmatter is data only code reads: the phase machine and the veto.
FRAMEWORK_KEYS = {"id", "name", "summary", "display_order", "phases", "activation"}
ACTIVATION_KEYS = {"never_offer_when_said"}
_STAGE = re.compile(r"(\S+) \((.+)\)")


def _framework_lines(name: str, body: str, phases: list[str]) -> list[str]:
    """The eight labelled lines of a framework body, refused with the reason when any rule breaks."""
    lines = body.strip().split("\n")
    if len(lines) != len(FRAMEWORK_LABELS):
        raise ValueError(
            f"{name}: the body has {len(lines)} lines, not {len(FRAMEWORK_LABELS)} "
            "(a blank line or a heading counts)"
        )
    for number, (line, label) in enumerate(zip(lines, FRAMEWORK_LABELS), start=1):
        found, _, text = line.partition(": ")
        if found != label or not text.strip():
            raise ValueError(f"{name}: line {number} should start with '{label}: ', not {line[:30]!r}")
        cap = MAX_STAGES_LINE if label == "Stages" else MAX_LINE
        if len(line) > cap:
            raise ValueError(f"{name}: the {label} line is {len(line)} characters, over {cap}")

    stages_line = lines[FRAMEWORK_LABELS.index("Stages")].removeprefix("Stages: ")
    # The | marks where the stages Mani learns from what they already said end and the ones they
    # work through together begin. The model reads it; no code does.
    if stages_line.count(STAGES_DIVIDER) != 1:
        raise ValueError(
            f"{name}: the Stages line needs exactly one '{STAGES_DIVIDER.strip()}', between the stages "
            f"they have usually told already and the ones they work through, not "
            f"{stages_line.count(STAGES_DIVIDER)}"
        )
    told, worked = stages_line.split(STAGES_DIVIDER)
    if not told.strip() or not worked.strip():
        raise ValueError(f"{name}: the Stages line has no stage on one side of the '{STAGES_DIVIDER.strip()}'")
    stages = told.split(" > ") + worked.split(" > ")
    named = []
    for stage in stages:
        match = _STAGE.fullmatch(stage)
        if not match:
            raise ValueError(f"{name}: the stage {stage!r} should be an id and a few words in parentheses")
        named.append(match.group(1))
    if phases[:1] != ["offering"]:
        raise ValueError(f"{name}: phases should start with offering")
    if named != phases[1:]:
        raise ValueError(
            f"{name}: the Stages line names {', '.join(named)}, but phases after offering are "
            f"{', '.join(phases[1:])}"
        )
    return lines


def parse_framework(path: pathlib.Path) -> dict:
    """Split a framework file into its YAML frontmatter (the veto and phase data) and body.

    Reuses the same frontmatter/body split as a prompt file - only the fields differ. The
    file's own `id` names the framework; the previous version wrote it by hand alongside
    two hardcoded entries. The body is the eight lines the model reads, checked here so a
    file that breaks the format is never seeded.
    """
    raw = path.read_text()
    if not raw.startswith("---"):
        raise ValueError(f"{path.name} has no frontmatter")
    _, frontmatter, body = raw.split("---", 2)
    meta = yaml.safe_load(frontmatter) or {}
    for required in ("id", "name", "phases"):
        if required not in meta:
            raise ValueError(f"{path.name} frontmatter has no {required}")
    if extra := sorted(set(meta) - FRAMEWORK_KEYS):
        raise ValueError(f"{path.name}: frontmatter keys not allowed: {', '.join(extra)}")
    activation = meta.get("activation") or {}
    if extra := sorted(set(activation) - ACTIVATION_KEYS):
        raise ValueError(f"{path.name}: activation keys not allowed: {', '.join(extra)}")
    vetoes = activation.get("never_offer_when_said", [])
    if not isinstance(vetoes, list) or not all(isinstance(p, str) and p.strip() for p in vetoes):
        raise ValueError(f"{path.name}: never_offer_when_said must be a list of non empty strings")
    lines = _framework_lines(path.name, body, meta["phases"])
    return {
        "id": meta["id"],
        "name": meta["name"],
        "summary": meta.get("summary", ""),
        "body": "\n".join(lines),
        # Read by nothing, but kept readable rather than blank for anyone looking at the table.
        "activation_conditions": lines[0].removeprefix("Starts when: "),
        # The body ending follows each framework's own phases. The files end at `closing`,
        # and this is rebuilt from the file every run, so appending is idempotent.
        "phases": meta["phases"] + list(ENDING_PHASES),
        "display_order": meta.get("display_order", 0),
        "activation": activation,
        # Read by nothing: the stage questions are the Stages line and the ending is the
        # mani_base prompt's `ending` section.
        "stages": {},
    }


async def seed() -> None:
    settings = get_settings()
    # Checked before connecting, so a refused prompt file stops the run with nothing opened.
    prompts = load_prompts()
    conn = await asyncpg.connect(settings.database_url)
    try:
        async with conn.transaction():
            framework_files = sorted(FRAMEWORKS_DIR.glob("*.md"))
            if not framework_files:
                raise SystemExit(f"no framework files in {FRAMEWORKS_DIR}")

            # Every file is checked before any is written, so a refusal leaves nothing half seeded.
            frameworks = [parse_framework(path) for path in framework_files]
            for framework in frameworks:
                await conn.execute(
                    """
                    insert into admin.frameworks
                        (id, name, summary, body, activation_conditions, phases,
                         display_order, activation, stages)
                    values ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9::jsonb)
                    on conflict (id) do update set
                        name = excluded.name,
                        summary = excluded.summary,
                        body = excluded.body,
                        activation_conditions = excluded.activation_conditions,
                        phases = excluded.phases,
                        display_order = excluded.display_order,
                        activation = excluded.activation,
                        stages = excluded.stages
                    """,
                    framework["id"],
                    framework["name"],
                    framework["summary"],
                    framework["body"],
                    framework["activation_conditions"],
                    framework["phases"],
                    framework["display_order"],
                    json.dumps(framework["activation"]),
                    json.dumps(framework["stages"]),
                )
                print(f"  {framework['name']:<28} {len(framework['phases'])} phases")
            print(f"frameworks: {len(framework_files)}")

            for prompt in prompts:
                await conn.execute(
                    """
                    insert into admin.prompts
                        (id, name, description, content, model_id, model_parameters)
                    values (coalesce($1::uuid, gen_random_uuid()), $2, $3, $4, $5, $6::jsonb)
                    on conflict (name) do update set
                        description = excluded.description,
                        content = excluded.content,
                        model_id = excluded.model_id,
                        model_parameters = excluded.model_parameters
                    """,
                    prompt["id"],
                    prompt["name"],
                    prompt["description"],
                    prompt["content"],
                    prompt["model_id"],
                    json.dumps(prompt["model_parameters"]),
                )
                print(f"  {prompt['name']:<18} {len(prompt['content']):>6} chars")
            print(f"prompts: {len(prompts)}")
    finally:
        await conn.close()


if __name__ == "__main__":
    try:
        asyncio.run(seed())
    except ValueError as refused:
        sys.exit(f"seed refused, nothing written: {refused}")
