# ABOUTME: Checks the deterministic corrections that replaced six regeneration calls.
# ABOUTME: Each case here cost an entire extra model call in the implementation ported from.

import pytest

from mani.chat import repairs
from mani.chat.techniques import Registry
from mani.llm.schema import Reply, SmartPrompt, Style, TechniqueState
from mani.models.rows import Framework

REFRAMING = Framework(
    id="thought_reframing", name="Thought Reframing", summary="s", body="b",
    phases=["offering", "surface", "externalize", "explore", "land", "ground"],
)
ABCDE = Framework(
    id="abcde", name="ABCDE", summary="s", body="b",
    phases=["offering", "activate", "belief", "consequence", "dispute", "effect", "ground"],
)


@pytest.fixture
def registry() -> Registry:
    return Registry([REFRAMING, ABCDE])


def reply(**overrides) -> Reply:
    return Reply(**({"text": "That sounds heavy to carry."} | overrides))


def fix(registry, model_reply, **overrides):
    defaults = {
        "said": "",
        "already_offered": [],
        "current_framework_id": None,
        "current_phase": None,
        "selected_label": None,
        "accepted_this_turn": False,
        "framework_running": False,
        "cooldown_passed": True,
        "conversation_style": "supportive",
        "wants_title": False,
    }
    return repairs.apply(model_reply, registry, **(defaults | overrides))


def test_mirroring_the_users_own_word_is_not_censored(registry):
    """The reference refused "heavy" anywhere, while instructing Mani to mirror."""
    assert fix(registry, reply()).text == "That sounds heavy to carry."


def test_leaked_script_metadata_is_stripped(registry):
    leaked = reply(
        text="Let's try something.\n\n**Mani:** Take a breath.\n\n(Include prompts: yes/no)"
    )
    fixed = fix(registry, leaked)
    assert "**Mani:**" not in fixed.text
    assert "Include prompts" not in fixed.text
    assert "Let's try something." in fixed.text
    assert fixed.notes


def test_an_already_offered_technique_is_dropped(registry):
    offered_again = reply(
        prompts=[
            SmartPrompt(label="Yes, let's try it", technique="abcde"),
            SmartPrompt(label="Not right now"),
        ]
    )
    fixed = fix(registry, offered_again, already_offered=["abcde"])
    assert [p.label for p in fixed.prompts] == ["Not right now"]


def test_the_technique_being_offered_is_not_a_duplicate_of_itself(registry):
    still_offering = reply(
        prompts=[SmartPrompt(label="Yes, let's try it", technique="abcde")]
    )
    fixed = fix(
        registry, still_offering, already_offered=["abcde"], current_framework_id="abcde"
    )
    assert len(fixed.prompts) == 1


def test_no_framework_is_offered_from_inside_a_running_one(registry):
    """A framework in progress is the whole conversation until it completes or the person
    stops it. The same one restarting itself and a second one opening underneath it are the
    same failure - the person is left inside two at once."""
    nested = reply(
        prompts=[
            SmartPrompt(label="Try ABCDE", technique="abcde"),
            SmartPrompt(label="Try reframing", technique="thought_reframing"),
            SmartPrompt(label="Keep talking", technique=None),
        ]
    )
    fixed = fix(
        registry,
        nested,
        current_framework_id="abcde",
        current_phase="belief",
        framework_running=True,
    )
    assert [p.label for p in fixed.prompts] == ["Keep talking"]


def test_an_invented_technique_id_is_refused(registry):
    """A model-supplied identifier is untrusted until the registry recognises it."""
    invented = reply(prompts=[SmartPrompt(label="Try box breathing", technique="box_breathing")])
    assert fix(registry, invented).prompts == []


def test_the_button_the_user_just_tapped_is_not_offered_back(registry):
    echoed = reply(
        prompts=[SmartPrompt(label="Yes, let's try it"), SmartPrompt(label="Tell me more")]
    )
    fixed = fix(registry, echoed, selected_label="  yes, let's try it ")
    assert [p.label for p in fixed.prompts] == ["Tell me more"]


def test_more_than_three_buttons_are_trimmed(registry):
    many = reply(prompts=[SmartPrompt(label=f"Option {n}") for n in range(6)])
    assert len(fix(registry, many).prompts) == repairs.MAX_PROMPTS


def test_reply_text_mirroring_an_established_feeling_is_not_flagged(registry):
    """The prose check exists to catch invention, not mirroring - the same exemption the
    capsule check already gets from `said`."""
    mirrored = reply(text="You sound worried right now. What's on your mind?")
    fixed = fix(registry, mirrored, said="I feel worried about tomorrow")
    assert fixed.text == "You sound worried right now. What's on your mind?"
    assert fixed.notes == []


def test_reply_text_introducing_an_unestablished_feeling_is_noted(registry):
    """Observational only: the note is logged, the text is neither rewritten nor dropped."""
    invented = reply(text="You're worried about it. What happens next?")
    fixed = fix(registry, invented, said="I have a presentation tomorrow")
    assert fixed.text == "You're worried about it. What happens next?"
    assert any("worried" in note for note in fixed.notes)


def test_reply_text_with_no_feeling_words_is_not_flagged(registry):
    unrelated = reply(text="What happens next in your plan?")
    fixed = fix(registry, unrelated, said="I have a presentation tomorrow")
    assert fixed.notes == []


def test_a_capsule_cannot_put_a_feeling_in_their_mouth_but_may_mirror_their_own(registry):
    """A label is the one part of a reply the person may send back as their own words, so
    a feeling they never named must not appear in one. A feeling they did name is the
    mirroring the same prompt asks for, and an earlier word list that could not tell the
    two apart is why this rule is written against what they said rather than a blocklist."""
    mixed = reply(
        prompts=[
            SmartPrompt(label="It's frustrating"),
            SmartPrompt(label="Still embarrassed"),
            SmartPrompt(label="I was not enough for her at all"),
        ]
    )
    fixed = fix(registry, mixed, said="I felt embarrassed in front of everyone")
    assert [p.label for p in fixed.prompts] == ["Still embarrassed"]
    assert len(fixed.notes) == 2


def test_a_capsule_that_judges_them_is_dropped(registry):
    """Observed live: a reply offered "I'm overthinking it" as a button to press."""
    judging = reply(
        prompts=[SmartPrompt(label="Tell me more"), SmartPrompt(label="I'm overthinking it")]
    )
    fixed = fix(registry, judging)
    assert [p.label for p in fixed.prompts] == ["Tell me more"]
    assert fixed.notes


def test_a_skipped_phase_is_corrected_rather_than_regenerated(registry):
    jumped = reply(state=TechniqueState(technique="thought_reframing", step="land"))
    fixed = fix(registry, jumped, current_framework_id="thought_reframing",
                current_phase="offering")
    assert fixed.phase == "surface"
    assert fixed.notes


def test_a_technique_appearing_mid_flow_is_pulled_back_to_offering(registry):
    straight_in = reply(state=TechniqueState(technique="abcde", step="belief"))
    assert fix(registry, straight_in).phase == "offering"


def test_state_for_an_unknown_technique_is_ignored(registry):
    nonsense = reply(state=TechniqueState(technique="somatic_release", step="offering"))
    fixed = fix(registry, nonsense)
    assert fixed.framework_id is None and fixed.phase is None


def test_a_long_title_is_trimmed_not_rejected(registry):
    """The schema capped this at 50 and failed the whole generation over it."""
    long = reply(title='  "Talking through a really long and rambling worry about work."  ')
    fixed = fix(registry, long, wants_title=True)
    assert fixed.title.startswith("Talking through")
    assert not fixed.title.endswith(".")
    assert len(fixed.title) <= repairs.MAX_TITLE_LENGTH


def test_a_title_is_ignored_when_none_was_asked_for(registry):
    assert fix(registry, reply(title="Unasked for")).title is None


def test_a_clean_reply_is_left_alone(registry):
    clean = reply(
        prompts=[SmartPrompt(label="Tell me more")],
        style=Style(shape="mirror and ask", voice="naming"),
    )
    fixed = fix(registry, clean)
    assert fixed.notes == []
    assert [p.label for p in fixed.prompts] == ["Tell me more"]


def test_a_style_the_model_reports_in_title_case_still_counts(registry):
    """The shapes are taught in a table, so the model returns them capitalised as often as
    not. Dropping those would starve the anti-repetition loop rather than protect it."""
    titled = reply(style=Style(shape="Mirror And Ask", voice="Naming"))
    fixed = fix(registry, titled)
    assert fixed.style == Style(shape="mirror and ask", voice="naming")
    assert fixed.notes == []


def test_an_off_list_shape_is_dropped_rather_than_failing_the_turn(registry):
    """A value outside the set is a ValidationError if the schema types it as an enum, and
    that costs a second provider call and then the person's message. It is only a self
    report about a reply that is otherwise fine, so it is dropped and the reply stands."""
    invented = reply(style=Style(shape="vibes", voice="naming"))
    fixed = fix(registry, invented)
    assert fixed.style is None
    assert fixed.text == "That sounds heavy to carry."
    assert fixed.notes


def test_an_off_list_voice_keeps_the_shape_it_came_with(registry):
    """voice is already nullable and shape is the anchor the block formats around, so only
    the half that is wrong is discarded."""
    half_wrong = reply(style=Style(shape="mirror and ask", voice="shouting"))
    fixed = fix(registry, half_wrong)
    assert fixed.style == Style(shape="mirror and ask", voice=None)
    assert fixed.notes


def test_a_button_to_a_library_section_that_does_not_exist_lands_on_the_library_home(registry):
    """Same reasoning as the shape: an enum here fails the whole turn. Observed values -
    "library", "default", a topic phrase - all meant the library in general, so the button
    keeps working and opens the front page rather than a section that does not exist."""
    nowhere = reply(
        prompts=[SmartPrompt(label="Go to Library", library="library"),
                 SmartPrompt(label="Tell me more")]
    )
    fixed = fix(registry, nowhere)
    assert [(p.label, p.library) for p in fixed.prompts] == [
        ("Go to Library", "home"), ("Tell me more", None),
    ]
    assert fixed.notes


def test_a_library_section_the_model_cased_differently_is_kept_and_corrected(registry):
    """A client navigates on this string exactly, so a value that matches loosely still has
    to leave repaired at the one spelling that string will actually match against."""
    lowercased = reply(
        prompts=[SmartPrompt(label="Read more", library="emotionalintelligence")]
    )
    fixed = fix(registry, lowercased)
    assert [p.library for p in fixed.prompts] == ["EmotionalIntelligence"]
    assert fixed.notes == []


def test_a_technique_offered_before_the_cooldown_has_passed_is_dropped(registry):
    """The cooldown paces offers so a person is not handed one framework after another. The
    prompt states it; this is what holds it when the model does not."""
    early = reply(
        prompts=[SmartPrompt(label="Try it", technique="abcde"), SmartPrompt(label="Not now")]
    )
    fixed = fix(registry, early, cooldown_passed=False)
    assert [p.label for p in fixed.prompts] == ["Not now"]
    assert any("cooldown" in n for n in fixed.notes)


def test_the_offer_still_waiting_for_an_answer_is_not_held_to_its_own_cooldown(registry):
    """The cooldown is measured from the offer itself, so without this the button for the
    offer the person has not answered yet would vanish on the very next turn."""
    pending = reply(prompts=[SmartPrompt(label="Yes, let's try", technique="abcde")])
    fixed = fix(
        registry, pending, cooldown_passed=False,
        current_framework_id="abcde", current_phase="offering", already_offered=["abcde"],
    )
    assert [p.technique for p in fixed.prompts] == ["abcde"]


def test_state_naming_a_different_framework_than_the_running_one_is_ignored(registry):
    """Every framework ends on the same stage ids, so a transition check alone lets the model
    record a framework the person never agreed to. Only the running one may be reported."""
    # Both frameworks exist and both have "offering", so only the identity check can refuse.
    swapped = reply(state=TechniqueState(technique="thought_reframing", step="surface"))
    fixed = fix(
        registry, swapped, framework_running=True,
        current_framework_id="abcde", current_phase="offering",
    )
    assert fixed.framework_id is None
    assert any("not the running one" in n for n in fixed.notes)


def test_the_offer_buttons_all_survive(registry):
    """The three buttons under every offer (muhammad, 2026-09-24): none may be lost to the
    label-length or offer-coherence repairs."""
    offer = reply(
        text="I have a sequence of questions that could help. Would you like to try it?",
        prompts=[
            SmartPrompt(label="Try it", technique="abcde"),
            SmartPrompt(label="Tell me about this"),
            SmartPrompt(label="Keep chatting", decline=True),
        ],
    )
    fixed = fix(registry, offer)
    assert [p.label for p in fixed.prompts] == ["Try it", "Tell me about this", "Keep chatting"]


def test_an_offer_refused_by_the_cooldown_takes_its_words_with_it(registry):
    """Dropping only the buttons left "Would you like to try it?" asking for a yes that
    nothing could take. The mirror before it stays."""
    early = reply(
        text="You open the report and then move away from it. I have a sequence of questions "
             "that could help you start. Would you like to try it?",
        prompts=[
            SmartPrompt(label="Try it", technique="abcde"),
            SmartPrompt(label="Tell me about this"),
            SmartPrompt(label="Keep chatting", decline=True),
        ],
    )
    fixed = fix(registry, early, cooldown_passed=False)
    assert fixed.prompts == []
    assert fixed.text == "You open the report and then move away from it."


@pytest.mark.parametrize("offer", [
    "There's a set of questions that could help you with this. Would you like to try it?",
    "We could go through a few questions together. Would you like to try that?",
    "There are some questions that might help set your mind at ease. Shall we go through them?",
    "Would it help to look at it together, one step at a time?",
])
def test_an_offer_in_any_wording_goes_with_its_button(registry, offer):
    """Offers are worded fresh each time (muhammad, 2026-09-24), so recognising one cannot
    depend on a single fixed sentence."""
    early = reply(
        text=f"You open the report and then move away from it. {offer}",
        prompts=[SmartPrompt(label="Try it", technique="abcde"),
                 SmartPrompt(label="Keep chatting", decline=True)],
    )
    fixed = fix(registry, early, cooldown_passed=False)
    assert fixed.text == "You open the report and then move away from it."


def test_varied_offer_wording_keeps_its_buttons(registry):
    offer = reply(
        text="There are some questions that might help set your mind at ease. Shall we go through them?",
        prompts=[SmartPrompt(label="Try it", technique="abcde"),
                 SmartPrompt(label="Tell me about this"),
                 SmartPrompt(label="Keep chatting", decline=True)],
    )
    assert [p.label for p in fix(registry, offer).prompts] == ["Try it", "Tell me about this", "Keep chatting"]


def test_an_offer_made_only_by_buttons_gets_the_clients_permission_question(registry):
    """The client's offer is a spoken question the buttons answer. A reply that mirrors and
    then lets the buttons do the asking leaves the person with nothing to say yes to."""
    silent = reply(
        text="You're replaying the exchange and wondering where you went wrong.",
        prompts=[
            SmartPrompt(label="Yes, let's try it", technique="abcde"),
            SmartPrompt(label="Tell me more"),
            SmartPrompt(label="I want to keep talking", decline=True),
        ],
    )
    fixed = fix(registry, silent, conversation_style="direct")
    assert fixed.text.endswith("Would you like to try it with me?")
    assert len(fixed.prompts) == 3


def test_offer_buttons_under_a_different_question_are_dropped(registry):
    """"What feels strongest right now?" with [Yes, let's try it] under it asks one thing and
    offers another. Dropping the offer is the safe correction; it can come next turn."""
    mixed = reply(
        text="Your chest feels tight and your thoughts are racing. What feels strongest right now?",
        prompts=[
            SmartPrompt(label="Yes, let's try it", technique="abcde"),
            SmartPrompt(label="Tell me more"),
            SmartPrompt(label="I want to keep talking", decline=True),
        ],
    )
    fixed = fix(registry, mixed, conversation_style="reflective")
    assert fixed.prompts == []
    assert fixed.text.endswith("What feels strongest right now?")


def test_a_real_offer_is_left_alone(registry):
    offer = reply(
        text="I have a structured approach that can help you work through this. Would you like to try it with me?",
        prompts=[SmartPrompt(label="Yes, let's try it", technique="abcde"),
                 SmartPrompt(label="Tell me more"),
                 SmartPrompt(label="I want to keep talking", decline=True)],
    )
    fixed = fix(registry, offer, conversation_style="direct")
    assert fixed.text == offer.text and len(fixed.prompts) == 3


@pytest.mark.parametrize(
    ("style", "text", "expected"),
    [
        # Live replies, Direct and Reflective, after someone asked only to be heard.
        ("reflective", "Then we'll just talk. I'm listening whenever you're ready to share more.",
         "Then we'll just talk."),
        ("reflective", "I'm listening. Tell me what is happening for you right now.",
         "Tell me what is happening for you right now."),
        ("direct", "I appreciate you sharing that with me. I'm here if you have more to get out.",
         "I appreciate you sharing that with me."),
        # Supportive may say it - the client's own Supportive example does.
        ("supportive", "I'm here with you. What was it about the text?", "I'm here with you. What was it about the text?"),
        # Never left with nothing to send.
        ("reflective", "I'm here.", "I'm here."),
        # The client's own Direct lines open on "I" and announce nothing.
        ("direct", "I'm sorry you're feeling this way. Tell me what is happening right now.",
         "I'm sorry you're feeling this way. Tell me what is happening right now."),
    ],
)
def test_presence_is_announced_only_in_supportive(registry, style, text, expected):
    """mani_base: saying presence out loud is a Supportive move only; Direct shows it by a
    clear next step and Reflective by what it reflects. The model's habit wins over the prompt
    when someone asks just to be heard, so the sentence is removed rather than argued with."""
    fixed = fix(registry, reply(text=text), conversation_style=style)
    assert fixed.text == expected
