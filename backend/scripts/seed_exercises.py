# ABOUTME: Uploads the exercise audio to the private storage bucket and seeds admin.exercises.
# ABOUTME: Idempotent: creates the bucket if missing, upserts every file and every row by id.

import asyncio
import json
import pathlib
import sys
import uuid

import asyncpg
import httpx
from pydantic import BaseModel, ConfigDict, Field

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from mani.config import get_settings  # noqa: E402
from mani.llm.schema import LibrarySection  # noqa: E402
from mani.storage import BUCKET  # noqa: E402

# Authored content, like content/frameworks: the audio and its manifest are input this script
# loads into storage and the database. Nothing in the running service opens these files.
EXERCISES_DIR = pathlib.Path(__file__).resolve().parent.parent / "content" / "exercises"
MANIFEST = EXERCISES_DIR / "exercises.json"


class ManifestEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: uuid.UUID
    filename: str
    title: str
    subtitle: str | None = None
    description: str
    type: str
    category: LibrarySection
    display_order: int = Field(alias="displayOrder")
    show_on_home_screen: bool = Field(alias="showOnHomeScreen")
    duration_minutes: float = Field(alias="durationMinutes")


def load_manifest() -> list[ManifestEntry]:
    raw = json.loads(MANIFEST.read_text())["exercises"]
    return [ManifestEntry.model_validate(entry) for entry in raw]


def _ensure_bucket(http: httpx.Client) -> None:
    """Create the private bucket once. A bucket that already exists is left as it is."""
    if http.get(f"/bucket/{BUCKET}").status_code == 200:
        return
    http.post("/bucket", json={"id": BUCKET, "name": BUCKET, "public": False}).raise_for_status()
    print(f"created bucket {BUCKET}")


def _upload(http: httpx.Client, entry: ManifestEntry) -> None:
    response = http.post(
        f"/object/{BUCKET}/{entry.filename}",
        content=(EXERCISES_DIR / entry.filename).read_bytes(),
        headers={"Content-Type": "audio/mpeg", "x-upsert": "true"},
    )
    response.raise_for_status()


async def _upsert_rows(entries: list[ManifestEntry]) -> None:
    conn = await asyncpg.connect(get_settings().database_url)
    try:
        async with conn.transaction():
            for e in entries:
                await conn.execute(
                    """
                    insert into admin.exercises
                        (id, title, subtitle, description, type, category, audio_path,
                         duration_minutes, display_order, show_on_home_screen)
                    values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    on conflict (id) do update set
                        title = excluded.title,
                        subtitle = excluded.subtitle,
                        description = excluded.description,
                        type = excluded.type,
                        category = excluded.category,
                        audio_path = excluded.audio_path,
                        duration_minutes = excluded.duration_minutes,
                        display_order = excluded.display_order,
                        show_on_home_screen = excluded.show_on_home_screen
                    """,
                    e.id, e.title, e.subtitle, e.description, e.type, e.category.value,
                    e.filename, e.duration_minutes, e.display_order, e.show_on_home_screen,
                )
    finally:
        await conn.close()


def main() -> None:
    entries = load_manifest()
    settings = get_settings()
    key = settings.supabase_service_role_key
    with httpx.Client(
        base_url=f"{settings.supabase_url.rstrip('/')}/storage/v1",
        headers={"Authorization": f"Bearer {key}", "apikey": key},
        timeout=120.0,
    ) as http:
        _ensure_bucket(http)
        for entry in entries:
            _upload(http, entry)
            print(f"  {entry.category.value:<22} {entry.title}")
    asyncio.run(_upsert_rows(entries))
    print(f"exercises: {len(entries)}")


if __name__ == "__main__":
    main()
