# ABOUTME: Checks the seed refuses a framework file that is not the eight labelled lines.
# ABOUTME: Writes real framework files to a temp folder; the shipped files are parsed as they are.

from __future__ import annotations

import pytest

from scripts.seed import FRAMEWORKS_DIR, check_distinctions, parse_framework

FRONTMATTER = """---
id: abcde
name: ABCDE
summary: "Look at what a setback came to mean."
display_order: 1
phases: [offering, activate, belief, consequence, examine, balanced, closing]
activation:
  strong_signals: ["so i must be"]
  signals: ["proves i"]
  redirects: ["i keep replaying it"]
---
"""

LINES = [
    "Starts when: you have learned the event that set it off and what it came to mean about them.",
    'Sounds like: "so I must be", "this proves I", one setback read as a verdict on who they are.',
    "Skip when: one quick thought to reframe (thought_reframe), or they only want to be heard.",
    "Stages: activate (what happened) > belief (what it came to mean) > consequence (how believing it "
    "affected them) > examine (what supports it, then what challenges it) > balanced (a fairer "
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
            _replaced(3, "Stages: activate (what happened) > belief (what it meant) > examine (the evidence) "
                         "> balanced (a fairer belief) > closing (how it sits)"),
            "the Stages line names activate, belief, examine, balanced, closing, but phases after "
            "offering are activate, belief, consequence, examine, balanced, closing",
        ),
        (_replaced(3, "Stages: activate > belief"), "the stage 'activate' should be an id and a few words"),
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
        (FRONTMATTER.replace("  signals:", "  to_find_out: [the event]\n  signals:"),
         "activation keys not allowed: to_find_out"),
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


RULE = '  distinctions:\n    - {name: a rule, priority: 1, phrases: ["so i must be"], over: []}\n'


@pytest.mark.parametrize(
    ("rule", "reason"),
    [
        (RULE.replace("over: []", "over: [], prefer: abcde"), "distinction keys not allowed: prefer"),
        (RULE.replace('["so i must be"]', "[]"), "a rule: phrases must be a non empty list"),
        (RULE.replace('["so i must be"]', '["so i must be", ""]'), "a rule: phrases must be a non empty list"),
        (RULE.replace("priority: 1", "priority: 0"), "a rule: priority must be a positive whole number"),
        (RULE.replace("priority: 1", "priority: 1.5"), "a rule: priority must be a positive whole number"),
        (RULE.replace("over: []", "over: [], standalone: maybe"), "a rule: standalone must be true or false"),
    ],
)
def test_a_distinction_that_cannot_be_a_rule_is_refused_with_the_file(tmp_path, rule, reason):
    frontmatter = FRONTMATTER.replace("\n---\n", "\n" + rule.rstrip("\n") + "\n---\n")
    with pytest.raises(ValueError, match=f"abcde.md: {reason}"):
        parse_framework(write(tmp_path, frontmatter=frontmatter))


def _framework(fid: str, *distinctions: dict) -> dict:
    return {"id": fid, "activation": {"distinctions": list(distinctions)}}


def _rule(priority: int, over: list[str], name: str = "r") -> dict:
    return {"name": name, "priority": priority, "phrases": ["p"], "over": over}


@pytest.mark.parametrize(
    ("frameworks", "reason"),
    [
        ([_framework("abcde", _rule(1, ["dbt_stop"]), _rule(1, ["dbt_stop"], "s")), _framework("dbt_stop")],
         "abcde: s: priority 1 is used twice"),
        ([_framework("abcde", _rule(1, ["nowhere"]))], "abcde: r: over names nowhere, which is unknown or its own"),
        ([_framework("abcde", _rule(1, ["abcde"]))], "abcde: r: over names abcde, which is unknown or its own"),
        ([_framework("abcde", _rule(1, [])), _framework("dbt_stop", _rule(2, [], "s"))],
         "dbt_stop: s: a second rule with an empty over"),
    ],
)
def test_distinctions_that_clash_across_files_are_refused_before_anything_is_written(frameworks, reason):
    with pytest.raises(ValueError, match=reason):
        check_distinctions(frameworks)


def test_the_shipped_distinctions_are_accepted():
    check_distinctions([parse_framework(path) for path in sorted(FRAMEWORKS_DIR.glob("*.md"))])
