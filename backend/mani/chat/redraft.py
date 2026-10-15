# ABOUTME: Why a drafted reply is asked for again once: an offer not allowed, an offer ruled out, no question, a question asked again.
# ABOUTME: Pure checks on the draft, so each reason is a unit test; the orchestrator makes the one extra call.

from __future__ import annotations

import re
from dataclasses import dataclass

from mani.chat import eligibility
from mani.chat.context import MAX_STAGE_ASKS
from mani.chat.techniques import Registry
from mani.llm.schema import NO_QUESTION_SHAPES, THEIR_SLOTS, Reply, WorkingRead
from mani.models.rows import ENDING_STAGES, Framework


def offered(reply: Reply, registry: Registry) -> str | None:
    """The framework a draft offers, if it carries an offer button for one that exists. An id the
    registry does not know is repairs.apply's to remove, not worth another call."""
    return next(
        (p.technique for p in reply.prompts or [] if p.technique and registry.get(p.technique)),
        None,
    )


def ruled_out(reply: Reply, user_texts: list[str], registry: Registry) -> str | None:
    """The framework a draft offers when what the person has said rules it out: the phrases a
    framework file lists under `never_offer_when_said` (early grief for Behavioral Activation).
    A prompt rule alone did not hold, so this is checked in code."""
    technique = offered(reply, registry)
    activation = registry.activations.get(technique) if technique else None
    if activation and eligibility.vetoes(activation, user_texts):
        return technique
    return None


_QUESTION = re.compile(r"[^.!?\n]*\?")
REPEAT_OVERLAP = 0.7

# How long the model calls of one turn may take together, and the least a redraft needs to be worth
# starting. Measured on 2026-10-14: a healthy call is 5-10 s, while a degraded upstream ran 20-60 s
# per call and a turn with two redrafts outlasted the client waiting on it.
REDRAFT_BUDGET_MS = 25_000
REDRAFT_MIN_MS = 5_000


def redraft_seconds(spent_ms: int) -> float | None:
    """How long a redraft may run, given what the turn's calls have taken: what is left of the
    budget, or None when that is less than a healthy call needs and the draft in hand stands."""
    left = REDRAFT_BUDGET_MS - spent_ms
    return left / 1000 if left >= REDRAFT_MIN_MS else None


def _last_question_words(text: str) -> set[str]:
    questions = _QUESTION.findall(text)
    return set(re.findall(r"[a-z']{4,}", questions[-1].lower())) if questions else set()


def repeats(reply: Reply, last_mani_text: str | None) -> bool:
    """Whether the draft's closing question is, by its words, the question Mani asked last turn.
    A person who answers a question and gets it back unchanged is stuck, however it is reworded."""
    now, before = _last_question_words(reply.text), _last_question_words(last_mani_text or "")
    return bool(now and before and len(now & before) / min(len(now), len(before)) >= REPEAT_OVERLAP)


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WORD = re.compile(r"\w+")
# How many words of its own a reply has to say, across the sentences that are not questions,
# before it can be an understanding rather than a line leading into a question. Measured over
# the live runs of 2026-10-13: a lead-in such as "It's hard to pin down when it feels like
# everything." runs to 11 words, while of the 38 replies that put an understanding to the
# person and asked whether it was right, the shortest ran to 20 and the median to 35. Nothing
# real was anywhere near the line, which is where it should sit: this rules out the replies
# that said nothing, and is not a judgement of how good what was said is.
UNDERSTANDING_WORDS = 14
# Above this share of its words taken from what they have said, a reply is their own message
# handed back rather than what Mani makes of it.
THEIR_WORDS = 0.5


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z']{4,}", text.lower()))


# A question this close to one Mani already asked, or to what the read already holds, is asking for
# something it has. The words are compared as repeats() compares them, less the question's frame
# against an earlier one, so it cannot tell two questions that mean the same in different words; it
# catches the ones that come back in the same.
EARLIER_OVERLAP = 0.6
# The words any question is put in. Against an earlier question they are left out: "What did your
# manager do?" shares two of its three words with "What are you afraid your colleagues think?".
_QUESTION_FRAME = frozenset({
    "what", "what's", "whats", "which", "when", "where", "does", "would", "could", "have", "been",
    "being", "your", "about", "that", "this", "with", "them", "they", "their", "there", "from",
    "into", "most", "more", "some", "like", "just",
})
# Against the read, only a question made wholly of its words: one word of the question's own, such
# as whether something is still so, asks for what they have not said.
KNOWN_OVERLAP = 1.0
# How many of Mani's earlier questions the draft is held against: the same window [ctx] shows it.
EARLIER_QUESTIONS = 4


def _is_choice(text: str | None) -> bool:
    """Whether a reply ends by putting a choice, by having an or in its last two sentences. The
    choice is often in the sentence before the closing question ("I wonder if it is this, or
    that. Which is closer?"), so the last two are read, not only the question. Structural: it
    cannot tell a real choice from a sentence that happens to say or, only that the shape is one."""
    sentences = [s for s in _SENTENCE_SPLIT.split((text or "").strip()) if s]
    return any(re.search(r"\bor\b", s, re.IGNORECASE) for s in sentences[-2:])


# No measured corpus behind this list (unlike REPEAT_OVERLAP/UNDERSTANDING_WORDS above) — these are
# the phrasings named in the bug report and muhammad's own transcript, kept short and literal on
# purpose: a false positive (reading a real stage answer as confusion) is worse than a missed one,
# so nothing here is loose enough to catch a merely short or uncertain answer.
_CONFUSED = re.compile(
    r"\bdoesn'?t make sense\b"
    r"|\b(?:don'?t|didn'?t) understand\b"
    r"|\bconfus(?:ing|ed)\b"
    r"|\bwhat do you mean\b"
    r"|^\s*what\?+\s*$",
    re.IGNORECASE,
)


def is_confused(content: str) -> bool:
    """Whether the user's current message is a correction/confusion signal rather than an answer.

    Deterministic and content-only, like _is_choice: a short list of literal phrasings, not a
    model call. When a stage question gets this back, the model has sometimes marked the stage
    answered anyway because its own step and stages_known ledger agree with each other - wrongly,
    since neither looks at what the person actually said."""
    return bool(_CONFUSED.search(content or ""))


# Broader and fuzzier than _CONFUSED on purpose: a question is open-ended, not five fixed
# phrasings, so this also catches a trailing clarifying fragment in a message that is mostly a
# stage answer ("...but what do you mean by evidence?"). It will have more false positives than
# is_confused - the asymmetry runs the other way here: a missed question lets the model silently
# advance past a stage it never answered (the bug this closes), while a false positive only costs
# one extra "make sure you answered that" note to the model, so leaning broad is the right side
# to err on.
_QUESTION_SHAPE = re.compile(
    r"\?"
    r"|^\s*(?:what|why|how|who|when|where|which|does that mean|do you mean|can you|could you)\b",
    re.IGNORECASE,
)


def is_question(content: str) -> bool:
    """Whether the user's current message asks something, rather than only answering.

    Deterministic and content-only, like is_confused: ends in a question mark, or opens with a
    question word or phrase. Meant to catch a genuine question is present, not to classify the
    whole message - a mostly-answer message with a question tacked on still counts."""
    return bool(_QUESTION_SHAPE.search(content or ""))


_REPEATED_TERMINAL_PUNCTUATION = re.compile(r"[?!]{2,}")


def question_count(content: str) -> int:
    """How many question-sentences the user's current message contains.

    The same _QUESTION pattern that counts question-sentences in Mani's own reply (to enforce
    one question per reply), applied here to the user's message instead. Mechanical sentence
    splitting, not a judgment of whether each is answerable or means something different.
    Runs of repeated terminal punctuation ("??", "?!") are collapsed to a single "?" first, so a
    doubled mark does not split off a phantom extra, empty question."""
    collapsed = _REPEATED_TERMINAL_PUNCTUATION.sub("?", content or "")
    return len(_QUESTION.findall(collapsed))


def asks_what_is_known(
    reply: Reply, previous: WorkingRead | None, mani_texts: list[str]
) -> str | None:
    """What the draft's closing question asks for that Mani already has, or None.

    Returns "an earlier question" when it is, by its words, one Mani asked in its last few replies,
    and the name of the slot when it is mostly made of the words of something the read holds. The
    read is what they told Mani, so asking for it again is asking them to say it twice."""
    now = _last_question_words(reply.text)
    if len(now) < 3:
        return None
    asking = now - _QUESTION_FRAME
    for text in mani_texts[-EARLIER_QUESTIONS:]:
        before = _last_question_words(text) - _QUESTION_FRAME
        if asking and before and len(asking & before) / min(len(asking), len(before)) >= EARLIER_OVERLAP:
            return "an earlier question"
    if previous is not None:
        asked = _stems(now)
        for slot in THEIR_SLOTS:
            held = _stems(_words(getattr(previous, slot) or ""))
            if len(held) >= 3 and len(asked & held) / len(asked) >= KNOWN_OVERLAP:
                return slot
    return None


def _stems(words: set[str]) -> set[str]:
    """Words with a final s dropped, so "take" in a question matches "takes" in what they said."""
    return {w.removesuffix("s") for w in words}


def stage_already_in_the_read(
    reply: Reply, framework: Framework | None, previous: WorkingRead | None, stage: str | None
) -> str | None:
    """The read slot that already answers the stage the draft asks as if it were unknown, or None.

    A framework file names, per stage, the slots of the read that answer it (`read_slots`). When the
    draft marks that stage missing and one of those slots holds what they said, or partial and all
    of them do, Mani is about to ask for something it has: it should say what it understands and
    check it instead. A partial stage with a slot still empty asks for that gap. The check is on the
    slots and not on words, so it needs no phrase list."""
    if framework is None or not stage or not reply.stages_known:
        return None
    entry = next((e for e in reply.stages_known if e.stage == stage), None)
    if entry is None or entry.status not in ("missing", "partial"):
        return None
    slots = ((framework.stages or {}).get(stage) or {}).get("read_slots") or []
    held = [
        slot for slot in slots
        if (getattr(reply.working_read, slot, None) if reply.working_read else None)
        or getattr(previous, slot, None)
    ]
    if not held or (entry.status == "partial" and len(held) < len(slots)):
        return None
    return held[0]


def same_unknown(previous: WorkingRead | None, reply: Reply) -> bool:
    """Whether the draft's read is still trying to find out what the last reply's already was.

    Noted for whoever watches the read, not sent back: what they said in between often does not
    answer it ("idk", a correction, a request for help), and then wanting it still is right. Their
    words and Mani's are compared by overlap, as repeats() compares questions: structural, and it
    cannot say whether the two are the same in meaning, only that they are the same in words."""
    now = reply.working_read.unknown if reply.working_read else None
    before = previous.unknown if previous else None
    if not now or not before:
        return False
    a, b = _words(now), _words(before)
    return bool(a and b and len(a & b) / min(len(a), len(b)) >= REPEAT_OVERLAP)


def _names_a_framework(sentence: str, names: tuple[str, ...]) -> bool:
    """Whether a sentence names one of the sets of questions. Every offer does, because
    repairs._compose_offer adds the name when the model leaves it out."""
    letters = re.compile(r"[^a-z0-9]")
    flat = letters.sub("", sentence.lower())
    return any(letters.sub("", name.lower()) in flat for name in names)


def stated_understanding(
    mani_texts: list[str], user_texts: list[str], framework_names: tuple[str, ...] = ()
) -> bool:
    """Whether one of Mani's earlier replies could have said what it makes of their situation,
    with a message of theirs after it.

    Structural only, and it checks one thing: that a reply said enough of its own, outside its
    question, to be an understanding at all. It cannot read meaning, so it rules out the replies
    where nothing was said - a question with a few words in front of it, or their own sentence
    handed back - and never the one that said something shallow. `understanding_said` is the
    model's claim about meaning; this is the part of the claim that can be checked.
    """
    if not mani_texts or not user_texts:
        return False
    said = _words(" ".join(user_texts))
    for text in mani_texts:
        stated = " ".join(
            s
            for s in _SENTENCE_SPLIT.split(text.strip())
            # An offer's own words describe the set of questions, not the person's situation, and
            # they are long enough to pass every test below. Left in, the first offer Mani makes
            # satisfies this check for the rest of the conversation.
            if s and not s.rstrip().endswith("?") and not _names_a_framework(s, framework_names)
        )
        if len(_WORD.findall(stated)) < UNDERSTANDING_WORDS:
            continue
        words = _words(stated)
        if words and len(words & said) / len(words) < THEIR_WORDS:
            return True
    return False


def understanding_ok(
    reply: Reply,
    mani_texts: list[str],
    user_texts: list[str],
    framework_names: tuple[str, ...] = (),
) -> bool:
    """Whether an offer may stand: the draft says it has already put its understanding to them,
    and Mani's own earlier replies bear that out."""
    return reply.understanding_said == "earlier" and stated_understanding(
        mani_texts, user_texts, framework_names
    )


@dataclass(frozen=True)
class StageInForce:
    """Where the questions stand as this reply is written. `asked` is whether that stage's question
    was already put to them: a stage they have been asked may be left once answered, even the
    closing; one never asked is skipped only if it may be."""

    framework_id: str
    stage: str
    asked: bool
    # How many replies have asked `stage`. At MAX_STAGE_ASKS it may be left whatever its status.
    asks: int = 0


def ledger_stage(reply: Reply, framework: Framework, start: StageInForce) -> str | None:
    """The stage the draft's own stages_known says to ask: walking from the stage in force, the first
    it does not mark met, or the first that may not be skipped. None when it has no ledger, or when
    the walk reaches the body route, which code runs."""
    if not reply.stages_known or framework.phase_index(start.stage) < 0:
        return None
    met = {entry.stage for entry in reply.stages_known if entry.met}
    for phase in framework.phases[framework.phase_index(start.stage) :]:
        if phase in ENDING_STAGES:
            return None
        passable = framework.may_skip(phase) or (phase == start.stage and start.asked)
        exhausted = phase == start.stage and start.asks >= MAX_STAGE_ASKS and framework.may_skip(phase)
        if not exhausted and (phase not in met or not passable):
            return phase
    return None


# What the reply does with a stage, for the debug view. `known` means they confirmed it.
_ACTIONS = {
    "known": "confirmed by them, gone on from",
    "partial": "partly known, ask only the gap",
    "confirm": "confirm it with them",
    "missing": "missing, ask it",
    "done": "answered in an earlier reply",
    "not_reached": "not reached yet",
    "unreported": "asked this reply; the model sent no ledger",
}


def ledger_view(reply: Reply, framework: Framework | None, phase: str | None = None) -> list[dict]:
    """Every content stage of the framework as the draft's own ledger reads it, for a person
    watching the conversation: how much of it is known, and what the reply does about it. A stage
    before the ledger starts was answered earlier, and one after it has not been reached. A reply
    with no ledger still shows where the questions stand, from the recorded `phase`."""
    entries = {entry.stage: entry for entry in reply.stages_known or []}
    order = (
        [p for p in framework.phases if p != "offering" and p not in ENDING_STAGES]
        if framework else list(entries)
    )
    asking = reply.state.step if reply.state else None
    if not entries:
        if not framework or not phase or phase == "offering":
            return []
        current = order.index(phase) if phase in order else len(order)
        return [
            {
                "stage": stage,
                "title": ((framework.stages or {}).get(stage) or {}).get("title"),
                "status": "done" if i < current else ("unreported" if i == current else "not_reached"),
                "known": None,
                "action": _ACTIONS["done" if i < current else ("unreported" if i == current else "not_reached")],
                "asking": i == current,
            }
            for i, stage in enumerate(order)
        ]
    first = next((i for i, stage in enumerate(order) if stage in entries), 0)
    rows = []
    for index, stage in enumerate(order):
        entry = entries.get(stage)
        known = entry.known if entry else None
        if entry:
            status = entry.status
        else:
            status = "done" if index < first else "not_reached"
        rows.append({
            "stage": stage,
            "title": (((framework.stages or {}).get(stage) or {}).get("title") if framework else None),
            "status": status,
            "known": known,
            "action": _ACTIONS[status],
            "asking": stage == asking,
        })
    return rows


def reasons(
    reply: Reply,
    user_texts: list[str],
    registry: Registry,
    *,
    offer_not_allowed: bool,
    needs_question: bool = False,
    may_offer: bool = False,
    stage_in_force: StageInForce | None = None,
    last_mani_text: str | None = None,
    mani_texts: list[str] | None = None,
    framework_names: tuple[str, ...] = (),
    urgent: bool = False,
    previous_read: WorkingRead | None = None,
) -> list[str]:
    """What is wrong with the draft that only the model can fix, as lines for the model to read.
    Empty when the draft stands."""
    notes: list[str] = []

    framework = registry.get(stage_in_force.framework_id) if stage_in_force else None
    expected = ledger_stage(reply, framework, stage_in_force) if framework else None
    step = (
        reply.state.step
        if expected and reply.state and reply.state.technique == framework.id
        else None
    )
    if expected and step != expected:
        notes.append(
            f"your stages_known says {expected} is the first stage not yet answered, but "
            f"state.step is {step or 'missing'}; ask {expected}, only for what its known does not "
            "already hold, and report it in state.step"
        )
    if stage_in_force and user_texts and is_confused(user_texts[-1]):
        moved_on = reply.state and reply.state.technique == stage_in_force.framework_id and (
            reply.state.step != stage_in_force.stage
        )
        entry = next(
            (e for e in reply.stages_known or [] if e.stage == stage_in_force.stage), None
        )
        marked_met = bool(entry and (entry.met or entry.status == "known"))
        if moved_on or marked_met:
            notes.append(
                f"what they just said is confusion, not an answer; {stage_in_force.stage} is not "
                f"answered, so stay on it: keep state.step at {stage_in_force.stage} and do not "
                "mark it known or met in stages_known"
            )
    if (
        stage_in_force and user_texts and is_question(user_texts[-1])
        and reply.state and reply.state.technique == stage_in_force.framework_id
        and reply.state.step != stage_in_force.stage
        and reply.next_move != "answer_request"
    ):
        notes.append(
            f"what they just said is a question; you moved on from {stage_in_force.stage} without "
            "answering it - answer what they asked (set next_move to answer_request) and keep "
            f"state.step at {stage_in_force.stage} until it is"
        )
    if stage_in_force and user_texts and is_question(user_texts[-1]):
        asked = question_count(user_texts[-1])
        answered = reply.questions_answered
        if asked > 1 and answered is not None and answered < asked:
            notes.append(
                f"they asked {asked} questions in that message and you answered {answered}; "
                "answer each one in turn before returning to the stage's own question"
            )
    if (
        stage_in_force and framework and stage_in_force.asks >= MAX_STAGE_ASKS
        and framework.may_skip(stage_in_force.stage)
        and reply.state and reply.state.technique == framework.id
        and reply.state.step == stage_in_force.stage
    ):
        notes.append(
            f"you have asked {stage_in_force.stage} twice already; take what they gave you, even "
            "partial or I don't know, and ask the next stage now, in your own tone"
        )

    in_read = stage_already_in_the_read(
        reply, framework, previous_read, reply.state.step if reply.state else None
    ) if stage_in_force else None
    if in_read:
        notes.append(
            f"you are asking this stage as if you knew nothing, but the read already holds {in_read} "
            "for it; say what you understand as a possibility and check it with them instead of asking"
        )
    technique = offered(reply, registry)
    known = None if technique or stage_in_force else asks_what_is_known(reply, previous_read, mani_texts or [])
    if known:
        notes.append(
            f"your question asks for something you already have ({known}); they have told you it, "
            "so take it as given and ask about something you do not yet know"
        )
    elif not technique and repeats(reply, last_mani_text):
        notes.append(
            "your draft asks the question you asked last turn, with the same choices; answer "
            "what they just said first (a yes or a question of theirs counts), then move on: "
            "if they asked you to choose, offer one small step as a draft they can accept or change"
        )
    if not technique and not stage_in_force and _is_choice(reply.text) and _is_choice(last_mani_text):
        notes.append(
            "your last reply put them a choice and this one does too; a choice is for when the "
            "answer tells you something you need, not a habit. Ask an open question about the "
            "situation, the feeling, what it means to them or what they do about it instead"
        )
    chose_to_ask_nothing = bool(
        reply.style and reply.style.shape.strip().lower() in NO_QUESTION_SHAPES
        or reply.next_move == "acknowledge"
    )
    if chose_to_ask_nothing and last_mani_text is not None and "?" not in last_mani_text:
        # Two replies in a row that ask nothing leave the person with nothing to answer: the
        # second is asked again whatever it chose. Only when the person says they want to be
        # left to speak is that wrong, and then the previous reply is the one that carried it.
        chose_to_ask_nothing = False
    if needs_question and not technique and "?" not in reply.text and not chose_to_ask_nothing:
        notes.append(
            "your draft asks no question; end with one short, plain question about one part of what "
            "they just said, in their words"
        )
    # A draft is offering when it carries a button for a set, or says it means to. next_move is
    # only read where an offer could be made at all: inside a running framework, or on a safety
    # concern, the model has no offer to choose and a stray "offer" there must not send the
    # reply back for an understanding instead of the stage question.
    offering = bool(technique) or (may_offer and reply.next_move == "offer")
    if technique and offer_not_allowed:
        notes.append(
            "your draft offered a set of questions, which may not be offered in this reply; offer "
            "nothing and ask one short, plain question about what they just said, in their words"
        )
    elif technique and ruled_out(reply, user_texts, registry):
        # Before the checks below, because what they said rules this set out whatever else is
        # wrong with the draft: told only that it offered too early, the model offers it again.
        framework = registry.get(technique)
        name = framework.name if framework else technique
        notes.append(
            f"your draft offered {name}, which does not fit what they have told you (see "
            "'Never offer one when'); offer nothing and ask one question instead"
        )
    elif offering and reply.next_move == "answer_request":
        notes.append(
            "they asked you for something and your draft offers a set of questions instead; "
            "answer what they asked in this reply, from what they have told you, and leave the "
            "set for later"
        )
    elif offering and not urgent and not understanding_ok(
        reply, mani_texts or [], user_texts, framework_names
    ):
        notes.append(
            "your draft offers a set of questions, but you have not yet said what you make of "
            "their situation and had them answer it; say what you think is going on underneath "
            "what they told you, in a few plain sentences they could correct, and ask whether "
            "you have it right"
        )
    elif technique and reply.next_move not in (None, "offer"):
        notes.append(
            f"your draft offers a set of questions but next_move is {reply.next_move}; offer only "
            "when you chose to, otherwise offer nothing and do what next_move says"
        )
    elif may_offer and not technique and reply.next_move == "offer":
        notes.append(
            "you chose next_move offer but sent no Try it button; offer it with the Try it button "
            "and the framework id, or choose another move"
        )
    return notes
