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

# Phase order is the state machine: a turn may hold or move back, never skip forward.
# Sourced from the previous implementation's constants/techniqueSteps.ts.
FRAMEWORKS = [
    {
        "id": "thought_reframing",
        "name": "Thought Reframing",
        "summary": "Surface a painful thought, separate it from the person, and test it.",
        "body": "",
        "activation_conditions": "A specific self-critical or catastrophic thought is stated.",
        "phases": ["offering", "surface", "externalize", "explore", "land", "ground"],
        "display_order": 1,
    },
    {
        "id": "abcde",
        "name": "ABCDE",
        "summary": "Walk an activating event through belief, consequence, dispute and effect.",
        "body": "",
        "activation_conditions": "A situation and a reaction to it are both present.",
        "phases": [
            "offering",
            "activate",
            "belief",
            "consequence",
            "dispute",
            "effect",
            "ground",
        ],
        "display_order": 2,
    },
]


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


async def seed() -> None:
    settings = get_settings()
    conn = await asyncpg.connect(settings.database_url)
    try:
        async with conn.transaction():
            for framework in FRAMEWORKS:
                await conn.execute(
                    """
                    insert into admin.frameworks
                        (id, name, summary, body, activation_conditions, phases, display_order)
                    values ($1, $2, $3, $4, $5, $6, $7)
                    on conflict (id) do update set
                        name = excluded.name,
                        summary = excluded.summary,
                        activation_conditions = excluded.activation_conditions,
                        phases = excluded.phases,
                        display_order = excluded.display_order
                    """,
                    framework["id"],
                    framework["name"],
                    framework["summary"],
                    framework["body"],
                    framework["activation_conditions"],
                    framework["phases"],
                    framework["display_order"],
                )
            print(f"frameworks: {len(FRAMEWORKS)}")

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
