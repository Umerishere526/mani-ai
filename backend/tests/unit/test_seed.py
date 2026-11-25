# ABOUTME: What the seed reads from a prompt file's frontmatter: the model, its parameters and its routing, which
# ABOUTME: is how the turn's model and zero-data-retention hosts reach the database.

from scripts.seed import PROMPTS_DIR, parse_prompt


def test_a_prompt_file_carries_its_routing():
    prompt = parse_prompt(PROMPTS_DIR / "mani.md")
    assert prompt["model_id"] == "deepseek/deepseek-v4.1-flash-1017"
    assert prompt["model_parameters"] == {"reasoning_effort": "high", "temperature": 0.3}
    assert prompt["routing"] == {"only": ["sail-research", "deepinfra"], "sort": "price", "zdr": True}


def test_a_prompt_file_without_routing_has_none():
    assert parse_prompt(PROMPTS_DIR / "summarization.md")["routing"] == {}



def test_a_framework_needs_no_offer_template_since_the_model_writes_the_offer():
    from scripts.seed import FRAMEWORKS_DIR, missing_for_activation, parse_framework

    framework = parse_framework(FRAMEWORKS_DIR / "abcde.md")
    assert "offer" not in framework["stages"]["offering"]
    assert missing_for_activation(framework) == []


def test_a_framework_stage_without_its_purpose_cannot_be_seeded_active():
    from scripts.seed import FRAMEWORKS_DIR, missing_for_activation, parse_framework

    framework = parse_framework(FRAMEWORKS_DIR / "abcde.md")
    framework["stages"]["belief"].pop("purpose")
    assert missing_for_activation(framework) == ["stages.belief.purpose"]


def test_the_prompt_asks_the_risk_classifications_clarifying_question_word_for_word():
    """S5 (PROVISIONAL: clinician sign-off required before deploy): the client's Risk Classification answers each
    MEDIUM phrase with one direct question in her words; a paraphrase drifts from what she approved."""
    safety = parse_prompt(PROMPTS_DIR / "mani.md")["content"].split("# Safety", 1)[1].split("\n# ", 1)[0]
    assert '"Are you thinking about hurting yourself, or are you feeling overwhelmed?"' in safety
    for medium in ("I feel numb", "I wish I could disappear", "I'm exhausted with life"):
        assert medium in safety, medium
