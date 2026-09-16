# ABOUTME: What Mani says and does when a reply reports a crisis signal.
# ABOUTME: The reply is real text; the resource list is empty until real services exist.

from __future__ import annotations

from pydantic import BaseModel

# The previous implementation returned an empty string here, so at the single most
# important moment in the product the person saw nothing at all. This is a plain,
# non-clinical acknowledgement that stays on screen while the resource panel opens.
CRISIS_REPLY = (
    "I'm really glad you told me that, and I want to be honest with you: what you're "
    "carrying is heavier than I can hold on my own.\n\n"
    "You deserve to talk to a person who can stay with you properly. If you're in "
    "immediate danger, please contact your local emergency number now.\n\n"
    "I'm not going anywhere."
)


class Resource(BaseModel):
    """One crisis service a person can actually reach."""

    country: str
    name: str
    description: str = ""
    phone: str | None = None
    sms: str | None = None
    url: str | None = None
    hours: str | None = None


# Deliberately empty. A wrong number in a crisis panel is worse than no number, and the
# countries and services this ships with are muhammad's to supply. The endpoint, the
# shape and the client contract exist so adding them is a content change.
RESOURCES: list[Resource] = []


def resources_for(country: str | None = None) -> list[Resource]:
    if country is None:
        return list(RESOURCES)
    return [r for r in RESOURCES if r.country.lower() == country.lower()]
