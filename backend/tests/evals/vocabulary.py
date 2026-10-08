# ABOUTME: The feeling words, self judgments and button length the specifications set, as data for the evals.
# ABOUTME: Read by the checks that score a reply; nothing in mani/ imports it.

from __future__ import annotations

import re

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
