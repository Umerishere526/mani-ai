# ABOUTME: Uploads the exercise audio to the private storage bucket and seeds admin.library_topics and admin.exercises.
# ABOUTME: Idempotent: creates the bucket if missing, upserts every file and every row by id.

import asyncio
import json
import pathlib
import sys
import uuid

import asyncpg
import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from mani.config import get_settings
from mani.llm.schema import LibrarySection
from mani.storage import BUCKET

# Authored content, like content/frameworks: the audio and its manifest are input this script
# loads into storage and the database. Nothing in the running service opens these files.
EXERCISES_DIR = pathlib.Path(__file__).resolve().parent.parent / "content" / "exercises"
MANIFEST = EXERCISES_DIR / "exercises.json"


class ManifestCollect(BaseModel):
    """Another topic's exercises, listed in this one under a subcategory of its own."""

    model_config = ConfigDict(extra="forbid")

    subcategory: str
    topic: LibrarySection


class ManifestTopic(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: LibrarySection
    title: str
    blurb: str
    display_order: int = Field(alias="displayOrder")
    collects: list[ManifestCollect] = []

    @model_validator(mode="after")
    def _collects_only_other_topics(self) -> "ManifestTopic":
        if any(c.topic == self.id for c in self.collects):
            raise ValueError(f"{self.id} collects its own exercises")
        return self


class ManifestEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: uuid.UUID
    # Null until the client records it: the app lists it as coming soon, with no audio and no length.
    filename: str | None
    title: str
    subtitle: str | None = None
    description: str
    type: str
    category: LibrarySection
    display_order: int = Field(alias="displayOrder")
    show_on_home_screen: bool = Field(alias="showOnHomeScreen")
    duration_minutes: float | None = Field(alias="durationMinutes")

    @model_validator(mode="after")
    def _a_recording_has_a_length(self) -> "ManifestEntry":
        if (self.filename is None) != (self.duration_minutes is None):
            raise ValueError(f"{self.title}: a recording needs its length, and an unrecorded item has neither")
        return self


def load_manifest() -> list[ManifestEntry]:
    raw = json.loads(MANIFEST.read_text())["exercises"]
    return [ManifestEntry.model_validate(entry) for entry in raw]


def load_topics() -> list[ManifestTopic]:
    raw = json.loads(MANIFEST.read_text())["topics"]
    return [ManifestTopic.model_validate(topic) for topic in raw]


class TopicLink(BaseModel):
    topic_id: LibrarySection
    exercise_id: uuid.UUID
    subcategory: str
    display_order: int


def topic_links(topics: list[ManifestTopic], entries: list[ManifestEntry]) -> list[TopicLink]:
    """Every exercise a topic collects from another, subcategory by subcategory, each in its own topic's order."""
    links = []
    for topic in topics:
        for collect in topic.collects:
            collected = sorted((e for e in entries if e.category == collect.topic), key=lambda e: e.display_order)
            links += [
                TopicLink(topic_id=topic.id, exercise_id=e.id, subcategory=collect.subcategory,
                          display_order=len(links) + n)
                for n, e in enumerate(collected)
            ]
    return links


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


async def _upsert_rows(topics: list[ManifestTopic], entries: list[ManifestEntry]) -> None:
    conn = await asyncpg.connect(get_settings().database_url)
    try:
        async with conn.transaction():
            for t in topics:
                await conn.execute(
                    """
                    insert into admin.library_topics (id, title, blurb, display_order)
                    values ($1, $2, $3, $4)
                    on conflict (id) do update set
                        title = excluded.title,
                        blurb = excluded.blurb,
                        display_order = excluded.display_order
                    """,
                    t.id.value, t.title, t.blurb, t.display_order,
                )
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
            # The manifest's links replace a topic's, so one it no longer collects leaves that topic's listing.
            await conn.execute(
                "delete from admin.exercise_topic_links where topic_id = any($1::text[])",
                [t.id.value for t in topics],
            )
            await conn.executemany(
                "insert into admin.exercise_topic_links (topic_id, exercise_id, subcategory, display_order) "
                "values ($1, $2, $3, $4)",
                [
                    (k.topic_id.value, k.exercise_id, k.subcategory, k.display_order)
                    for k in topic_links(topics, entries)
                ],
            )
    finally:
        await conn.close()


def main() -> None:
    topics = load_topics()
    entries = load_manifest()
    recorded = [e for e in entries if e.filename is not None]
    missing = [e.filename for e in recorded if not (EXERCISES_DIR / e.filename).is_file()]
    if missing:
        # The audio is client content and stays off GitHub, so a fresh clone has none of it.
        sys.exit(
            f"missing audio in {EXERCISES_DIR}: {', '.join(missing)}. The files are not in git; copy them from "
            "the production `exercises` bucket, or convert the client's recording with scripts/convert_audio.sh."
        )
    settings = get_settings()
    key = settings.supabase_service_role_key
    with httpx.Client(
        base_url=f"{settings.supabase_url.rstrip('/')}/storage/v1",
        headers={"Authorization": f"Bearer {key}", "apikey": key},
        timeout=120.0,
    ) as http:
        _ensure_bucket(http)
        for entry in recorded:
            _upload(http, entry)
            print(f"  {entry.category.value:<22} {entry.title}")
    asyncio.run(_upsert_rows(topics, entries))
    print(f"topics: {len(topics)}, exercises: {len(entries)} ({len(recorded)} recorded)")


if __name__ == "__main__":
    main()
