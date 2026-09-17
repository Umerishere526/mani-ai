# ABOUTME: Loads the framework registry and the prompt markdown into the database.
# ABOUTME: Markdown is seed input; once seeded the database is the runtime source of truth.

import asyncio
import json
import pathlib
import sys

import asyncpg
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from mani.config import get_settings  # noqa: E402

PROMPTS_DIR = pathlib.Path(__file__).resolve().parent.parent / "prompts"
FRAMEWORKS_DIR = pathlib.Path(__file__).resolve().parent.parent / "frameworks"


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
    """Split a framework file into its YAML frontmatter (the router and stage data) and body.

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
    }


async def seed() -> None:
    settings = get_settings()
    conn = await asyncpg.connect(settings.database_url)
    try:
        async with conn.transaction():
            framework_files = sorted(FRAMEWORKS_DIR.glob("*.md"))
            if not framework_files:
                raise SystemExit(f"no framework files in {FRAMEWORKS_DIR}")

            for path in framework_files:
                framework = parse_framework(path)
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
                print(f"  {framework['name']:<28} {len(framework['stages'])} stages")
            print(f"frameworks: {len(framework_files)}")

            files = sorted(PROMPTS_DIR.glob("*.md"))
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
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(seed())
