# ABOUTME: Checks the seed refuses a framework file that is not the eight labelled lines.
# ABOUTME: Writes real framework files to a temp folder; the shipped files are parsed as they are.

from __future__ import annotations

import pytest

from mani.chat.techniques import ENDING_PHASES
from scripts.seed import FRAMEWORKS_DIR, parse_framework

FRONTMATTER = """---
id: abcde
name: ABCDE
summary: "Look at what a setback came to mean."
display_order: 1
phases: [offering, activate, belief, consequence, examine, balanced, closing]
activation:
  never_offer_when_said: ["died"]
---
"""

LINES = [
    "Starts when: you have learned the event that set it off and what it came to mean about them.",
    'Sounds like: "so I must be", "this proves I", one setback read as a verdict on who they are.',
    "Skip when: one quick thought to reframe (thought_reframe), or they only want to be heard.",
    "Stages: activate (what happened) > belief (what it came to mean) > consequence (how believing it "
    "affected them) | examine (what supports it, then what challenges it) > balanced (a fairer "
    "belief) > closing (how it sits now)",
    "Ends when: they hold a belief that fits all the evidence and sounds like them.",
    "Offer: mirror what the event came to mean to them, in their words, then ask if they want to look at it.",
    "Never: invent evidence, or decide the belief is false.",
    "Never: question whether abuse or danger was real or as serious as it felt.",
]


def write(tmp_path, lines=LINES, frontmatter=FRONTMATTER):
    path = tmp_path / "abcde.md"
    path.write_text(frontmatter + "\n".join(lines) + "\n")
    return path


def test_eight_labelled_lines_seed_as_the_body_and_starts_when_as_the_activation_text(tmp_path):
    parsed = parse_framework(write(tmp_path))

    assert parsed["body"] == "\n".join(LINES)
    assert parsed["activation_conditions"] == LINES[0].removeprefix("Starts when: ")
    assert parsed["stages"] == {}
    assert parsed["phases"][0] == "offering"


def test_the_body_ending_follows_the_files_own_phases_in_every_shipped_framework():
    for path in sorted(FRAMEWORKS_DIR.glob("*.md")):
        parsed = parse_framework(path)
        assert parsed["phases"][-3:] == ["closing", *ENDING_PHASES], path.name
        assert parsed["stages"] == {}, path.name


def _replaced(index, line):
    return LINES[:index] + [line] + LINES[index + 1:]


@pytest.mark.parametrize(
    ("lines", "reason"),
    [
        (LINES + ["Never: a third rule."], "the body has 9 lines, not 8"),
        (LINES[:3] + [""] + LINES[3:7], "line 4 should start with 'Stages: '"),
        (["# ABCDE"] + LINES[:7], "line 1 should start with 'Starts when: '"),
        (LINES[:4] + LINES[5:] + ["Never: one more."], "line 5 should start with 'Ends when: '"),
        ([LINES[1], LINES[0]] + LINES[2:], "line 1 should start with 'Starts when: '"),
        (_replaced(4, "Ends when: " + "x" * 210), "the Ends when line is 221 characters, over 220"),
        (_replaced(3, LINES[3] + " " + "y" * (320 - len(LINES[3]))), "the Stages line is 321 characters, over 320"),
        (
            _replaced(3, "Stages: activate (what happened) > belief (what it meant) | examine (the evidence) "
                         "> balanced (a fairer belief) > closing (how it sits)"),
            "the Stages line names activate, belief, examine, balanced, closing, but phases after "
            "offering are activate, belief, consequence, examine, balanced, closing",
        ),
        (_replaced(3, "Stages: activate | belief"), "the stage 'activate' should be an id and a few words"),
        (_replaced(3, LINES[3].replace(" | ", " > ")), "the Stages line needs exactly one '|'"),
        (_replaced(3, LINES[3].replace(" > balanced", " | balanced")), "the Stages line needs exactly one '|'"),
        (_replaced(3, "Stages:  | examine (the evidence)"), "no stage on one side of the '|'"),
        (_replaced(3, "Stages: activate (what happened) | "), "no stage on one side of the '|'"),
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
        (FRONTMATTER.replace("[offering, activate,", "[activate,"), "phases should start with offering"),
    ],
)
def test_frontmatter_beyond_the_code_data_is_refused(tmp_path, frontmatter, reason):
    with pytest.raises(ValueError, match=reason):
        parse_framework(write(tmp_path, frontmatter=frontmatter))


def test_every_shipped_framework_is_eight_lines_with_only_code_data_beside_them():
    """parse_framework is the seed's own check, so a shipped file it refuses could never be seeded."""
    files = sorted(FRAMEWORKS_DIR.glob("*.md"))
    assert len(files) == 6
    for path in files:
        assert len(parse_framework(path)["body"].split("\n")) == 8, path.name
