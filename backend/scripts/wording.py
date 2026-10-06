# ABOUTME: The feeling words and button checks the evals and the style counts measure replies against.
# ABOUTME: Measurement only (spec 0010): no reply is changed or asked for again because of them.

from __future__ import annotations

import re
from difflib import SequenceMatcher

# The feeling words the specifications are strict about: a reply may use one only if the
# person used it first. "MANI never introduces a feeling word the user did not use."
FEELING_WORDS = frozenset(
    {
        "abandoned", "afraid", "angry", "anxious", "ashamed", "betrayed", "broken",
        "crushed", "defeated", "dejected", "depressed", "desperate", "devastated",
        "disappointed", "distressed", "embarrassed", "exhausted", "fearful", "frustrated",
        "furious", "guilty", "helpless", "hopeless", "humiliated", "hurt", "insecure",
        "isolated", "lonely", "lost", "miserable", "overwhelmed", "panicked", "rejected",
        "resentful", "sad", "scared", "stressed", "terrified", "trapped", "unloved",
        "unwanted", "upset", "worried", "worthless",
        "empty", "heartbroken", "heavy", "numb", "painful", "scary",
        # The adjectival forms, which describe the situation rather than the person and are
        # the shape a capsule label usually takes: "It's frustrating", "It's exhausting".
        "depressing", "devastating", "draining", "embarrassing", "exhausting",
        "frustrating", "humiliating", "isolating", "overwhelming", "terrifying",
        "upsetting", "worrying",
        # Forms and neighbours that slipped through when the list was a fixed few dozen:
        # "That sounds incredibly stressful" named a feeling the person never did.
        "anxiety", "nervous", "nervousness", "tense", "tension", "worry", "worries",
        "stress", "stressful", "stressing", "dread", "dreading", "dreaded", "fear", "fears",
        "frightened", "frightening", "panic", "panicking", "overwhelm", "sadness", "unhappy",
        "anger", "annoyed", "annoying", "irritated", "irritating", "bitter", "jealous",
        "envious", "guilt", "shame", "shameful", "embarrassment", "humiliation", "loneliness",
        "isolation", "hopelessness", "despair", "despairing", "depression", "misery",
        "devastation", "grief", "grieving", "sorrow", "discouraged", "disheartened",
        "drained", "burnout", "burnt", "hollow", "confused", "confusing", "distress",
        "relieved", "relief", "calm", "happy", "happiness", "joy", "joyful", "excited",
        "proud", "grateful", "ecstatic", "thrilled", "terrible", "awful", "dreadful",
    }
)

# Judgments a person may hold about themselves but must never be handed as a button to press.
# Observed live: a reply offered "I'm overthinking it" as a capsule.
SELF_JUDGMENTS = (
    "overthinking", "over thinking", "being dramatic", "too sensitive", "overreacting",
    "over reacting", "being silly", "being stupid", "my fault", "i'm weak", "i am weak",
    "i'm broken", "i am broken", "not enough", "being needy", "being difficult",
)

# Five: room for a choice in the person's own voice. Past that a label is becoming a sentence.
MAX_CAPSULE_WORDS = 5


WORD = re.compile(r"[a-z']+")


def words(text: str) -> set[str]:
    return set(WORD.findall(text.lower()))


_SUFFIXES = ("iness", "ness", "ment", "ied", "ful", "ing", "ed", "ion", "ly", "y")


def _stem(word: str) -> str:
    """A rough root, so a feeling word and its plain forms count as one: lonely and loneliness,
    stressed and stress, overwhelmed and overwhelming. Never merges two different feelings."""
    for _ in range(2):
        for suffix in _SUFFIXES:
            if word.endswith(suffix) and len(word) - len(suffix) >= 3:
                word = word[: -len(suffix)] + ("y" if suffix in ("iness", "ied") else "")
                break
    return word


def introduced_feelings(text: str, said: str) -> list[str]:
    """Feeling words in `text` that the person has not used. "MANI never introduces a feeling
    word the user did not use": their own word, or a plain form of it, may come back; a
    different feeling may not."""
    theirs = {_stem(w) for w in words(said)}
    return sorted(
        w for w in words(text) & FEELING_WORDS
        if _stem(w) not in theirs and not _misspelt_by_them(w, theirs)
    )


def _skeleton(stem: str) -> str:
    """The consonants of a root with repeats collapsed: "emberess" and "embarrass" are both "mbrs"."""
    return re.sub(r"(.)\1+", r"\1", re.sub(r"[aeiou]", "", stem))


def _misspelt_by_them(word: str, theirs: set[str]) -> bool:
    """Whether they wrote this feeling word badly ("emberessed" for "embarrassed"): a reply that
    spells it right has not introduced it. Long words only, and close, so one feeling is never
    taken for another (sad and mad, lonely and lovely stay different; across the word list only
    burnout and burnt share a skeleton, and they are one feeling)."""
    stem = _stem(word)
    if len(stem) < 5:
        return False
    skeleton = _skeleton(stem)
    return any(
        len(other) >= 5
        and (
            SequenceMatcher(None, stem, other).ratio() >= 0.8
            or (len(skeleton) >= 4 and other[0] == stem[0] and _skeleton(other) == skeleton)
        )
        for other in theirs
    )
