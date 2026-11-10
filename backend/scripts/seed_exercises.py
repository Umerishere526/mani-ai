# ABOUTME: Encodes the client's studio recordings, uploads them to the private bucket and seeds admin.exercises.
# ABOUTME: Idempotent: upserts every file and row by id; what the manifest no longer names is removed or set inactive.

import argparse
import asyncio
import json
import pathlib
import subprocess
import sys
import uuid

import asyncpg
import httpx
from pydantic import BaseModel, ConfigDict, Field

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from mani.config import get_settings  # noqa: E402
from mani.llm.schema import LibrarySection  # noqa: E402
from mani.storage import BUCKET  # noqa: E402

# Authored content, like content/frameworks: the manifest is input this script loads into storage and the
# database. The recordings are not in git; `source` is each one's path inside the client's delivery folder.
MANIFEST = pathlib.Path(__file__).resolve().parent.parent / "content" / "exercises" / "exercises.json"


class ManifestEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: uuid.UUID
    source: str
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


def _encode(recording: pathlib.Path) -> bytes:
    """The studio WAV (24-bit 48 kHz stereo) as a 192 kbps stereo MP3: indistinguishable for voice over a
    music bed, at a twelfth of the size, which a phone can stream."""
    return subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(recording), "-vn", "-c:a", "libmp3lame", "-b:a", "192k", "-f", "mp3", "-"],
        capture_output=True, check=True,
    ).stdout


def _upload(http: httpx.Client, entry: ManifestEntry, delivery: pathlib.Path) -> None:
    response = http.post(
        f"/object/{BUCKET}/{entry.filename}",
        content=_encode(delivery / entry.source),
        headers={"Content-Type": "audio/mpeg", "x-upsert": "true"},
    )
    response.raise_for_status()


def _remove_unlisted(http: httpx.Client, entries: list[ManifestEntry]) -> None:
    """Delete every bucket file no entry names, so a replaced recording cannot be served again."""
    response = http.post(f"/object/list/{BUCKET}", json={"prefix": "", "limit": 1000})
    response.raise_for_status()
    unlisted = sorted({o["name"] for o in response.json()} - {e.filename for e in entries})
    if unlisted:
        http.request("DELETE", f"/object/{BUCKET}", json={"prefixes": unlisted}).raise_for_status()
        print(f"removed {len(unlisted)} unlisted files: {', '.join(unlisted)}")


async def _upsert_rows(entries: list[ManifestEntry]) -> None:
    conn = await asyncpg.connect(get_settings().database_url, statement_cache_size=0)
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
                        show_on_home_screen = excluded.show_on_home_screen,
                        is_active = true
                    """,
                    e.id, e.title, e.subtitle, e.description, e.type, e.category.value,
                    e.filename, e.duration_minutes, e.display_order, e.show_on_home_screen,
                )
            # Never deleted, since completions and threads refer to them; listing one again brings it back.
            await conn.execute(
                "update admin.exercises set is_active = false where id <> all($1::uuid[])", [e.id for e in entries]
            )
    finally:
        await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the exercise library from the client's recordings.")
    parser.add_argument("delivery", type=pathlib.Path, help="the client's folder of recordings (LIBRARY AUDIOS)")
    delivery = parser.parse_args().delivery
    entries = load_manifest()
    missing = [e.source for e in entries if not (delivery / e.source).is_file()]
    if missing:
        sys.exit(f"not in {delivery}: {', '.join(missing)}")
    settings = get_settings()
    key = settings.supabase_service_role_key
    with httpx.Client(
        base_url=f"{settings.supabase_url.rstrip('/')}/storage/v1",
        headers={"Authorization": f"Bearer {key}", "apikey": key},
        timeout=120.0,
    ) as http:
        _ensure_bucket(http)
        for entry in entries:
            _upload(http, entry, delivery)
            print(f"  {entry.category.value:<22} {entry.title}")
        # Rows move to the uploaded files before the files they pointed at are deleted.
        asyncio.run(_upsert_rows(entries))
        _remove_unlisted(http, entries)
    print(f"exercises: {len(entries)}")


if __name__ == "__main__":
    main()
