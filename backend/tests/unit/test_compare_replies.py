# ABOUTME: Checks the MVP side of the comparison is composed the way the MVP composed it.
# ABOUTME: A baseline built in the wrong order would measure a prompt the client never used.

from scripts.compare_replies import mvp_ctx, mvp_system_prompt, render
from scripts.eval_replies import Exchange


def _write(directory, name, body):
    (directory / f"{name}.md").write_text(f"---\nname: {name}\n---\n\n{body}\n")


def test_the_mvp_prompt_keeps_the_mvps_own_layer_order(tmp_path):
    for name in ("mani_base", "techniques", "response_format"):
        _write(tmp_path, name, f"BODY OF {name}")
    (tmp_path / "README.md").write_text("# not a prompt\n")

    prompt = mvp_system_prompt("Sam", tmp_path)

    order = [prompt.index(f"BODY OF {n}") for n in ("mani_base", "techniques")]
    order += [prompt.index('The user prefers to be called "Sam".'), prompt.index("BODY OF response_format")]
    assert order == sorted(order)
    assert "not a prompt" not in prompt


def test_the_mvp_prompt_leaves_out_user_context_without_a_nickname(tmp_path):
    for name in ("mani_base", "techniques", "response_format"):
        _write(tmp_path, name, name)
    assert "User Context" not in mvp_system_prompt(None, tmp_path)


def test_the_mvp_ctx_block_matches_the_mvps_format():
    assert mvp_ctx([]) == "[ctx]\ncooldown_passed: yes\n[/ctx]\n\n"
    block = mvp_ctx([("mirror and ask", "receiving"), ("presence only", None)])
    assert "recent_styles: mirror and ask (receiving) → presence only\n" in block


def test_every_style_answers_under_each_line_the_person_said():
    ours = {
        "supportive": [Exchange(message="hi", reply="S1"), Exchange(message="more", reply="S2", buttons=["Try it"])],
        "direct": [Exchange(message="hi", reply="D1"), Exchange(message="more", reply="D2")],
    }
    page = render("demo", ["hi", "more"], ["M1", "M2"], ours)

    assert page.index("**Person:** hi") < page.index("M1") < page.index("S1") < page.index("D1")
    assert page.index("**Person:** more") < page.index("M2") < page.index("S2")
    assert "`[Try it]`" in page
