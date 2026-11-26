# ABOUTME: What Mani says and does when a reply reports a crisis signal.
# ABOUTME: The reply is real text; the resource list holds reference numbers until the client supplies hers.

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

# A plain, non-clinical acknowledgement that stays on screen while the resource panel opens, so at the most
# important moment in the product the person never sees nothing.
CRISIS_REPLY = (
    "I'm really glad you told me that, and I want to be honest with you: what you're "
    "carrying is heavier than I can hold on my own.\n\n"
    "You deserve to talk to a person who can stay with you properly. If you're in "
    "immediate danger, please contact your local emergency number now.\n\n"
    "I'm not going anywhere."
)
# Where to get help, said wherever a message goes out unread for safety: an outage, or a refusal for a limit.
IN_DANGER = "If you're in danger or thinking about hurting yourself, call 911 now, or call or text 988."
# Added after Mani's text when code raised a body worry to danger that the model judged lower: a possible medical
# emergency gets "call emergency services now" every time (muhammad, 2026-11-18). Wording is ours until the client
# supplies hers.
BODY_EMERGENCY = "If this is happening now, please call 911 or get to the nearest emergency room now."
# What goes out when no host answered and no safety worry was open, so a first message about danger during an outage
# still reaches the numbers (the design of 2026-11-17). Wording is ours until the client supplies hers.
TROUBLE_REPLY = f"I'm having trouble replying right now, so please try again in a moment. {IN_DANGER}"

# The fixed words that stand in for a reply the model never gave. A retry of a message answered with one runs the turn
# again, so a message nobody read gets read (turn._arrival).
UNREAD_REPLIES = (CRISIS_REPLY, TROUBLE_REPLY)

# What Mani asks after a framework's last stage when a turn of the conversation reached danger
# (record.DANGER_REACHED), as a reply of its own before the closing choices (muhammad, 2026-11-11). Wording is ours
# until the client supplies hers.
END_CHECK = (
    "Thank you for going through that with me. Before we finish, I want to come back to the worry about safety that "
    "came up earlier. How are things with that right now?"
)
# What Mani says on the first turn back after a pause, whatever the model wrote: safety comes before anything else, so it
# can never agree to carry on first (muhammad, 2026-11-19, the client's blocker test: "Yes, we can keep talking"). The
# model's own read of their message still counts. Wording is ours until the client supplies hers.
RETURN_CHECK_REPLY = (
    "Before anything else, I want to ask about what was happening when I paused our chat. How are things with that "
    f"right now? {IN_DANGER}"
)
# What Mani says on the first turn back when that message itself is read as danger: the way to help, with no question
# about the pause and no agreement to carry on (muhammad, 2026-11-20: "I just took the pills" got the question above and
# lost Mani's own reply). Wording is ours until the client supplies hers.
RETURN_DANGER_REPLY = (
    "I'm worried about what you just told me. Please call 911 now, or call or text 988. Is anyone with you right now?"
)
# The reply on the turn that pauses the chat, by whose danger it is (the reply's safety.about): whom Mani worries for, and the
# help that fits. A body emergency gets no suicide line; a danger of unknown kind keeps it. Wording is ours (muhammad,
# 2026-11-13); every number is one of RESOURCES.
_PAUSE_FOR: dict[str | None, tuple[str, str]] = {
    "themselves": (
        "your safety", "If anyone might get hurt, call 911 now, or call or text 988 to talk with someone right away.",
    ),
    "someone_else": ("everyone's safety", "If anyone might get hurt, call 911 now."),
    "from_someone": ("your safety", "If anyone might get hurt, call 911 now."),
    "body": ("your health", "If this might be an emergency, call 911 now."),
}


def _length(seconds: int) -> str:
    """A pause's length in the largest whole unit that holds it: "30 seconds", "15 minutes", "1 hour"."""
    unit_seconds, unit = next(((n, name) for n, name in ((3600, "hour"), (60, "minute")) if seconds % n == 0),
                              (1, "second"))
    count = seconds // unit_seconds
    return f"{count} {unit}" if count == 1 else f"{count} {unit}s"


def pause_reply(about: str | None, seconds: int) -> str:
    """What Mani says on the turn that pauses the chat."""
    who, help_now = _PAUSE_FOR.get(about, _PAUSE_FOR["themselves"])
    return (
        f"I'm worried about {who}, so I'm pausing our chat for {_length(seconds)}. {help_now} "
        "I'll be here when you come back."
    )


class Resource(BaseModel):
    """One crisis service a person can actually reach."""

    country: str
    # emergency: for immediate danger; support: a line to talk or text with someone; directory: finds a helpline in
    # any country. A client draws each kind its own way.
    kind: Literal["emergency", "support", "directory"] = "support"
    name: str
    description: str = ""
    phone: str | None = None
    sms: str | None = None
    url: str | None = None
    hours: str | None = None


# Reference numbers for the US, and a directory of helplines for every other country, standing in until the client
# supplies her own list. A wrong number in a crisis panel is worse than none, so each is a long-standing public service.
RESOURCES: list[Resource] = [
    Resource(
        country="US", kind="emergency", name="Emergency services",
        description="For immediate danger to you or someone else.", phone="911",
    ),
    Resource(
        country="US", name="988 Suicide & Crisis Lifeline", description="Call, text or chat with a trained counselor.",
        phone="988", sms="988", url="https://988lifeline.org", hours="24/7",
    ),
    Resource(
        country="US", name="Crisis Text Line", description="Text HOME to reach a trained crisis counselor.",
        sms="741741", hours="24/7",
    ),
    Resource(
        country="US", kind="directory", name="Find a helpline in your country", url="https://findahelpline.com",
        description="Free, confidential helplines in more than 175 countries.",
    ),
]


def resources_for(country: str | None = None) -> list[Resource]:
    """Every resource, or one country's; the helpline directory is listed whatever the country."""
    if country is None:
        return list(RESOURCES)
    return [r for r in RESOURCES if r.kind == "directory" or r.country.lower() == country.lower()]
