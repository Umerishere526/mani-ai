# ABOUTME: Checks the bounds on profile fields that are pasted into the system prompt.
# ABOUTME: Every turn carries them, so an unbounded field is a prompt-injection channel.

import pytest
from pydantic import ValidationError

from mani.models.api import ProfileIn


def test_a_normal_set_of_topics_is_accepted():
    assert ProfileIn(topics=["work stress", "sleep"]).topics == ["work stress", "sleep"]


@pytest.mark.parametrize(
    "topics",
    [
        [f"topic {i}" for i in range(11)],   # too many
        ["x" * 61],                           # one too long to be a topic
        [""],                                 # empty
    ],
)
def test_topics_that_could_carry_instructions_are_refused(topics):
    with pytest.raises(ValidationError):
        ProfileIn(topics=topics)
