# ABOUTME: Checks what a 👍/👎 body accepts: a known rating, and a reason cleaned as a message is.
# ABOUTME: A reason that is only spaces or invisible characters is no reason; one over 1000 characters is refused.

import pytest
from pydantic import ValidationError

from mani.models.api import FeedbackIn


def test_a_reason_is_cleaned_and_nothing_left_means_no_reason():
    assert FeedbackIn(rating="up", reason="  calming, \u200bthank you  ").reason == "calming, thank you"
    assert FeedbackIn(rating="down", reason=" \u200b \n ").reason is None
    assert FeedbackIn(rating="down").reason is None


def test_an_unknown_rating_or_an_overlong_reason_is_refused():
    with pytest.raises(ValidationError):
        FeedbackIn(rating="meh")
    with pytest.raises(ValidationError):
        FeedbackIn(rating="up", reason="x" * 1001)
