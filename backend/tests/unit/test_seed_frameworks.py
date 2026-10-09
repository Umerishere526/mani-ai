# ABOUTME: Checks the seed refuses a framework file that is not the seven labelled lines, and offer wording for no file.
# ABOUTME: Writes real framework files to a temp folder; the shipped files are parsed as they are.

from __future__ import annotations

import pytest

from mani.chat.techniques import ENDING_PHASES
from scripts.seed import FRAMEWORKS_DIR, check_offer_frameworks, load_replies, parse_framework

FRONTMATTER = """---
id: abcde
name: ABCDE
summary: "Look at what a setback came to mean."
display_order: 1
phases: [offering, activating_event, belief, consequences, dispute, effective_new_belief, closing]
activation:
  never_offer_when_said: ["died"]
---
"""

LINES = [
    "Starts when: you have learned the event that set it off and what it came to mean about them.",
    'Sounds like: "so I must be", "this proves I", one setback read as a verdict on who they are.',
    "Skip when: one quick thought to reframe (thought_reframe), or they only want to be heard.",
    "Stages: activating_event (what happened) > belief (what it came to mean) > consequences (how believing it "
    "affected them) > dispute (what supports it, then what challenges it) > effective_new_belief (a fairer "
    "belief) > closing (how it sits now)",
    "Ends when: they hold a belief that fits all the evidence and sounds like them.",
    "Never: invent evidence, or decide the belief is false.",
    "Never: question whether abuse or danger was real or as serious as it felt.",
]


def write(tmp_path, lines=LINES, frontmatter=FRONTMATTER):
    path = tmp_path / "abcde.md"
    path.write_text(frontmatter + "\n".join(lines) + "\n")
    return path


def test_seven_labelled_lines_seed_as_the_body(tmp_path):
    parsed = parse_framework(write(tmp_path))

    assert parsed["body"] == "\n".join(LINES)
    assert parsed["phases"][0] == "offering"


def test_the_body_ending_follows_the_files_own_phases_in_every_shipped_framework():
    for path in sorted(FRAMEWORKS_DIR.glob("*.md")):
        parsed = parse_framework(path)
        assert parsed["phases"][-3:] == ["closing", *ENDING_PHASES], path.name


def _replaced(index, line):
    return LINES[:index] + [line] + LINES[index + 1:]


@pytest.mark.parametrize(
    ("lines", "reason"),
    [
        (LINES[:5] + ["Offer: mirror what it came to mean, then ask."] + LINES[5:],
         "the body has 8 lines, not 7"),
        (LINES[:3] + [""] + LINES[3:6], "line 4 should start with 'Stages: '"),
        (["# ABCDE"] + LINES[:6], "line 1 should start with 'Starts when: '"),
        (LINES[:4] + LINES[5:] + ["Never: one more."], "line 5 should start with 'Ends when: '"),
        ([LINES[1], LINES[0]] + LINES[2:], "line 1 should start with 'Starts when: '"),
        (_replaced(4, "Ends when: " + "x" * 210), "the Ends when line is 221 characters, over 220"),
        (_replaced(3, LINES[3] + " " + "y" * (420 - len(LINES[3]))), "the Stages line is 421 characters, over 420"),
        (
            _replaced(3, "Stages: activating_event (what happened) > belief (what it meant) > dispute (the evidence) "
                         "> effective_new_belief (a fairer belief) > closing (how it sits)"),
            "the Stages line names activating_event, belief, dispute, effective_new_belief, closing, but phases after "
            "offering are activating_event, belief, consequences, dispute, effective_new_belief, closing",
        ),
        (
            _replaced(3, LINES[3].replace(" > dispute", " | dispute")),
            "the Stages line names activating_event, belief, consequences, effective_new_belief, closing, but phases "
            "after offering are activating_event, belief, consequences, dispute, effective_new_belief, closing",
        ),
    ],
)
def test_a_body_that_breaks_the_format_is_refused_with_the_file_and_the_reason(tmp_path, lines, reason):
    with pytest.raises(ValueError) as refused:
        parse_framework(write(tmp_path, lines))
    assert str(refused.value).startswith("abcde.md: ")
    assert reason in str(refused.value)


def test_words_inside_a_stages_parentheses_may_carry_commas(tmp_path):
    lines = _replaced(3, LINES[3].replace("(what happened)", "(what happened, where, and with whom)"))
    assert parse_framework(write(tmp_path, lines))["body"].count("with whom") == 1


@pytest.mark.parametrize(
    ("frontmatter", "reason"),
    [
        (FRONTMATTER.replace("display_order: 1\n", "display_order: 1\nstages: {}\n"),
         "frontmatter keys not allowed: stages"),
        (FRONTMATTER.replace("  never_offer_when_said:", "  to_find_out: [the event]\n  never_offer_when_said:"),
         "activation keys not allowed: to_find_out"),
        (FRONTMATTER.replace("  never_offer_when_said:", "  signals: [proves i]\n  never_offer_when_said:"),
         "activation keys not allowed: signals"),
        (FRONTMATTER.replace("  never_offer_when_said:", "  distinctions: []\n  never_offer_when_said:"),
         "activation keys not allowed: distinctions"),
        (FRONTMATTER.replace('["died"]', '"died"'),
         "never_offer_when_said must be a list of non empty strings"),
        (FRONTMATTER.replace('["died"]', '["died", " "]'),
         "never_offer_when_said must be a list of non empty strings"),
        (FRONTMATTER.replace("[offering, activating_event,", "[activating_event,"), "phases should start with offering"),
        (FRONTMATTER.replace('summary: "Look at what a setback came to mean."\n', ""),
         "frontmatter has no summary"),
        (FRONTMATTER.replace('"Look at what a setback came to mean."', '"  "'), "summary must not be blank"),
    ],
)
def test_frontmatter_beyond_the_code_data_is_refused(tmp_path, frontmatter, reason):
    with pytest.raises(ValueError, match=reason):
        parse_framework(write(tmp_path, frontmatter=frontmatter))


def test_every_shipped_framework_is_seven_lines_with_only_code_data_beside_them():
    """parse_framework is the seed's own check, so a shipped file it refuses could never be seeded."""
    files = sorted(FRAMEWORKS_DIR.glob("*.md"))
    assert len(files) == 6
    for path in files:
        assert len(parse_framework(path)["body"].split("\n")) == 7, path.name


def test_offer_wording_for_a_framework_with_no_file_stops_the_seed():
    """covers: AC-2 - a mistyped or renamed id would never be offered, so its wording would go
    unused without a word; the seed refuses it by name instead."""
    replies = load_replies()
    shipped = {parse_framework(path)["id"] for path in FRAMEWORKS_DIR.glob("*.md")}
    mistyped = replies.model_copy(update={"offer": replies.offer.model_copy(update={
        "by_framework": {"abcd": replies.offer.by_framework["abcde"]},
    })})

    check_offer_frameworks(replies, shipped)
    with pytest.raises(ValueError, match="offer.by_framework names no framework file: abcd$"):
        check_offer_frameworks(mistyped, shipped)
