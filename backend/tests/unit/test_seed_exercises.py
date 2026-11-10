# ABOUTME: Checks the committed exercise manifest before anything is uploaded from it, and that a seed
# ABOUTME: leaves the bucket holding only the files the manifest names.

import json

import httpx
import pytest
from pydantic import ValidationError

from mani.llm.schema import LibrarySection
from scripts.seed_exercises import ManifestEntry, _remove_unlisted, load_manifest


def test_every_manifest_entry_names_its_own_recording_and_a_known_section():
    entries = load_manifest()

    assert len(entries) == 30
    assert len({e.id for e in entries}) == len({e.source for e in entries}) == len({e.filename for e in entries}) == 30
    for entry in entries:
        assert entry.source.endswith(".wav"), entry.source
        assert entry.category in set(LibrarySection)
        assert entry.duration_minutes > 0


def test_an_entry_with_an_unknown_section_is_refused():
    with pytest.raises(ValidationError):
        ManifestEntry.model_validate({
            "id": "4847c6ce-b2cd-46c4-a918-dd2c185237e0", "source": "X/x.wav", "filename": "x.mp3", "title": "X",
            "description": "", "type": "Breathing", "category": "Stress", "displayOrder": 0,
            "showOnHomeScreen": False, "durationMinutes": 1.0,
        })


def test_a_seed_deletes_every_bucket_file_the_manifest_does_not_name():
    bucket = {"bee-breathing.mp3", "anxiety-bee-breathing.mp3", "anxiety-calm-your-mind.mp3"}

    def storage(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, json=[{"name": name} for name in sorted(bucket)])
        bucket.difference_update(json.loads(request.content)["prefixes"])
        return httpx.Response(200, json=[])

    entry = ManifestEntry.model_validate({
        "id": "0c10b2a9-46e2-4626-8d2d-0b417adffeb4", "source": "ANXIETY/Bee Breathing.wav",
        "filename": "bee-breathing.mp3", "title": "Bee Breathing", "description": "", "type": "Breathing",
        "category": "Anxiety", "displayOrder": 0, "showOnHomeScreen": False, "durationMinutes": 3.95,
    })
    with httpx.Client(transport=httpx.MockTransport(storage), base_url="http://storage") as http:
        _remove_unlisted(http, [entry])

    assert bucket == {"bee-breathing.mp3"}
