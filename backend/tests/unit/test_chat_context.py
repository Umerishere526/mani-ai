# ABOUTME: Checks the hidden [ctx] block and how a tap on a capsule button is recognised.
# ABOUTME: Both read the database snapshot rather than a mutated in-memory copy.

import datetime as dt
import uuid

from mani.chat import context
from mani.chat.orchestrator import find_tapped_prompt, pending_offer
from mani.chat.router import Signal
from mani.db.threads import TurnContext
from mani.models.rows import (
    Framework,
    Message,
    MessageRole,
    Profile,
    ResponseStyle,
    TechniqueOutcome,
    TechniqueState,
    Thread,
)

USER = uuid.UUID("a0000000-0000-4000-8000-00000000000a")
THREAD = uuid.UUID("b0000000-0000-4000-8000-00000000000b")
NOW = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)


def thread(message_count: int = 10) -> Thread:
    return Thread(
        id=THREAD, user_id=USER, message_count=message_count,
        created_at=NOW, last_message_at=NOW,
    )


def mani(content: str, options: list[dict] | None = None) -> Message:
    return Message(
        id=uuid.uuid4(), thread_id=THREAD, user_id=USER, role=MessageRole.MANI,
        content=content, prompt_options=options, created_at=NOW,
    )


def user(content: str) -> Message:
    return Message(
        id=uuid.uuid4(), thread_id=THREAD, user_id=USER, role=MessageRole.USER,
        content=content, created_at=NOW,
    )


def test_a_thread_with_no_technique_says_the_cooldown_has_passed():
    block = context.build(TurnContext(thread=thread(), profile=None, technique=None))
    assert "cooldown_passed: yes" in block
    assert "since_last" not in block


def test_a_recent_decline_holds_the_cooldown_closed():
    state = TechniqueState(
        thread_id=THREAD, framework_id="abcde", outcome=TechniqueOutcome.DECLINED,
        at_message_count=8,
    )
    block = context.build(TurnContext(thread=thread(10), profile=None, technique=state))
    assert "cooldown_passed: no" in block
    assert "since_last: 2" in block
    assert "this_thread: abcde (declined)" in block


def test_an_accepted_technique_waits_for_the_library_offer():
    state = TechniqueState(
        thread_id=THREAD, framework_id="abcde", outcome=TechniqueOutcome.ACCEPTED,
        phase="ground", at_message_count=4, library_offered_since=False,
    )
    block = context.build(TurnContext(thread=thread(60), profile=None, technique=state))
    assert "library_pending: yes" in block
    assert "current_phase: ground" in block


def test_a_retired_technique_still_holds_the_cooldown_closed():
    """Completion used to delete this row. That destroyed at_message_count, so the next
    turn reported that nothing had ever run and a second framework could start at once."""
    state = TechniqueState(
        thread_id=THREAD, framework_id="abcde", outcome=TechniqueOutcome.ACCEPTED,
        phase=None, at_message_count=8,
    )
    block = context.build(TurnContext(thread=thread(10), profile=None, technique=state))
    assert "cooldown_passed: no" in block
    assert "since_last: 2" in block
    assert "this_thread: abcde (accepted)" in block
    # Retired, so there is no phase to be in.
    assert "current_phase" not in block


def test_a_finished_framework_waits_longer_than_a_declined_one():
    """45 messages against 20. The longer wait was unreachable while completion deleted
    the row it is measured from."""
    started_at = 10
    long_enough_for_a_decline = thread(started_at + context.COOLDOWN_AFTER_DECLINE)
    finished = TechniqueState(
        thread_id=THREAD, framework_id="abcde", outcome=TechniqueOutcome.ACCEPTED,
        phase=None, at_message_count=started_at,
    )
    declined = finished.model_copy(update={"outcome": TechniqueOutcome.DECLINED})

    assert "cooldown_passed: no" in context.build(
        TurnContext(thread=long_enough_for_a_decline, profile=None, technique=finished)
    )
    assert "cooldown_passed: yes" in context.build(
        TurnContext(thread=long_enough_for_a_decline, profile=None, technique=declined)
    )


def test_recent_styles_are_listed_so_a_reply_can_avoid_repeating_one():
    block = context.build(
        TurnContext(
            thread=thread(), profile=None, technique=None,
            recent_styles=[
                ResponseStyle(shape="mirror and ask", voice="naming"),
                ResponseStyle(shape="presence only"),
            ],
        )
    )
    assert "recent_styles: mirror and ask (naming) → presence only" in block


def test_a_context_block_can_be_stripped_back_out():
    """Messages written by the previous system carry one; nothing written here does."""
    stored = context.build(TurnContext(thread=thread(), profile=None, technique=None))
    assert context.strip(stored + "I had a hard day") == "I had a hard day"


def test_a_tap_is_matched_against_the_last_message_that_offered_buttons():
    history = [mani("Want to try something?", [{"label": "Yes, let's try it",
                                                "technique": "abcde"}])]
    tapped = find_tapped_prompt(history, "yes, let's try it")
    assert tapped is not None and tapped.technique == "abcde"


def test_a_stale_offer_is_not_matched_once_mani_has_spoken_again():
    """The reference searched back to the last Mani message carrying any options, so a
    plain reply in between left the old offer live and every later answer resolved it."""
    history = [
        mani("Want to try something?", [{"label": "Yes, let's try it", "technique": "abcde"}]),
        user("not now, I want to talk about work"),
        mani("Tell me about work."),
    ]
    assert find_tapped_prompt(history, "yes, let's try it") is None
    assert pending_offer(history) is None


def test_typed_text_is_not_mistaken_for_a_tap():
    history = [mani("Want to try something?", [{"label": "Yes, let's try it"}])]
    assert find_tapped_prompt(history, "I think so maybe") is None


def framework() -> Framework:
    return Framework(
        id="abcde", name="ABCDE", summary="s", body="b",
        phases=["offering", "activate", "belief", "consequence"],
        stages={
            "offering": {
                "purpose": "Offer the framework once the event and belief are understood.",
                "ask": {"direct": "Would you like to work through it?"},
            },
            "activate": {
                "purpose": "Identify the event.",
                "listen_for": "What happened.",
                "ready_when": "The event is clear.",
                "boundaries": ["must not assume a motive", "must not merge events"],
                "if_unclear": [{"when": "too broad", "reply": "Which event?"}],
                "ask": {"supportive": "What happened?", "direct": "State the facts."},
            },
            "belief": {
                "purpose": "Identify the belief.",
                "ask": {"supportive": "What did that mean to you?"},
            },
        },
    )


def test_the_router_shortlist_is_a_ranked_annotation_not_a_decision():
    block = context.build(
        TurnContext(thread=thread(), profile=None, technique=None),
        shortlist=[Signal("behavioral_activation", 2.6, ["cannot make myself begin"])],
    )
    assert "framework_shortlist: behavioral_activation (2.60)" in block


def test_a_confident_candidate_adds_its_offer_line_resolved_to_style():
    profile = Profile(user_id=USER, support_style="direct")
    block = context.build(
        TurnContext(thread=thread(), profile=profile, technique=None),
        shortlist=[Signal("abcde", 2.6, ["she said"], spread=2)],
        candidate=framework(),
    )
    assert "offer_purpose: Offer the framework once the event and belief are understood." in block
    assert "offer_ask: Would you like to work through it?" in block


def test_an_unconfident_shortlist_carries_no_candidate_content():
    """Below the confidence threshold, the shortlist is ids and scores only - central
    indications for those ids already sit in the static Framework Index."""
    block = context.build(
        TurnContext(thread=thread(), profile=None, technique=None),
        shortlist=[Signal("abcde", 0.6, ["she said"])],
        candidate=framework(),
    )
    assert "framework_shortlist: abcde (0.60)" in block
    assert "offer_purpose" not in block
    assert "offer_ask" not in block


def test_an_active_framework_carries_current_and_next_stage_resolved_to_style():
    state = TechniqueState(
        thread_id=THREAD, framework_id="abcde", outcome=TechniqueOutcome.ACCEPTED,
        phase="activate", at_message_count=4,
    )
    profile = Profile(user_id=USER, support_style="direct")
    block = context.build(
        TurnContext(thread=thread(), profile=profile, technique=state),
        framework=framework(),
    )
    assert "active_framework: abcde" in block
    assert "framework_stages: offering, activate, belief, consequence" in block
    assert "stage_purpose: Identify the event." in block
    assert "stage_boundaries: must not assume a motive; must not merge events" in block
    assert "stage_if_unclear: if too broad: Which event?" in block
    assert "stage_ask: State the facts." in block
    # The next stage's purpose and its style-resolved ask, even though "belief" is not
    # the current stage - this is what lets a reply anticipate where it is headed.
    assert "next_stage: belief" in block
    assert "next_stage_purpose: Identify the belief." in block
    # "belief" has no "direct" ask in the fixture, so nothing is fabricated for it.
    assert "next_stage_ask" not in block


def test_the_last_stage_has_no_next_stage():
    state = TechniqueState(
        thread_id=THREAD, framework_id="abcde", outcome=TechniqueOutcome.ACCEPTED,
        phase="consequence", at_message_count=4,
    )
    block = context.build(
        TurnContext(thread=thread(), profile=None, technique=state), framework=framework(),
    )
    assert "active_framework: abcde" in block
    assert "next_stage" not in block


def test_the_conversations_own_style_wins_over_the_profile_default():
    """Onboarding sets a default; a thread may differ from it without changing it. That
    is the whole reason threads.conversation_style exists beside profiles.support_style."""
    state = TechniqueState(
        thread_id=THREAD, framework_id="abcde", outcome=TechniqueOutcome.ACCEPTED,
        phase="activate", at_message_count=4,
    )
    chose_direct = Thread(
        id=THREAD, user_id=USER, message_count=10, created_at=NOW, last_message_at=NOW,
        conversation_style="direct",
    )
    block = context.build(
        TurnContext(
            thread=chose_direct,
            profile=Profile(user_id=USER, support_style="supportive"),
            technique=state,
        ),
        framework=framework(),
    )
    assert "stage_ask: State the facts." in block


def test_style_falls_back_to_supportive_with_no_profile_or_choice():
    state = TechniqueState(
        thread_id=THREAD, framework_id="abcde", outcome=TechniqueOutcome.ACCEPTED,
        phase="activate", at_message_count=4,
    )
    block = context.build(
        TurnContext(thread=thread(), profile=None, technique=state), framework=framework(),
    )
    assert "stage_ask: What happened?" in block
