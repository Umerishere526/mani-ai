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

from mani.chat.repairs import template_slots  # noqa: E402
from mani.chat.techniques import OFFERING  # noqa: E402
from mani.config import get_settings  # noqa: E402
from mani.models.rows import ENDING_STAGES, SupportStyle  # noqa: E402

# Authored content, not code: markdown is the input this script loads, and once loaded the
# database is what the application reads. Kept outside the `mani` package for that reason -
# nothing in the running service ever opens these files.
CONTENT_DIR = pathlib.Path(__file__).resolve().parent.parent / "content"
PROMPTS_DIR = CONTENT_DIR / "prompts"
# Prompt rows no turn reads any more: switched off on every seed, kept for the calls that reference them.
RETIRED_PROMPTS = ("mani_base", "response_format", "style_directive", "style_supportive", "style_reflective")
FRAMEWORKS_DIR = CONTENT_DIR / "frameworks"

# Only the files directly in frameworks/ are seeded. A framework moved into frameworks/paused/ is
# left out of the registry (its row is set inactive, never deleted, because threads and exercises
# refer to it) and comes back by moving the file up again.
# The somatic route is authored once and appended to every framework, rather than repeated in
# each framework file. It is not a prompt row and not a composer layer - its two stages are
# merged into each framework's phases and stages here, so the phase machine and [ctx] handle
# them like any other stage. Skipped in the prompts loop below for the same reason.
SOMATIC_FILE = PROMPTS_DIR / "somatic.md"
# Framework Landing, the shared last stage of every framework (muhammad, 2026-11-06), merged the same way: after the
# framework's own stages and before the closing.
LANDING_FILE = PROMPTS_DIR / "landing.md"
LANDING = "landing"
_FENCED_YAML = re.compile(r"```yaml\n(.*?)\n```", re.DOTALL)


def _somatic_block() -> dict:
    match = _FENCED_YAML.search(SOMATIC_FILE.read_text())
    if not match:
        raise ValueError(f"{SOMATIC_FILE.name} has no fenced yaml stages block")
    return yaml.safe_load(match.group(1)) or {}


def load_somatic_stages() -> dict:
    """The shared somatic route's stage defs, from the fenced yaml block in somatic.md."""
    stages = _somatic_block().get("stages")
    if not stages:
        raise ValueError(f"{SOMATIC_FILE.name} yaml block has no stages")
    return stages


def load_landing_stage() -> dict:
    """The shared landing stage's def, from the fenced yaml block in landing.md."""
    match = _FENCED_YAML.search(LANDING_FILE.read_text())
    stage = ((yaml.safe_load(match.group(1)) or {}).get("stages") or {}).get(LANDING) if match else None
    if not stage:
        raise ValueError(f"{LANDING_FILE.name} has no {LANDING} stage")
    return stage


def with_landing(framework: dict) -> dict:
    """The framework with the shared landing stage after its own last stage."""
    return {
        **framework,
        "phases": [*framework["phases"], LANDING],
        "stages": {**framework["stages"], LANDING: load_landing_stage()},
    }


def somatic_phases() -> list[str]:
    """The somatic stages appended to every framework's phases: all of them but the ones somatic.md pauses, so a
    paused body check-in ends the questions on the closing choices (muhammad, 2026-11-05)."""
    paused = set(_somatic_block().get("paused") or [])
    return [stage for stage in load_somatic_stages() if stage not in paused]


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


def parse_framework(path: pathlib.Path) -> dict:
    """Split a framework file into its YAML frontmatter (the activation and stage data) and body.

    Reuses the same frontmatter/body split as a prompt file - only the fields differ. The
    file's own `id` names the framework; the previous version wrote it by hand alongside
    two hardcoded entries.
    """
    raw = path.read_text()
    if not raw.startswith("---"):
        raise ValueError(f"{path.name} has no frontmatter")
    _, frontmatter, body = raw.split("---", 2)
    meta = yaml.safe_load(frontmatter) or {}
    for required in ("id", "name", "phases"):
        if required not in meta:
            raise ValueError(f"{path.name} frontmatter has no {required}")
    activation = meta.get("activation") or {}
    return {
        "id": meta["id"],
        "name": meta["name"],
        "summary": meta.get("summary", ""),
        "body": body.strip(),
        # No longer read for routing - admin.frameworks.activation carries that now - but
        # kept human-readable rather than blank, for anyone looking at the table directly.
        "activation_conditions": activation.get("central_indication", ""),
        "phases": meta["phases"],
        "display_order": meta.get("display_order", 0),
        "activation": activation,
        "stages": meta.get("stages") or {},
        "confirm_phrases": meta.get("confirm_phrases") or [],
    }


def missing_for_activation(framework: dict) -> list[str]:
    """What an active framework lacks of the content the chat reads, named by its path in the
    file. Empty when it can be seeded active, so a paused framework moved back fails here, not in
    a live chat (spec 0006, AC-13)."""
    stages = framework["stages"]
    offering = stages.get(OFFERING) or {}
    missing = []
    for style in SupportStyle:
        offer = (offering.get("offer") or {}).get(style.value)
        if not offer or template_slots(offer)[1] is None:
            missing.append(f"stages.offering.offer.{style.value} with a <going_through> slot")
        for key in ("keep_chatting", "explain"):
            if not (offering.get(key) or {}).get(style.value):
                missing.append(f"stages.offering.{key}.{style.value}")
    for phase in framework["phases"]:
        if phase == OFFERING or phase in ENDING_STAGES:
            continue
        stage = stages.get(phase) or {}
        if not stage.get("intro") and not stage.get("no_intro"):
            missing.append(f"stages.{phase}.intro")
        missing += [f"stages.{phase}.ask.{style.value}" for style in SupportStyle
                    if not (stage.get("ask") or {}).get(style.value)]
    return missing


async def seed() -> None:
    settings = get_settings()
    conn = await asyncpg.connect(settings.database_url)
    try:
        async with conn.transaction():
            framework_files = sorted(FRAMEWORKS_DIR.glob("*.md"))
            if not framework_files:
                raise SystemExit(f"no framework files in {FRAMEWORKS_DIR}")

            somatic_stages = load_somatic_stages()
            appended = somatic_phases()

            for path in framework_files:
                framework = with_landing(parse_framework(path))
                missing = missing_for_activation(framework)
                if missing:
                    raise SystemExit(f"{path.name} cannot be active, it lacks: {', '.join(missing)}")
                # Append the shared somatic route after each framework's own phases. The files
                # end at `closing`, and this is rebuilt from the file every run, so appending is
                # idempotent - there is nothing to dedupe.
                framework["phases"] = framework["phases"] + appended
                framework["stages"] = {**framework["stages"], **somatic_stages}
                await conn.execute(
                    """
                    insert into admin.frameworks
                        (id, name, summary, body, activation_conditions, phases,
                         display_order, activation, stages, confirm_phrases, is_active)
                    values ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9::jsonb, $10, true)
                    on conflict (id) do update set
                        is_active = true,
                        name = excluded.name,
                        summary = excluded.summary,
                        body = excluded.body,
                        activation_conditions = excluded.activation_conditions,
                        phases = excluded.phases,
                        display_order = excluded.display_order,
                        activation = excluded.activation,
                        stages = excluded.stages,
                        confirm_phrases = excluded.confirm_phrases
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
                    framework["confirm_phrases"],
                )
                print(f"  {framework['name']:<28} {len(framework['stages'])} stages")
            seeded_ids = [parse_framework(path)["id"] for path in framework_files]
            paused = await conn.fetch(
                "update admin.frameworks set is_active = false "
                "where is_active and not (id = any($1::text[])) returning id",
                seeded_ids,
            )
            for row in paused:
                print(f"  {row['id']:<28} paused")
            print(f"frameworks: {len(framework_files)}")

            # somatic.md is the merge source above, not a prompt row.
            files = [p for p in sorted(PROMPTS_DIR.glob("*.md")) if p not in (SOMATIC_FILE, LANDING_FILE)]
            if not files:
                raise SystemExit(f"no prompt files in {PROMPTS_DIR}")

            for path in files:
                prompt = parse_prompt(path)
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
            print(f"prompts: {len(files)}")
            # The layers the old path composed, before every turn spoke in voice.md (muhammad, 2026-10-27). Named
            # rather than "every row with no file", so a prompt made in the portal is never switched off.
            retired = await conn.fetch(
                "update admin.prompts set is_active = false "
                "where is_active and name = any($1::text[]) returning name",
                list(RETIRED_PROMPTS),
            )
            for row in retired:
                print(f"  {row['name']:<18} retired")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(seed())
