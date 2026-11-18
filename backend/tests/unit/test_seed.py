# ABOUTME: What the seed reads from a prompt file's frontmatter: the model, its parameters and its routing, which
# ABOUTME: is how the turn's model and zero-data-retention hosts reach the database.

from scripts.seed import PROMPTS_DIR, parse_prompt


def test_a_prompt_file_carries_its_routing():
    prompt = parse_prompt(PROMPTS_DIR / "mani.md")
    assert prompt["model_id"] == "minimax/minimax-m3.1-flash"
    assert prompt["model_parameters"] == {"reasoning_effort": "low", "temperature": 0.3}
    assert prompt["routing"] == {
        "only": ["inferact-vllm", "together", "modelrun", "fireworks", "makora", "nebius"], "zdr": True,
    }


def test_a_prompt_file_without_routing_has_none():
    assert parse_prompt(PROMPTS_DIR / "summarization.md")["routing"] == {}



def test_a_framework_needs_no_offer_template_since_the_model_writes_the_offer():
    from scripts.seed import FRAMEWORKS_DIR, missing_for_activation, parse_framework

    framework = parse_framework(FRAMEWORKS_DIR / "abcde.md")
    assert "offer" not in framework["stages"]["offering"]
    assert missing_for_activation(framework) == []


def test_a_framework_without_its_worked_example_cannot_be_seeded_active():
    from scripts.seed import FRAMEWORKS_DIR, missing_for_activation, parse_framework

    framework = parse_framework(FRAMEWORKS_DIR / "abcde.md")
    framework["stages"]["offering"].pop("example", None)
    assert missing_for_activation(framework) == ["stages.offering.example"]


def test_a_framework_stage_without_its_purpose_cannot_be_seeded_active():
    from scripts.seed import FRAMEWORKS_DIR, missing_for_activation, parse_framework

    framework = parse_framework(FRAMEWORKS_DIR / "abcde.md")
    framework["stages"]["belief"].pop("purpose")
    assert missing_for_activation(framework) == ["stages.belief.purpose"]
