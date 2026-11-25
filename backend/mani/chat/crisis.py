# ABOUTME: What Mani says and does when a reply reports a crisis signal.
# ABOUTME: The reply is real text; the resource list holds reference numbers until the client supplies hers.

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from mani.errors import ServiceError

# Every text that says where to get help gives the US numbers and this, with no country detection (S11).
# PROVISIONAL: clinician sign-off required before deploy.
DIRECTORY = "findahelpline.com"
OUTSIDE_US = f"Outside the US: {DIRECTORY}."
# Where to get help, said wherever a message goes out unread for safety: an outage, a refusal for a limit or a pause,
# and any error while a worry is held (S9). PROVISIONAL: clinician sign-off required before deploy.
IN_DANGER = f"If you're in danger or thinking about hurting yourself, call 911 now, or call or text 988. {OUTSIDE_US}"
# A plain, non-clinical acknowledgement that stays on screen while the resource panel opens, so at the most
# important moment in the product the person never sees nothing.
CRISIS_REPLY = (
    "I'm really glad you told me that, and I want to be honest with you: this is more than "
    "I can help with on my own.\n\n"
    f"You deserve to talk to a person who can stay with you properly. {IN_DANGER}"
)
# Where to get help for whose danger it is (the reply's safety.about); a danger of unknown kind keeps the suicide line.
# The body's line says only to call if it is happening now, never what the symptom might be (S13, Safety Guardrails
# section 2); danger from someone adds the National Domestic Violence Hotline (S14, R152). 911 leads every line. Every
# number is one of RESOURCES. PROVISIONAL: clinician sign-off required before deploy.
_HELP: dict[str, str] = {
    "themselves": (
        f"If anyone might get hurt, call 911 now, or call or text 988 to talk with someone right away. {OUTSIDE_US}"
    ),
    "someone_else": f"If anyone might get hurt, call 911 now. {OUTSIDE_US}",
    "from_someone": (
        "If you're in danger, call 911 now. The National Domestic Violence Hotline is 1-800-799-7233 "
        f"(or text START to 88788). {OUTSIDE_US}"
    ),
    "body": f"If this is happening now, call 911. {OUTSIDE_US}",
}


def resources_line(about: str | None) -> str:
    """Where to get help for whose danger it is."""
    return _HELP.get(about or "themselves", _HELP["themselves"])


# What a reply must name for each kind of danger, or code adds the kind's line after it (S2): the kind's numbers, and
# the directory for everyone outside the US (S11). PROVISIONAL: clinician sign-off required before deploy.
_NEEDED = {"themselves": ("911", "988", DIRECTORY), "someone_else": ("911", DIRECTORY),
           "from_someone": ("911", "799-7233", DIRECTORY), "body": ("911", DIRECTORY)}


def names_help(text: str, about: str | None) -> bool:
    """Whether the reply already names everything its kind of danger needs."""
    return help_missing(text, about) is None


def help_missing(text: str, about: str | None) -> str | None:
    """What code adds after a reply so it names everything its kind of danger needs: nothing when it does, only the
    outside-US line when that alone is missing (so a reply that already named the numbers does not say them twice), and
    the kind's whole line otherwise."""
    missing = [needed for needed in _NEEDED.get(about or "themselves", _NEEDED["themselves"]) if needed not in text.lower()]
    if not missing:
        return None
    return OUTSIDE_US if missing == [DIRECTORY] else resources_line(about)
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
# The question of immediate danger to themselves (CR-1), asked by code on the first turn back, when the danger the
# pause rested on is still open (CR-5). Wording is ours until the client supplies hers. PROVISIONAL: clinician sign-off
# required before deploy.
IMMEDIACY_QUESTION = (
    "Are you alone right now, do you have a plan or something you could hurt yourself with, and do you feel you might "
    "act on it tonight?"
)
_RETURN_CHECK_THEMSELVES = (
    f"Before anything else, I want to ask about what was happening when I paused our chat. {IMMEDIACY_QUESTION} "
    f"{IN_DANGER}"
)


def return_check_reply(about: str | None) -> str:
    """Code's question on the first turn back, by whose danger the pause was for: for themselves (or a kind unknown),
    the question of immediate danger; otherwise how things are with it. Both say where to get help."""
    return _RETURN_CHECK_THEMSELVES if about in (None, "themselves") else RETURN_CHECK_REPLY


# What Mani says on the first turn back when that message itself is read as danger: the way to help, with no question
# about the pause and no agreement to carry on (muhammad, 2026-11-20: "I just took the pills" got the question above and
# lost Mani's own reply). Wording is ours until the client supplies hers.
RETURN_DANGER_REPLY = (
    f"I'm worried about what you just told me. Please call 911 now, or call or text 988. {OUTSIDE_US} "
    "Is anyone with you right now?"
)
# The one question after their answer to return_check_reply says they are all right: "I'm fine" is taken at its word,
# with one gentle follow-up about who they can reach, never a second pause (S12, R151). Wording is ours until the
# client supplies hers. PROVISIONAL: clinician sign-off required before deploy.
AFTER_PAUSE_FOLLOW_UP = "If things get hard again, who is someone you could reach out to?"
# Whom Mani worries for on the turn that pauses the chat, by whose danger it is (muhammad, 2026-11-13).
_WORRIED_FOR = {"themselves": "your safety", "someone_else": "everyone's safety", "from_someone": "your safety",
                "body": "your health"}


def _length(seconds: int) -> str:
    """A pause's length in the largest whole unit that holds it: "30 seconds", "15 minutes", "1 hour"."""
    unit_seconds, unit = next(((n, name) for n, name in ((3600, "hour"), (60, "minute")) if seconds % n == 0),
                              (1, "second"))
    count = seconds // unit_seconds
    return f"{count} {unit}" if count == 1 else f"{count} {unit}s"


def pause_reply(about: str | None, seconds: int) -> str:
    """What Mani says on the turn that pauses the chat: where to get help first, 911 leading, then the pause and its
    length said once (S6: a safety screen, not a countdown). PROVISIONAL: clinician sign-off required before deploy."""
    who = _WORRIED_FOR.get(about or "themselves", _WORRIED_FOR["themselves"])
    return (
        f"{resources_line(about)}\n\nI'm worried about {who}, so I'm pausing our chat for {_length(seconds)}. "
        "We can talk again when you come back."
    )


def with_help(error: ServiceError) -> ServiceError:
    """The same refusal with where to get help after its words, for an error while a worry is held (S9, S10).
    PROVISIONAL: clinician sign-off required before deploy."""
    return ServiceError(str(error), error.category, retryable=error.retryable,
                        user_message=f"{error.user_message} {IN_DANGER}", details=error.details)


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
    # Danger from someone (S14, R152). PROVISIONAL: clinician sign-off required before deploy.
    Resource(
        country="US", name="National Domestic Violence Hotline",
        description="Call, or text START, to reach an advocate.", phone="1-800-799-7233", sms="88788",
        url="https://www.thehotline.org", hours="24/7",
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
