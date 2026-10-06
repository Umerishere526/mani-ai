# ABOUTME: Counts what the client's style check measures in the replies of one conversation.
# ABOUTME: Pure functions over saved turns, so the numbers can be tested without a model.

from __future__ import annotations

import random
import re
import statistics
from dataclasses import dataclass, field

from mani.chat import context, repairs
from scripts.seed import FRAMEWORKS_DIR, parse_framework
from tests.evals import validators

SOUNDS_LIKE = re.compile(r"\b(?:it |that )?sounds (?:like|as if|as though)\b")
SEEMS_LIKE = re.compile(r"\b(?:it |that )?seems (?:like|as if|as though)\b")

# The phrases the client's document names as the ones Mani must not lean on, and the two that
# read as a machine once a person had read the transcripts, matched on text where "I am" has
# been written "I'm", apostrophes are straight and capitals are lower case.
STOCK_PHRASES = (
    re.compile(r"\bi hear you\b"),
    re.compile(r"\bi'm (?:right )?here (?:for|with) you\b"),
    re.compile(r"\bthat makes sense\b"),
    SOUNDS_LIKE,
    SEEMS_LIKE,
)

# An em dash, an en dash, or a hyphen with a space on both sides. A hyphen inside a word
# ("check-in") is not punctuation and is left alone, and neither is a list marker.
_DASH = re.compile(r"[—–]|(?<=\s)-(?=\s)")
_LIST_MARKER = re.compile(r"(?m)^[ \t]*[-*][ \t]+")

_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+")
_PARAGRAPH_BREAK = re.compile(r"\n\s*\n")

# A reply this many sentences long or longer is more than the instructions ask for.
LONG_REPLY_SENTENCES = 4
# A message of this many raw words or fewer answers the question Mani just asked.
SHORT_MESSAGE_WORDS = 3
# The conversation the styles are read on, and how many replies from its start (AC-9).
STYLE_READ_CONVERSATION = "panic"
STYLE_READ_POINTS = 2
# Reported on its own line: the client's own lines use it, so whether it may stay is open.
SIZE_PHRASE_REPORTED_ALONE = "a lot"


@dataclass(frozen=True)
class Turn:
    """One exchange of a saved conversation."""

    message: str
    reply: str
    offered: bool = False
    tapped: bool = False
    # The person's line came from the client's own document, written to answer the client's Mani.
    scripted: bool = False


def framework_descriptions() -> frozenset[str]:
    """The description each framework's offer carries, as the code composes it into the reply."""
    return frozenset(
        " ".join(parse_framework(path)["summary"].split())
        for path in sorted(FRAMEWORKS_DIR.glob("*.md"))
    )


def own_words(reply: str, descriptions: frozenset[str]) -> str:
    """Mani's part of a reply. An offer is composed by the code as Mani's part, the framework's
    description and the permission question, one paragraph each; the last two are not Mani's.
    Stripped wherever they appear, since an offer whose buttons were dropped keeps its text."""
    permission = set(repairs.PERMISSION_QUESTIONS.values())
    paragraphs = [p.strip() for p in _PARAGRAPH_BREAK.split(reply.strip())]
    return "\n\n".join(
        p for p in paragraphs if " ".join(p.split()) not in descriptions and p not in permission
    )


@dataclass(frozen=True)
class ReplyCounts:
    questions: int
    phrases: dict[str, int]
    dashes: int

    @property
    def stock_phrases(self) -> int:
        return sum(self.phrases.values())


@dataclass(frozen=True)
class ConversationCounts:
    replies: list[ReplyCounts]
    repeated_openers: int
    # The message (counting from 1) whose reply first offered a framework; None if none did.
    offer_at: int | None
    # Mani's own words: replies from the person's acceptance on are left out, and the
    # description and permission question the code adds to an offer are stripped.
    own_replies: int
    own_questions: int
    double_question_replies: int
    long_replies: int
    # Per stock phrase, how often Mani's own words said it before the offer was accepted.
    own_phrases: dict[str, int] = field(default_factory=dict)
    unused_feelings: list[str] = field(default_factory=list)
    unused_sizes: list[str] = field(default_factory=list)
    # Questions a person would have to stop and work out (spec 0008), over every reply in Mani's
    # own words, the offer's description and permission question left out.
    long_questions: int = 0
    lead_clauses: int = 0
    flagged_words: int = 0
    either_ors: int = 0

    @property
    def questions(self) -> int:
        return sum(r.questions for r in self.replies)

    @property
    def replies_with_a_question(self) -> int:
        return sum(1 for r in self.replies if r.questions)

    @property
    def stock_phrases(self) -> int:
        return sum(self.own_phrases.values())

    @property
    def all_stock_phrases(self) -> int:
        """Every stock phrase in every reply, the text the code adds to an offer included."""
        return sum(r.stock_phrases for r in self.replies)

    @property
    def phrases_said_twice(self) -> int:
        """Stock phrases Mani's own words said more than once in this conversation."""
        return sum(1 for count in self.own_phrases.values() if count > 1)

    @property
    def dashes(self) -> int:
        return sum(r.dashes for r in self.replies)


def count_dashes(text: str) -> int:
    return len(_DASH.findall(_LIST_MARKER.sub("", text)))


def count_phrases(text: str) -> dict[str, int]:
    """How often each stock phrase appears in the text; a phrase that is absent has no entry."""
    plain = re.sub(r"\bi am\b", "i'm", text.lower().replace("’", "'"))
    return {p.pattern: len(p.findall(plain)) for p in STOCK_PHRASES if p.search(plain)}


def count_reply(reply: str) -> ReplyCounts:
    return ReplyCounts(
        questions=reply.count("?"),
        phrases=count_phrases(reply),
        dashes=count_dashes(reply),
    )


def _sentences(text: str) -> int:
    return len([s for s in _SENTENCE_BREAK.split(text.strip()) if s])


def _accepted_at(turns: list[Turn]) -> int | None:
    """The index of the turn where the person tapped an offer's button."""
    return next(
        (i for i, t in enumerate(turns) if t.tapped and i > 0 and turns[i - 1].offered), None
    )


QUESTION_RULES = {
    "long question": "long_questions",
    "lead clause": "lead_clauses",
    "flagged word": "flagged_words",
    "either/or": "either_ors",
}


def count_question_findings(turns: list[Turn], descriptions: frozenset[str]) -> dict[str, int]:
    """How often each question rule is broken over the whole conversation, keyed by the
    `ConversationCounts` field it fills. Replies from the acceptance of an offer on are inside
    the framework."""
    accepted = _accepted_at(turns)
    totals = dict.fromkeys(QUESTION_RULES.values(), 0)
    for index, turn in enumerate(turns):
        in_framework = accepted is not None and index >= accepted
        for finding in validators.question_findings(
            own_words(turn.reply, descriptions), turn.message, in_framework=in_framework
        ):
            totals[QUESTION_RULES[finding.rule]] += 1
    return totals


def count_conversation(turns: list[Turn], descriptions: frozenset[str]) -> ConversationCounts:
    replies = [r.reply for r in turns]
    first_offer = next((i for i, t in enumerate(turns, 1) if t.offered), None)
    accepted = _accepted_at(turns)
    own_turns = turns if accepted is None else turns[:accepted]

    own_questions = double = long_replies = 0
    own_phrases: dict[str, int] = {}
    unused: list[str] = []
    unused_sizes: list[str] = []
    said: list[str] = []
    for turn in own_turns:
        said.append(turn.message)
        words = own_words(turn.reply, descriptions)
        own_questions += words.count("?")
        for phrase, count in count_phrases(words).items():
            own_phrases[phrase] = own_phrases.get(phrase, 0) + count
        if validators.question_count(words) > 1:
            double += 1
        if _sentences(words) >= LONG_REPLY_SENTENCES:
            long_replies += 1
        unused += repairs.introduced_feelings(words, " ".join(said))
        unused_sizes += repairs.introduced_size(words, " ".join(said))

    return ConversationCounts(
        replies=[count_reply(r) for r in replies],
        repeated_openers=len(validators.repeated_openers(replies)),
        offer_at=first_offer,
        own_replies=len(own_turns),
        own_questions=own_questions,
        double_question_replies=double,
        long_replies=long_replies,
        own_phrases=own_phrases,
        unused_feelings=unused,
        unused_sizes=unused_sizes,
        **count_question_findings(turns, descriptions),
    )


def style_read_replies(turns: list[Turn], descriptions: frozenset[str]) -> list[str]:
    """Mani's reply to each of the first two messages, in Mani's own words, each shown under
    the message it answered. These are the points the styles are read at (AC-9)."""
    nothing = "(nothing outside the offer text)"
    return [
        f"**Person:** {t.message}\n\n**Mani:** {own_words(t.reply, descriptions) or nothing}"
        for t in turns[:STYLE_READ_POINTS]
    ]


def own_words_before_acceptance(
    turns: list[Turn], descriptions: frozenset[str], tagged: bool = False,
) -> str:
    """A conversation as Mani's own words, from the start to the person's acceptance of an
    offer, each reply under the message it answered. What the meaning read looks at (AC-8).
    Tagged, an offer reply carries `[offer]` and the opening after a button tap `[after tap]`,
    the replies the restating read leaves out (AC-14)."""
    accepted = _accepted_at(turns)

    def tag(turn: Turn) -> str:
        if not tagged:
            return ""
        return "[offer] " if turn.offered else "[after tap] " if turn.tapped else ""

    return "\n\n".join(
        f"**Person:** {t.message}\n\n**Mani:** {tag(t)}{own_words(t.reply, descriptions)}"
        for t in (turns if accepted is None else turns[:accepted])
    )


RESTATING_DEFINITION = """# Restating read

Count two things in the untagged replies of each conversation below.

1. **Restating.** A reply restates when it holds a sentence that is not a question and only says the
   person's last message again in other words, adding nothing. "You find yourself unable to stop
   scrolling." after "I cannot stop scrolling" is a restatement. A plain question that uses their
   words is not, and neither is a short reply that adds something.
2. **A meaning stated as fact.** A reply states a meaning when it says something about what the
   person's words mean that they did not say, without asking. "Stuck in a loop" and "this thought
   is pulling at you" are examples.

Leave out the replies tagged `[offer]` (the sentence that introduces an offer) and `[after tap]` (the
opening after a button). Leave out the reply to a message that says they just need to get it out, the
opening after a correction, and the reflection after Chat More, since those are meant to mirror.

Write the number of restating replies and the number of eligible replies for each conversation, and
list every case. The source of each conversation is hidden until the key at the end.
"""


def turns_from_saved(turns: list[dict]) -> list[Turn]:
    """The turns of one conversation as `transcripts.json` saves them."""
    return [
        Turn(t["message"], t["reply"], offered=t["offered"], tapped=t["tapped"], scripted=t["scripted"])
        for t in turns
    ]


def restating_read(
    sources: dict[str, list[dict]], descriptions: frozenset[str], run: int = 1, seed: int = 0,
) -> str:
    """The file a person reads to count restating replies (AC-14) and meanings stated as fact
    (AC-8): one run of every conversation from each source, tagged, shuffled so the source is
    hidden, with the definition at the top and the key at the end. `sources` maps a label to the
    saved conversations of one check."""
    entries = [
        (
            f"{label} · {saved['conversation']} · {saved['style']}",
            own_words_before_acceptance(turns_from_saved(saved["turns"]), descriptions, tagged=True),
        )
        for label, conversations in sources.items()
        for saved in conversations
        if saved["run"] == run
    ]
    return f"{RESTATING_DEFINITION}\n{shuffled_for_reading(entries, seed)}"


def shuffled_for_reading(entries: list[tuple[str, str]], seed: int = 0) -> str:
    """The entries in a random order under numbers only, so the reader cannot tell where each
    came from, and what each number was listed only in a key at the end."""
    order = list(range(len(entries)))
    random.Random(seed).shuffle(order)
    body = [f"## {n}\n\n{entries[i][1]}\n" for n, i in enumerate(order, 1)]
    key = [f"- {n}: {entries[i][0]}" for n, i in enumerate(order, 1)]
    return "\n".join([*body, "## Key (do not read before marking)", "", *key, ""])


def short_message_turns(turns: list[Turn]) -> list[int]:
    """The turns where the person sent three raw words or fewer and did not tap a button, so
    Mani's reply to each can be read against the question it answered."""
    return [
        i for i, t in enumerate(turns)
        if not t.tapped and context.word_count(t.message) <= SHORT_MESSAGE_WORDS
    ]


def _per_run_mean(runs: dict[int, list[ConversationCounts]], value) -> float:
    return statistics.fmean(value(counts) for counts in runs.values())


def figures(records: list[tuple[str, int, ConversationCounts]]) -> dict[str, float]:
    """The numbers the specification's acceptance criteria are judged on, from every
    conversation of a check: `(style, run, counts)` for each one. Ratios are taken within a run
    and then averaged over the runs; the rest are totals over the whole check."""
    by_run: dict[int, list[ConversationCounts]] = {}
    for _, run, counts in records:
        by_run.setdefault(run, []).append(counts)

    def per_style(style: str, value) -> float:
        chosen = [c for s, _, c in records if s == style]
        return statistics.fmean(value(c) for c in chosen) if chosen else 0.0

    styles = sorted({s for s, _, _ in records})
    all_counts = [c for _, _, c in records]
    result: dict[str, float] = {
        "questions_per_reply_own": _per_run_mean(
            by_run, lambda cs: sum(c.own_questions for c in cs) / max(1, sum(c.own_replies for c in cs))
        ),
        "questions_per_reply_all": _per_run_mean(
            by_run, lambda cs: sum(c.questions for c in cs) / max(1, sum(len(c.replies) for c in cs))
        ),
        "replies_with_two_questions": sum(c.double_question_replies for c in all_counts),
        "phrases_said_twice": sum(c.phrases_said_twice for c in all_counts),
        "sounds_or_seems_like": sum(
            c.own_phrases.get(p.pattern, 0) for c in all_counts for p in (SOUNDS_LIKE, SEEMS_LIKE)
        ),
        "sounds_or_seems_like_all": sum(
            r.phrases.get(p.pattern, 0) for c in all_counts for r in c.replies for p in (SOUNDS_LIKE, SEEMS_LIKE)
        ),
        "unused_feelings": sum(len(c.unused_feelings) for c in all_counts),
        "unused_size_phrases": sum(
            1 for c in all_counts for p in c.unused_sizes if p != SIZE_PHRASE_REPORTED_ALONE
        ),
        "unused_a_lot": sum(c.unused_sizes.count(SIZE_PHRASE_REPORTED_ALONE) for c in all_counts),
        "long_replies": sum(c.long_replies for c in all_counts),
        "dashes": sum(c.dashes for c in all_counts),
        "conversations": len(all_counts),
        "offered": sum(1 for c in all_counts if c.offer_at is not None),
        "offered_at_2_to_4": sum(1 for c in all_counts if c.offer_at is not None and 2 <= c.offer_at <= 4),
        **{name: sum(getattr(c, name) for c in all_counts) for name in QUESTION_RULES.values()},
    }
    for style in styles:
        result[f"stock_phrases_per_conversation_{style}"] = per_style(style, lambda c: c.stock_phrases)
        result[f"stock_phrases_all_per_conversation_{style}"] = per_style(style, lambda c: c.all_stock_phrases)
        result[f"repeated_openers_per_conversation_{style}"] = per_style(style, lambda c: c.repeated_openers)
    return result
