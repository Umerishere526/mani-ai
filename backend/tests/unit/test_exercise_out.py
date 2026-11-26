# ABOUTME: Checks the exercise a client receives: its length rounded to the nearest 30 seconds, never 0:00,
# ABOUTME: and an unrecorded item marked as such with no storage path on the wire.

import uuid

import pytest

from mani.models.rows import Exercise
from mani.routers.serializers import to_exercise


def _exercise(minutes: float | None, audio_path: str | None = "x.mp3") -> Exercise:
    return Exercise(id=uuid.uuid4(), title="Bee Breathing", category="Anxiety", audio_path=audio_path,
                    duration_minutes=minutes)


@pytest.mark.parametrize(("exact", "shown"), [
    (3.95, 4.0),    # 3:57 -> 4:00
    (4.58, 4.5),    # 4:35 -> 4:30
    (4.75, 5.0),    # 4:45, exactly between, goes up
    (19.15, 19.0),  # The Gardener's Shed, 19:09 -> 19:00
    (0.2, 0.5),     # a 12 s item is never 0:00
    (None, None),
])
def test_a_length_reaches_the_client_rounded_to_the_nearest_30_seconds(exact, shown):
    assert to_exercise(_exercise(exact), None, None).duration_minutes == shown


def test_an_unrecorded_item_reaches_the_client_as_not_recorded_with_no_storage_path():
    out = to_exercise(_exercise(None, audio_path=None), None, None)

    assert out.recorded is False and out.audio_url is None
    assert "audio_path" not in out.model_dump()
