# ABOUTME: A labelled table of messages the safety screen must read correctly, both ways.
# ABOUTME: Each row is a real failure mode: a false lock, or a risk that passed unseen.

import pytest

from mani.chat.safety import Category, Level, screen

CRISIS, CONCERN, NONE = Level.CRISIS, Level.CONCERN, Level.NONE


@pytest.mark.parametrize(
    ("text", "level"),
    [
        # Denied, not stated. A lock here takes the conversation from someone saying they are safe.
        ("I would never kill myself", NONE),
        ("I'm not going to kill myself, I just need to vent", NONE),
        ("I don't want to die", NONE),
        ("I'm not suicidal, just tired", NONE),
        # A word inside a longer word is not the word.
        ("I want to diet before summer", NONE),
        # An accident, not self-harm.
        ("I cut myself shaving", NONE),
        # Self-harm said without intent or a plan asks; said with one, locks.
        ("I cut myself again last night", CONCERN),
        ("I'm going to cut myself", CRISIS),
        # Hyperbole: asks, does not lock.
        ("this exam makes me want to kill myself", CONCERN),
        ("I want to die of embarrassment lol", CONCERN),
        ("I showed up wanting to kill myself today", CONCERN),
        # Sustained, not exasperated: "been wanting to" is ideation over time, and locks.
        ("I've been wanting to kill myself for weeks", CRISIS),
        ("Kill me. Just fucking kill me.", CONCERN),
        # Explicit statement, plan, method or act: locks.
        ("I want to kill myself", CRISIS),
        ("I am suicidal", CRISIS),
        ("I'm going to hang myself", CRISIS),
        ("I took 30 tablets", CRISIS),
        ("I swallowed a bottle of paracetamol", CRISIS),
        ("I have the rope ready", CRISIS),
        ("I wrote my goodbye letters", CRISIS),
        ("I have a gun and I keep thinking about using it on myself", CRISIS),
        ("I am about to go confront him with a knife", CRISIS),
        # Spelled to slip past a filter: still read.
        ("I want to kms", CRISIS),
        ("I'm going to unalive myself", CRISIS),
        ("i want to k1ll myself", CRISIS),
        # Someone else's safety, harm wished on someone, or violence received: asks.
        ("my friend wants to kill himself", CONCERN),
        ("I want to kill my husband", CONCERN),
        ("he strangled me last night", CONCERN),
        # A "not" that denies something else, and idioms, read as they always should.
        ("I don't know, I want to die", CRISIS),
        ("I couldn't even kill myself properly", CRISIS),
        ("I will not be here tomorrow", CONCERN),
        ("I took my tablets this morning", NONE),
        ("my mum will kill me if I fail", NONE),
        ("I'm dying to see that film", NONE),
        ("This traffic is killing me", NONE),
    ],
)
def test_the_screen_reads_the_message_at_the_right_level(text, level):
    assert screen(text).level is level


@pytest.mark.parametrize(
    ("text", "category"),
    [
        ("I took 30 tablets", Category.OVERDOSE),
        ("I'm going to hang myself", Category.SUICIDE),
        ("I am about to go confront him with a knife", Category.HARM_TO_OTHER),
        ("I want to kill my husband", Category.HARM_TO_OTHER),
        ("he strangled me last night", Category.ABUSE_OR_VIOLENCE),
    ],
)
def test_the_category_names_what_was_said(text, category):
    assert screen(text).category is category
