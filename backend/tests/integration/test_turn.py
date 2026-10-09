# ABOUTME: Runs whole turns against a live database with a scripted model in place.
# ABOUTME: The model is faked; every write, policy and transition under test is real.

import dataclasses
import json
import logging
import uuid
from types import SimpleNamespace

import asyncpg
import pytest

from mani.auth.jwt import Claims
from mani.chat import context, crisis, orchestrator
from mani.config import get_settings
from mani.db import llm_calls, messages as messages_db, profiles, threads
from mani.errors import ErrorCategory, ServiceError
from mani.llm import chain, client
from mani.llm.schema import Crisis, Reply, SmartPrompt, StageReport, Style, TechniqueState
from mani.models import rows
from mani.models.rows import LedgerEntry, StageStatus, TechniqueOutcome
from tests.integration.cleanup import remove_test_users
from tests.seeded import seeded_replies, seeded_tuning

# The seeded numbers and lines, which a test overrides one key at a time.
REPLIES = seeded_replies()
TUNING = seeded_tuning()
STYLE_WINDOW = TUNING.windows.style_window
CONTEXT_WINDOW = TUNING.windows.context_window

ALICE = uuid.UUID("a0000000-0000-4000-8000-0000000000d1")
# The real exercise pick, kept before the autouse fixture below replaces it in every test.
REAL_CHOOSE_EXERCISE = client.choose_exercise


def claims_for(user_id: uuid.UUID) -> Claims:
    return Claims(sub=str(user_id), raw={"sub": str(user_id), "role": "authenticated"})


class ScriptedModel:
    """A model that answers from a script, and counts how often it was asked.

    The count is the regression test for one chat call per turn: the implementation ported
    from made up to twenty-one provider calls for one user message, because every output
    check it failed was answered by generating again.
    """

    def __init__(self, *replies: Reply) -> None:
        self._replies = list(replies)
        self.calls = 0
        self.last_messages: list[dict] | None = None
        self.last_kwargs: dict = {}

    async def __call__(self, messages, schema, **kwargs):
        self.calls += 1
        self.last_messages = messages
        self.last_kwargs = kwargs
        reply = self._replies[min(self.calls - 1, len(self._replies) - 1)]
        return client.Call(value=reply, call_id=uuid.uuid4())


class ScriptedChooser:
    """Stands in for the exercise-selection tool call, counting when it was needed.

    A completing framework is the only turn shape that reaches it, and only when the
    catalog actually has something for that framework - so `calls` is the regression test
    for the second provider call staying rare rather than becoming routine.
    """

    def __init__(self, chosen: str | None = None) -> None:
        self._chosen = chosen
        self.calls = 0
        self.kwargs: dict = {}
        self.candidates: list[dict] = []
        self.instruction: str | None = None

    async def __call__(self, candidates, framework_name, instruction, **kwargs):
        self.calls += 1
        self.kwargs = kwargs
        self.candidates = candidates
        self.instruction = instruction
        return self._chosen if self._chosen is not None else candidates[0]["id"]


@pytest.fixture(autouse=True)
def no_real_exercise_call(monkeypatch):
    """Every completing framework reaches the exercise pick once the catalog is seeded, and
    no test here may spend a real provider call on it. A test that wants to watch the pick
    installs its own chooser, which replaces this one."""
    monkeypatch.setattr(orchestrator.client, "choose_exercise", ScriptedChooser())


async def reachable() -> bool:
    try:
        conn = await asyncpg.connect(get_settings().database_url, timeout=3)
    except (OSError, asyncpg.PostgresError):
        return False
    await conn.close()
    return True


@pytest.fixture
async def alice():
    if not await reachable():
        pytest.skip("no database reachable; run `supabase start`")
    from mani.db import pool

    await pool.open_pool()
    async with pool.as_admin() as conn:
        await remove_test_users(conn, ALICE)
        await conn.execute(
            "insert into auth.users (id, email) values ($1, 'd1@t.test')", ALICE
        )
    try:
        yield claims_for(ALICE)
    finally:
        async with pool.as_admin() as conn:
            await remove_test_users(conn, ALICE)
        await pool.close_pool()


@pytest.fixture
def model(monkeypatch):
    def install(*replies: Reply) -> ScriptedModel:
        scripted = ScriptedModel(*replies)
        monkeypatch.setattr(orchestrator.client, "complete", scripted)
        return scripted

    return install


async def start(claims: Claims):
    from mani.db import pool

    async with pool.as_user(claims) as conn:
        await profiles.upsert(conn, ALICE, nickname="Al")
        thread, _ = await orchestrator.start_thread(conn, claims)
    return thread


async def past_the_opening(thread):
    """The rounds of conversation the client wants before anything is offered, already had.
    For tests about what happens to an offer, not about when one may come."""
    from mani.db import pool

    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.threads set message_count = message_count + 8 where id = $1", thread.id
        )
    return thread


async def send(claims: Claims, thread_id, content, **kwargs):
    from mani.db import pool

    async with pool.as_user(claims) as conn:
        return await orchestrator.send(conn, claims, thread_id, content, **kwargs)


async def test_a_turn_makes_one_chat_call_and_does_not_retry_a_malformed_reply(alice, model):
    scripted = model(Reply(text="Here you go. What happened?"))
    thread = await start(alice)
    await send(alice, thread.id, "I had a hard day")

    assert scripted.calls == 1
    assert scripted.last_kwargs["retry_malformed"] is False


@pytest.fixture
def tuned(monkeypatch):
    """Runs turns on the seeded config with some tuning keys replaced:
    `await tuned(windows={"context_window": 4})`."""

    async def install(**groups):
        config = await orchestrator.cache.load()
        changed = dataclasses.replace(config, tuning=seeded_tuning(**groups))

        async def load():
            return changed

        monkeypatch.setattr(orchestrator.cache, "load", load)

    return install


async def test_the_history_the_model_sees_and_the_summary_trigger_follow_the_tuned_window(
    alice, model, tuned
):
    await tuned(windows={"context_window": 4})
    scripted = model(Reply(text="What happened next?"))
    thread = await start(alice)

    first = await send(alice, thread.id, "I had a hard day")
    second = await send(alice, thread.id, "My manager shouted at me")
    third = await send(alice, thread.id, "I did not know what to say")

    # The system prompt, the last four stored messages, and this turn's message.
    assert len(scripted.last_messages) == 1 + 4 + 1
    # The greeting and two exchanges have 5 messages after the second turn, and nothing is summarized.
    assert (first.needs_summary, second.needs_summary, third.needs_summary) == (False, True, True)


async def test_the_model_replies_out_with_only_its_unstorable_parts_taken_out(alice, model):
    """Leaked script text, a stage jumped to and an unknown technique id: the words go out as
    written, and only the technique button goes."""
    written = "Here you go. What happened?\n\n**Mani:** breathe\n\n(Include prompts: yes/no)"
    scripted = model(
        Reply(
            text=written,
            prompts=[
                SmartPrompt(label="Tell Me More"),
                SmartPrompt(label="Try It", technique="made_up_technique"),
                SmartPrompt(label="Later"),
            ],
            state=TechniqueState(technique="abcde", step="dispute"),
            style=Style(shape="mirror and ask"),
        )
    )
    thread = await start(alice)
    turn = await send(alice, thread.id, "I had a hard day")

    assert scripted.calls == 1
    assert turn.content == written
    assert [p.label for p in turn.prompts] == ["Tell Me More", "Later"]


# Drafts that break a rule the prompt states: each is stored as the model wrote it, after one call.
EARLY_OFFER = Reply(
    text="An exam tomorrow with no plan is a lot to face.",
    prompts=[SmartPrompt(label="Try It", technique="structured_problem_solving"),
             SmartPrompt(label="Keep Chatting", decline=True)],
    state=TechniqueState(technique="structured_problem_solving", step="offering"),
)
GRIEF_OFFER = Reply(
    text="Losing him is a heavy thing to carry.",
    prompts=[SmartPrompt(label="Try It", technique="behavioral_activation"),
             SmartPrompt(label="Keep Chatting", decline=True)],
    state=TechniqueState(technique="behavioral_activation", step="offering"),
)


@pytest.mark.parametrize(
    ("message", "draft", "opened"),
    [
        ("i've an exam in 24 hours and i have not studied at all",
         Reply(text="An exam in 24 hours sounds incredibly stressful. What do you need first?"), False),
        ("i felt small when she questioned me in front of everyone",
         Reply(text="It is okay to feel that way. I am here with you."), False),
        ("i miss him and the flat is quiet",
         Reply(text="What is the hardest part of the evenings?", heading_toward="act_choice_point"), True),
    ],
    ids=["a feeling never named", "no question", "no offer after several messages"],
)
async def test_a_draft_that_used_to_be_asked_for_again_is_stored_as_written_after_one_call(
    alice, model, message, draft, opened
):
    scripted = model(draft)
    thread = await start(alice)
    if opened:
        await past_the_opening(thread)
    turn = await send(alice, thread.id, message)

    assert scripted.calls == 1
    assert turn.content == draft.text
    assert [p.label for p in turn.prompts] == [p.label for p in draft.prompts or []]


@pytest.mark.parametrize(
    ("message", "draft", "opened"),
    [
        ("i have an exam tomorrow and i don't know where to start", EARLY_OFFER, False),
        ("my dog died and i can't stop thinking about him", GRIEF_OFFER, True),
    ],
    ids=["an offer too early", "an offer the words rule out"],
)
async def test_an_offer_that_breaks_a_told_rule_still_goes_out_after_one_call(
    alice, model, message, draft, opened
):
    """The cooldown and the grief veto are told, not enforced, so the offer goes out: the seeded
    words."""
    scripted = model(draft)
    thread = await start(alice)
    if opened:
        await past_the_opening(thread)
    turn = await send(alice, thread.id, message)

    assert scripted.calls == 1
    assert turn.content == await _offer_turn(draft.state.technique)
    assert [p.label for p in turn.prompts] == OFFER_LABELS


async def test_the_question_asked_last_turn_is_asked_again_when_the_model_writes_it_again(alice, model):
    asked = Reply(text="What was it about that moment that stayed with you?")
    scripted = model(asked, asked)
    thread = await start(alice)
    await send(alice, thread.id, "my manager criticized me in front of everyone")
    turn = await send(alice, thread.id, "it was just bad")

    assert scripted.calls == 2
    assert turn.content == asked.text


async def test_a_tapped_button_reaches_the_model_as_its_label_under_a_key(alice, model):
    """response_format.md `buttons` says what `tapped:` means, so the code sends no sentence."""
    scripted = model(
        Reply(
            text="There are some questions we could go through together. Would you like to try it?",
            prompts=[SmartPrompt(label="Try It", technique="abcde"),
                     SmartPrompt(label="Keep Chatting", decline=True)],
            state=TechniqueState(technique="abcde", step="offering"),
        ),
        Reply(text="Of course. What is on your mind?"),
    )
    thread = await start(alice)
    await past_the_opening(thread)
    await send(alice, thread.id, "my manager embarrassed me in front of everyone")
    await send(alice, thread.id, "Keep Chatting")

    assert scripted.last_messages[-1]["content"].endswith("[/ctx]\n\ntapped: Keep Chatting")


async def test_what_they_said_rules_out_is_told_and_nothing_else_names_it(alice, model):
    """Early grief rules Behavioral Activation out: the model is told so, and no other line names it."""
    scripted = model(Reply(text="What is it like at home without him?"))
    thread = await start(alice)
    await past_the_opening(thread)
    await send(alice, thread.id, "i stopped doing the things i enjoy since he died and i can't make myself start anything")

    sent = scripted.last_messages[-1]["content"].splitlines()
    assert "ruled_out: behavioral_activation" in sent
    assert not [line for line in sent if "behavioral_activation" in line and line != "ruled_out: behavioral_activation"]


BRIDGE = "That is a lot to weigh."


def _offer(technique: str) -> Reply:
    return Reply(
        text=BRIDGE,
        prompts=[SmartPrompt(label="Try It", technique=technique),
                 SmartPrompt(label="Keep Chatting", decline=True)],
        state=TechniqueState(technique=technique, step="offering"),
    )


OFFER_LABELS = ["Try It", "Tell Me More", "Keep Chatting"]


async def _filled(template: str, technique: str) -> str:
    framework = (await orchestrator.cache.load()).registry.get(technique)
    return template.format(name=framework.name, description=" ".join(framework.summary.split()))


async def _offer_turn(technique: str, answer: str = "") -> str:
    """An offer turn as the person sees it: the seeded offer, filled from the framework's own row,
    after the model's line only when that line answers a typed question about the offer."""
    seeded = await _filled(REPLIES.offer.text, technique)
    return f"{answer}\n\n{seeded}" if answer else seeded


async def _told_more(technique: str, style: str) -> str:
    """The reply to Tell me more: the framework's own text in that style when the row has it,
    otherwise the seeded line filled from the framework's own row."""
    styled = REPLIES.offer.by_framework.get(technique, {}).get(style)
    return styled.more_text if styled else await _filled(REPLIES.offer.more_text, technique)


def _stored_offer(technique: str) -> list[dict]:
    return [
        {"label": "Try It", "technique": technique},
        {"label": "Tell Me More", "more": True},
        {"label": "Keep Chatting", "decline": True},
    ]


@pytest.mark.parametrize("technique", ["structured_problem_solving", "abcde", "thought_reframe"])
async def test_an_offer_is_made_on_the_second_message_in_any_style(alice, model, technique):
    """muhammad, 2026-10-01: once Mani can tell what fits it should offer, not wait out the old
    four. No framework waits for a later message either: ABCDE's offer stands on the second.
    The model decides that it offers and which set; the words and the three buttons are the
    seeded offer's, and the model's own line is dropped."""
    scripted = model(
        Reply(text="What is the hardest part of it?", heading_toward=technique),
        _offer(technique),
    )
    thread = await start(alice)
    await _supportive(thread)
    await send(alice, thread.id, "i have an exam tomorrow and i don't know where to start")
    turn = await send(alice, thread.id, "i'm confused between studying everything or picking topics")

    assert scripted.calls == 2
    assert turn.content == await _offer_turn(technique)
    assert BRIDGE not in turn.content
    assert [p.label for p in turn.prompts] == OFFER_LABELS
    assert [p.technique for p in turn.prompts if p.technique] == [technique]
    stored = (await _history(alice, thread.id))[-1]
    assert (stored.content, stored.prompt_options) == (turn.content, _stored_offer(technique))


async def _in_style(thread, style: str):
    """The style tap and its opener, which the real greeting flow adds before their first message."""
    from mani.db import pool

    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.threads set conversation_style = $2, message_count = message_count + 2 "
            "where id = $1",
            thread.id, style,
        )


async def _supportive(thread):
    from mani.models.rows import SupportStyle

    await _in_style(thread, SupportStyle.SUPPORTIVE.value)


@pytest.mark.parametrize(
    ("technique", "style"),
    [("abcde", "direct"), ("abcde", "supportive"), ("abcde", "reflective"), ("thought_reframe", "reflective")],
)
async def test_an_offer_is_the_same_seeded_words_in_every_style(alice, model, technique, style):
    """muhammad, 2026-10-09: every set, ABCDE included, is offered in the shared seeded words
    whatever the thread's style; only Tell me more follows the style."""
    scripted = model(_offer(technique))
    thread = await past_the_opening(await start(alice))
    await _in_style(thread, style)
    turn = await send(alice, thread.id, "my manager criticised me in front of everyone")

    assert scripted.calls == 1
    assert turn.content == await _offer_turn(technique)
    assert [p.label for p in turn.prompts] == OFFER_LABELS
    stored = (await _history(alice, thread.id))[-1]
    assert (stored.content, stored.prompt_options) == (turn.content, _stored_offer(technique))


@pytest.mark.parametrize(
    ("profile_style", "expected"),
    [(None, TUNING.offers.default_style), ("direct", "direct")],
    ids=["no style anywhere", "the profile's style"],
)
async def test_a_thread_with_no_style_offers_in_the_profile_style_then_the_default(
    alice, model, profile_style, expected
):
    """covers: AC-4 - Tell me more takes the style [ctx] names: the thread's, then the profile's,
    then the tuning default."""
    from mani.db import pool

    model(_offer("abcde"))
    thread = await past_the_opening(await start(alice))
    if profile_style:
        async with pool.as_user(alice) as conn:
            await profiles.upsert(conn, ALICE, support_style=profile_style)
    offered = await send(alice, thread.id, "my manager criticised me in front of everyone")
    explained = await send(alice, thread.id, "Tell Me More")

    assert offered.content == await _offer_turn("abcde")
    assert explained.content == await _told_more("abcde", expected)


async def test_a_plain_sentence_is_offerable_at_the_second_message_and_logged_by_id_only(
    alice, model, caplog
):
    """covers: AC-1, AC-8 - no phrase from any list is in these words, and the offer is stored and
    logged all the same, by id and one flag, never a word of what was said."""
    scripted = model(Reply(text="What has that been like?"), _offer("behavioral_activation"))
    thread = await start(alice)
    await _supportive(thread)
    await send(alice, thread.id, "I've been avoiding my friends because I've been overwhelmed")
    first = scripted.last_messages[-1]["content"].splitlines()
    with caplog.at_level("INFO", logger="mani.chat.orchestrator"):
        turn = await send(alice, thread.id, "and I feel guilty about ignoring them")
    second = scripted.last_messages[-1]["content"].splitlines()

    assert "cooldown_passed: yes" in second
    assert not [line for line in first + second if line.startswith("framework_shortlist")]
    assert [p.technique for p in turn.prompts if p.technique] == ["behavioral_activation"]
    offers = [r.getMessage() for r in caplog.records if r.getMessage().startswith("offer on thread")]
    assert offers == [f"offer on thread {thread.id}: behavioral_activation cooldown_passed: yes"]
    assert "avoiding my friends" not in caplog.text


async def test_the_turn_is_stored_and_the_thread_state_follows_it(alice, model):
    """An offer with a blank line of the model's own falls back to the seeded offer alone. Its
    shape is not recorded: it describes a reply, not the text the person saw."""
    model(
        Reply(text="What has been the heaviest part?", style=Style(shape="warmth lead")),
        Reply(
            text="",
            prompts=[
                SmartPrompt(label="Try It", technique="abcde"),
                SmartPrompt(label="Not right now", decline=True),
            ],
            state=TechniqueState(technique="abcde", step="offering"),
            style=Style(shape="mirror and ask"),
        ),
    )
    from mani.db import pool

    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "everything feels like too much")
    turn = await send(alice, thread.id, "work, mostly")

    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE, STYLE_WINDOW)

    assert turn.content == await _offer_turn("abcde")
    assert ctx.technique.framework_id == "abcde"
    assert ctx.technique.outcome is TechniqueOutcome.OFFERED
    assert ctx.techniques_offered == ["abcde"]
    assert [style.shape for style in ctx.recent_styles] == ["warmth lead"]
    assert [m.role for m in (await _history(alice, thread.id))][-2:] == ["user", "mani"]


async def test_tapping_the_offer_records_acceptance(alice, model):
    scripted = model(
        Reply(
            text="Want to try something?",
            prompts=[SmartPrompt(label="Let's do it", technique="abcde")],
            state=TechniqueState(technique="abcde", step="offering"),
        ),
        Reply(
            text="Good. What happened first?",
            state=TechniqueState(technique="abcde", step="activating_event"),
        ),
    )
    from mani.db import pool

    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "I keep spiralling")
    # The seeded label, tapped in another case: the label the model wrote is never shown.
    await send(alice, thread.id, "try IT")

    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE, STYLE_WINDOW)

    assert ctx.technique.outcome is TechniqueOutcome.ACCEPTED
    assert ctx.technique.phase == "activating_event"
    # So the first stage builds on what they already said instead of asking it again.
    assert "framework_starting: yes" in scripted.last_messages[-1]["content"]


async def test_tell_me_more_is_answered_with_no_model_call_and_the_offer_stays_open(alice, model):
    """covers: AC-3, AC-4, AC-5 - the reply is the framework's own steps in the thread's style, and
    Try It after it is the ordinary accept: one model call, on the first stage."""
    scripted = model(
        _offer("abcde"),
        Reply(text="What happened first?", state=_abcde_state("activating_event", activating_event="partial")),
    )
    thread = await past_the_opening(await start(alice))
    await _in_style(thread, "reflective")
    await send(alice, thread.id, "my manager criticised me in front of everyone")
    asked = scripted.calls

    turn = await send(alice, thread.id, "tell me MORE")

    assert scripted.calls == asked
    assert turn.content == await _told_more("abcde", "reflective")
    assert [p.label for p in turn.prompts] == ["Try It", "Keep Chatting"]
    assert (turn.llm_call_id, turn.needs_summary, turn.was_duplicate) == (None, False, False)
    assert turn.crisis_blocks_chat is get_settings().crisis_blocks_chat
    history = await _history(alice, thread.id)
    assert [m.selected_prompt for m in history if m.selected_prompt] == ["Tell Me More"]
    assert history[-1].prompt_options == [
        {"label": "Try It", "technique": "abcde"},
        {"label": "Keep Chatting", "decline": True},
    ]
    row = await _state_row(thread.id)
    assert (row["outcome"], row["phase"]) == ("offered", "offering")

    await send(alice, thread.id, "Try It")

    assert scripted.calls == asked + 1
    row = await _state_row(thread.id)
    assert (row["outcome"], row["phase"]) == ("accepted", "activating_event")


async def test_finishing_a_technique_retires_it_without_losing_the_turn(alice, model):
    """The turn after a technique lands is the normal successful path, not an edge case.

    Retiring the row is an UPDATE inside the turn's one transaction: if it is refused,
    the user's message and Mani's reply go down with it. The row has to survive, because
    at_message_count is what the next turn's cooldown is measured from.
    """
    model(Reply(text="How has the rest of the week been?", ending="choice"))
    from mani.db import pool

    thread = await start(alice)
    # The phase clamp only advances one step per turn, so the landed state is set
    # directly rather than walked through all six of abcde's phases.
    async with pool.as_user(alice) as conn:
        await threads.set_technique_outcome(
            conn, thread.id, ALICE, "abcde", TechniqueOutcome.ACCEPTED,
            at_message_count=2, phase="somatic_practice",
        )

    turn = await send(alice, thread.id, "that helped, thanks")

    assert turn.content == "How has the rest of the week been?"
    assert [(p.label, p.library) for p in turn.prompts] == [
        ("Chat More", None), ("Go to Library", "home"),
    ]

    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE, STYLE_WINDOW)

    # Retired, not deleted: the framework is finished but the thread remembers running it.
    assert ctx.technique is not None
    assert ctx.technique.phase is None
    assert ctx.technique.outcome is TechniqueOutcome.ACCEPTED
    assert ctx.technique.at_message_count == 2
    assert ctx.technique.ending_from is None
    assert "cooldown_passed: no" in context.build(ctx, replies=REPLIES, tuning=TUNING)
    assert [m.role for m in (await _history(alice, thread.id))][-2:] == ["user", "mani"]


async def test_an_offer_button_on_the_turn_that_retires_a_framework_cannot_cancel_the_retirement(
    alice, model
):
    """The offer's OFFERED row would be written over the retirement, so the finished framework
    would be running again. The model's offer goes, and the two choices are the only buttons."""
    model(Reply(
        text="That is a good place to stop. Want to try another?",
        prompts=[SmartPrompt(label="Try It", technique="thought_reframe"),
                 SmartPrompt(label="Keep Chatting", decline=True)],
        state=TechniqueState(technique="abcde", step="somatic_practice"),
        ending="choice",
    ))
    from mani.db import pool

    thread = await start(alice)
    await _land_on(alice, thread.id, "somatic_practice")

    turn = await send(alice, thread.id, "that helped, thanks")

    assert [p.label for p in turn.prompts] == ["Chat More", "Go to Library"]
    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE, STYLE_WINDOW)
    assert (ctx.technique.framework_id, ctx.technique.phase) == ("abcde", None)
    assert ctx.technique.outcome is TechniqueOutcome.ACCEPTED


async def test_a_library_button_from_the_model_does_not_silence_the_library_offer(alice, model):
    """Only the two choices the orchestrator writes at the end of a framework count as the library
    having been offered, so a stray library button mid framework leaves it still pending."""
    scripted = model(
        Reply(
            text="What happened right before that?",
            prompts=[SmartPrompt(label="Go to Library", library="home")],
            state=TechniqueState(technique="abcde", step="belief"),
        ),
        Reply(text="And what did you tell yourself then?",
              state=TechniqueState(technique="abcde", step="belief")),
    )
    from mani.db import pool

    thread = await start(alice)
    async with pool.as_user(alice) as conn:
        await threads.set_technique_outcome(
            conn, thread.id, ALICE, "abcde", TechniqueOutcome.ACCEPTED,
            at_message_count=2, phase="belief",
        )

    await send(alice, thread.id, "she ignored my message")
    await send(alice, thread.id, "I thought I was being a burden")

    assert "library_pending: yes" in scripted.last_messages[-1]["content"].splitlines()


ABCDE_STAGES = ["activating_event", "belief", "consequences", "dispute", "effective_new_belief"]


def _known_before(phase: str) -> dict[str, LedgerEntry]:
    """The ledger a thread on `phase` holds: every ABCDE stage before it known, and all of them from
    the last own phase on, so the stored stage is the one the ledger gives."""
    before = ABCDE_STAGES[: ABCDE_STAGES.index(phase)] if phase in ABCDE_STAGES else ABCDE_STAGES
    return {stage: LedgerEntry(status=StageStatus.KNOWN) for stage in before}


async def _land_on(alice, thread_id, phase, stage_ledger=None) -> None:
    from mani.db import pool

    async with pool.as_user(alice) as conn:
        await threads.apply(conn, thread_id, ALICE, threads.ThreadUpdates(technique=rows.TechniqueState(
            thread_id=thread_id, framework_id="abcde", outcome=TechniqueOutcome.ACCEPTED,
            at_message_count=2, phase=phase,
            stage_ledger=_known_before(phase) if stage_ledger is None else stage_ledger,
        )))


async def _retire_abcde_on(alice, thread_id) -> None:
    """Land a thread on ABCDE's last ending phase, so a reply that sets `ending` completes it."""
    await _land_on(alice, thread_id, "somatic_practice")


@pytest.fixture
async def abcde_exercise(alice):
    """One exercise that names abcde, for the turns where the hand-off should fire.

    A fixture rather than seed content: the real catalog is empty, and the mechanism has
    to be provable before there is anything real in it.
    """
    from mani.db import pool

    async with pool.as_admin() as conn:
        exercise_id = await conn.fetchval(
            "insert into admin.exercises (title, category, audio_path, framework_id) "
            "values ('Settling after ABCDE', 'grounding', 'abcde/settle.mp3', 'abcde') "
            "returning id"
        )
    try:
        yield exercise_id
    finally:
        async with pool.as_admin() as conn:
            await conn.execute("delete from admin.exercises where id = $1", exercise_id)


@pytest.fixture
async def library_exercise(alice):
    """An ordinary library exercise, linked to no framework."""
    from mani.db import pool

    async with pool.as_admin() as conn:
        exercise_id = await conn.fetchval(
            "insert into admin.exercises (title, type, category, audio_path) "
            "values ('Unwinding', 'Breathing', 'Burnout', 'test-unwinding.mp3') returning id"
        )
    try:
        yield exercise_id
    finally:
        async with pool.as_admin() as conn:
            await conn.execute("delete from admin.exercises where id = $1", exercise_id)


@pytest.fixture
async def empty_catalog(alice):
    """Hide the seeded catalog for one test, and put back exactly what was hidden."""
    from mani.db import pool

    async with pool.as_admin() as conn:
        hidden = await conn.fetch(
            "update admin.exercises set is_active = false where is_active returning id"
        )
    try:
        yield
    finally:
        async with pool.as_admin() as conn:
            await conn.execute(
                "update admin.exercises set is_active = true where id = any($1::uuid[])",
                [r["id"] for r in hidden],
            )


async def test_a_completing_framework_with_an_empty_catalog_still_costs_one_call(
    alice, model, monkeypatch, empty_catalog
):
    """With nothing in the catalog the hand-off's second call never happens, and a
    completing turn costs exactly what every other turn costs."""
    scripted = model(Reply(text="How has the rest of the week been?", ending="choice"))
    chooser = ScriptedChooser()
    monkeypatch.setattr(orchestrator.client, "choose_exercise", chooser)

    thread = await start(alice)
    await _retire_abcde_on(alice, thread.id)

    turn = await send(alice, thread.id, "that helped, thanks")

    assert scripted.calls == 1
    assert chooser.calls == 0
    assert turn.exercise is None


async def test_a_completing_framework_hands_off_to_its_exercise(
    alice, model, monkeypatch, abcde_exercise
):
    """With something in the catalog for that framework, the turn spends a second call -
    a bound tool call - and the reply carries the exercise it chose."""
    scripted = model(Reply(text="How has the rest of the week been?", ending="choice"))
    chooser = ScriptedChooser()
    monkeypatch.setattr(orchestrator.client, "choose_exercise", chooser)

    thread = await start(alice)
    await _retire_abcde_on(alice, thread.id)

    turn = await send(alice, thread.id, "that helped, thanks")

    assert scripted.calls == 1
    assert chooser.calls == 1
    assert chooser.kwargs["purpose"] is llm_calls.Purpose.EXERCISE_SELECT
    assert turn.exercise is not None
    assert turn.exercise.id == abcde_exercise
    assert turn.exercise.framework_id == "abcde"


async def test_the_hand_off_chooses_from_the_whole_catalog_for_this_conversation(
    alice, model, monkeypatch, abcde_exercise, library_exercise
):
    """Every active exercise is a candidate, the framework's own listed first, and the
    chooser sees what the person just said - so a library exercise can win on fit."""
    model(Reply(text="How has the rest of the week been?", ending="choice"))
    chooser = ScriptedChooser(chosen=str(library_exercise))
    monkeypatch.setattr(orchestrator.client, "choose_exercise", chooser)

    thread = await start(alice)
    await _retire_abcde_on(alice, thread.id)

    turn = await send(alice, thread.id, "that helped, thanks")

    ids = [c["id"] for c in chooser.candidates]
    assert ids[0] == str(abcde_exercise)
    assert str(library_exercise) in ids
    assert {"type": "Breathing", "category": "Burnout"}.items() <= next(
        c for c in chooser.candidates if c["id"] == str(library_exercise)
    ).items()
    assert chooser.kwargs["said"][-1] == "that helped, thanks"
    assert turn.exercise is not None
    assert turn.exercise.id == library_exercise


async def test_an_ordinary_turn_never_reaches_the_exercise_hand_off(
    alice, model, monkeypatch, abcde_exercise
):
    """The second call is scoped to a completing framework, not to having a catalog."""
    model(Reply(text="Tell me more about that."))
    chooser = ScriptedChooser()
    monkeypatch.setattr(orchestrator.client, "choose_exercise", chooser)

    thread = await start(alice)
    turn = await send(alice, thread.id, "I had a hard day")

    assert chooser.calls == 0
    assert turn.exercise is None


async def serve_with_row(monkeypatch, name: str, **changes) -> None:
    """Serve the seeded configuration with one prompt row changed, as a portal edit would."""
    config = await orchestrator.cache.load()
    changed = config.prompts[name].model_copy(update=changes)
    served = dataclasses.replace(config, prompts={**config.prompts, name: changed})

    async def load():
        return served

    monkeypatch.setattr(orchestrator.cache, "load", load)


async def test_an_exercise_row_with_no_level_offers_the_first_candidate_without_a_pick(
    alice, model, monkeypatch, abcde_exercise, caplog
):
    """The reply is already built when the pick runs, so a broken exercise_select row costs
    the pick and not the turn, and nothing is sent at a level nobody chose."""
    model(Reply(text="How has the rest of the week been?", ending="choice"))
    chooser = ScriptedChooser()
    monkeypatch.setattr(orchestrator.client, "choose_exercise", chooser)
    await serve_with_row(monkeypatch, "exercise_select", model_parameters={"maxTokens": 200})

    thread = await start(alice)
    await _retire_abcde_on(alice, thread.id)
    with caplog.at_level(logging.WARNING, logger="mani.chat.orchestrator"):
        turn = await send(alice, thread.id, "that helped, thanks")

    assert chooser.calls == 0
    assert turn.exercise is not None
    assert turn.exercise.id == abcde_exercise
    assert "exercise_select" in caplog.text


async def test_the_chat_turn_thinks_at_the_level_its_row_names(alice, model, monkeypatch):
    """Every seeded row says high, so only a changed row shows the level is read, not assumed."""
    scripted = model(Reply(text="Tell me more about that."))
    thread = await start(alice)
    await serve_with_row(monkeypatch, "mani_base", model_parameters={"reasoning_effort": "low"})

    await send(alice, thread.id, "I had a hard day")

    assert scripted.last_kwargs["reasoning_effort"] == "low"


async def test_a_chat_row_with_no_level_refuses_the_turn_before_the_model_is_asked(
    alice, model, monkeypatch
):
    """A config error, not a call at some default level: no tokens are spent finding out."""
    scripted = model(Reply(text="Tell me more about that."))
    thread = await start(alice)
    await serve_with_row(monkeypatch, "mani_base", model_parameters={})

    with pytest.raises(ServiceError) as refused:
        await send(alice, thread.id, "I had a hard day")

    assert refused.value.category is ErrorCategory.CONFIG_ERROR
    assert scripted.calls == 0


async def test_the_exercise_pick_sends_what_its_own_row_names(
    alice, model, monkeypatch, abcde_exercise
):
    """Model, thinking level, budget and routing are the exercise_select row's, and the seeded
    row asks for exactly what the pick sent when it borrowed the chat turn's settings."""
    sent: dict = {}

    class Bound:
        async def ainvoke(self, messages):
            sent["messages"] = messages
            call = {"name": "StartExercise", "args": {"exercise_id": str(abcde_exercise)}, "id": "1"}
            return SimpleNamespace(tool_calls=[call], usage_metadata={}, response_metadata={})

    real_model = chain._model

    def spy(*configuration):
        sent["model"] = configuration[3]
        sent["extra_body"] = json.loads(configuration[-1])
        sent["params"] = real_model(*configuration)._default_params
        return SimpleNamespace(bind_tools=lambda tools, tool_choice: Bound())

    monkeypatch.setattr(chain, "_model", spy)
    monkeypatch.setattr(get_settings(), "openrouter_api_key", "sk-test-not-a-real-key")
    monkeypatch.setattr(orchestrator.client, "choose_exercise", REAL_CHOOSE_EXERCISE)
    model(Reply(text="How has the rest of the week been?", ending="choice"))

    thread = await start(alice)
    await _retire_abcde_on(alice, thread.id)
    turn = await send(alice, thread.id, "that helped, thanks")

    row = (await orchestrator.cache.load()).prompts["exercise_select"]
    assert turn.exercise is not None
    assert turn.exercise.id == abcde_exercise
    assert sent["messages"][0]["content"].startswith(row.content)
    assert sent["model"] == "openai/gpt-6-luna"
    assert sent["extra_body"]["reasoning"] == {"effort": "high"}
    assert sent["extra_body"]["provider"]["order"] == get_settings().openrouter_provider_order
    assert sent["extra_body"]["provider"]["data_collection"] == "deny"
    assert sent["params"]["max_completion_tokens"] == 200 + chain.REASONING_ALLOWANCE_TOKENS
    assert "temperature" not in sent["params"]


async def test_asking_about_an_offer_leaves_it_open(alice, model):
    """A question about the offer is answered and the offer made again, so it is still waiting
    for their answer - unlike carrying on past it, which is Keep Chatting."""
    model(
        Reply(
            text="Want to try something?",
            prompts=[SmartPrompt(label="Try It", technique="abcde")],
            state=TechniqueState(technique="abcde", step="offering"),
        ),
        Reply(
            text="We'd look at what happened and what you told yourself about it.",
            prompts=[SmartPrompt(label="Try It", technique="abcde"),
                     SmartPrompt(label="Keep Chatting", decline=True)],
            state=TechniqueState(technique="abcde", step="offering"),
        ),
    )
    from mani.db import pool

    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "I keep spiralling")
    turn = await send(alice, thread.id, "what would that involve?")

    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE, STYLE_WINDOW)

    assert ctx.technique.outcome is TechniqueOutcome.OFFERED
    # The reply carried the offer again, so it still waits. A typed question is the one case where
    # the model's line goes before the seeded offer: it is the answer to what they asked.
    assert turn.content == await _offer_turn(
        "abcde", "We'd look at what happened and what you told yourself about it."
    )
    assert [p.label for p in turn.prompts] == OFFER_LABELS


async def test_a_model_reported_crisis_does_not_lock_the_thread(alice, model):
    """The model's own crisis judgment no longer locks: a small model over-fires it on
    ordinary distress, pain, or injury. Only the deterministic screen locks. A model report
    is a non-locking concern - the reply stays in the model's words, no event is recorded,
    and the conversation the person came for is not cut off."""
    model(
        Reply(text="I hear you, and I'm right here with you.", crisis=Crisis(reason="hopelessness")),
        Reply(text="What has today been like?"),
    )
    from mani.db import pool

    thread = await start(alice)
    turn = await send(alice, thread.id, "there is no point in me being here")

    assert turn.crisis_detected is False
    assert turn.content != crisis.CRISIS_REPLY
    assert turn.content.strip()

    async with pool.as_admin() as conn:
        event = await conn.fetchrow(
            "select reason from admin.crisis_events where thread_id = $1", thread.id
        )
    assert event is None

    # The thread is not locked, so a following turn is answered normally.
    again = await send(alice, thread.id, "I guess I am still here")
    assert again.crisis_detected is False
    assert again.content.strip()


async def test_an_offer_a_safety_concern_drops_goes_out_in_the_models_words(alice, model):
    written = "That sounds like a lot to carry. Are you safe right now?"
    model(Reply(**{**_offer("abcde").model_dump(), "text": written,
                   "crisis": Crisis(reason="hopelessness")}))
    thread = await past_the_opening(await start(alice))

    turn = await send(alice, thread.id, "I can't see the point of any of it")

    assert turn.content == written
    assert turn.prompts == []


async def test_the_safety_screen_locks_a_thread_with_no_provider_call(alice, model):
    """An explicit statement is caught before the model is ever asked anything - the
    scripted model has no reply queued, so a call here would raise, not just cost extra."""
    from mani.db import pool

    scripted = model()
    thread = await start(alice)
    turn = await send(alice, thread.id, "I am going to kill myself tonight.")

    assert scripted.calls == 0
    assert turn.crisis_detected is True
    assert turn.content.strip()

    async with pool.as_admin() as conn:
        event = await conn.fetchrow(
            "select reason from admin.crisis_events where thread_id = $1", thread.id
        )
    assert event["reason"] == "safety screen: suicide"


async def test_a_framework_completing_on_a_crisis_turn_is_still_retired(alice, model):
    """A crisis turn makes no model call, so no `ending` can come: a framework in its ending is
    retired here or never, and the thread locks one way, so nothing would correct it later."""
    from mani.db import pool

    thread = await start(alice)
    await _retire_abcde_on(alice, thread.id)

    turn = await send(alice, thread.id, "I am going to kill myself tonight.")
    assert turn.crisis_detected is True

    # The thread is locked, so the snapshot is read as admin rather than through a turn.
    async with pool.as_admin() as conn:
        row = await conn.fetchrow(
            "select phase, outcome from public.thread_technique_state where thread_id = $1",
            thread.id,
        )
    assert row["phase"] is None
    assert row["outcome"] == TechniqueOutcome.ACCEPTED


async def test_a_clear_wish_to_die_locks_before_any_call(alice, model):
    """"I want to die" is a clear wish to die, so the deterministic screen locks it before the
    model is ever asked - the sole locking authority, not the model. The scripted model has no
    reply queued, so a call here would raise rather than just cost extra."""
    from mani.db import pool

    scripted = model()
    thread = await start(alice)
    turn = await send(alice, thread.id, "I want to die")

    assert scripted.calls == 0
    assert turn.crisis_detected is True
    assert turn.llm_call_id is None

    async with pool.as_admin() as conn:
        event = await conn.fetchrow(
            "select reason from admin.crisis_events where thread_id = $1", thread.id
        )
    assert event["reason"] == "safety screen: suicide"


async def test_a_crisis_thread_refuses_another_turn(alice, model):
    # A deterministic crisis locks the thread; the model is never called for the first turn.
    model()
    thread = await start(alice)
    await send(alice, thread.id, "I want to die")

    from mani.errors import ServiceError

    with pytest.raises(ServiceError):
        await send(alice, thread.id, "are you there")


async def test_a_retried_send_returns_the_first_reply_without_paying_again(alice, model):
    scripted = model(Reply(text="I'm here. What happened?"), Reply(text="A different answer."))
    thread = await start(alice)
    client_id = uuid.uuid4()

    first = await send(alice, thread.id, "hello", client_message_id=client_id)
    again = await send(alice, thread.id, "hello", client_message_id=client_id)

    assert scripted.calls == 1
    assert again.was_duplicate is True
    assert again.content == first.content


async def test_a_title_is_written_once_the_thread_has_an_exchange(alice, model):
    """`message_count == 3` exactly was the reference's gate; one crisis turn writes a
    single message, moved the count past it, and the thread was never titled."""
    model(
        Reply(text="Go on."),
        Reply(text="I see.", title='"Replaying a hard day at work."'),
    )
    from mani.db import pool

    thread = await start(alice)
    await send(alice, thread.id, "work was hard")
    turn = await send(alice, thread.id, "I keep replaying it")

    assert turn.title == "Replaying a hard day at work"
    async with pool.as_user(alice) as conn:
        assert (await threads.get(conn, thread.id, ALICE)).title == turn.title


async def test_starting_a_chat_twice_reuses_the_untouched_thread(alice):
    """Tapping "new chat" repeatedly used to leave a trail of empty threads."""
    from mani.db import pool

    async with pool.as_user(alice) as conn:
        first, created_first = await orchestrator.start_thread(conn, alice)
        second, created_second = await orchestrator.start_thread(conn, alice)

    assert second.id == first.id
    assert created_first is True and created_second is False

    async with pool.as_user(alice) as conn:
        history = await messages_db.recent_for_context(conn, first.id, ALICE, CONTEXT_WINDOW)
    assert len(history) == 1, "a reused thread must not get a second greeting"


async def test_starting_a_chat_after_speaking_makes_a_new_one(alice, model):
    model(Reply(text="Go on."))
    from mani.db import pool

    first = await start(alice)
    await send(alice, first.id, "work was hard")

    async with pool.as_user(alice) as conn:
        second, created = await orchestrator.start_thread(conn, alice)

    assert second.id != first.id and created is True


async def test_buttons_are_returned_only_on_manis_newest_message(alice, model):
    """Buttons are presentation, not history. The reference kept them on old rows and
    cleaned up with an UPDATE, so a failed write left stale offers tappable."""
    model(
        Reply(
            text="Want to try something?",
            prompts=[SmartPrompt(label="Try It", technique="abcde")],
        ),
        Reply(text="Good. What happened first?"),
    )
    from mani.db import pool
    from mani.routers.serializers import to_messages

    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "I keep spiralling")
    await send(alice, thread.id, "Try It")

    async with pool.as_user(alice) as conn:
        history = await messages_db.recent_for_context(conn, thread.id, ALICE, CONTEXT_WINDOW)
        live = await messages_db.latest_mani_id(conn, thread.id, ALICE)

    rendered = to_messages(history, live)
    offered = next(m for m in history if any(o.get("technique") for o in m.prompt_options or []))
    offer = next(m for m in rendered if m.id == offered.id)
    newest = rendered[-1]

    assert newest.id == live and newest.content == "Good. What happened first?"
    assert offer.prompts == [], "an answered offer must not stay tappable"
    assert [m for m in rendered if m.prompts] == []
    # What the person chose stays in the record even once the offer is gone.
    assert [m.selected_prompt for m in rendered if m.selected_prompt] == [
        "Try It"
    ]


async def test_a_failed_summary_is_logged_and_does_not_break_the_thread(
    alice, model, monkeypatch, caplog
):
    """Summarization is allowed to fail - it costs Mani some memory, not a reply. The
    swallow must leave a trace, or a silently dead summary looks like working code."""
    from mani import summarize

    model(Reply(text="Go on."))
    thread = await start(alice)
    await send(alice, thread.id, "work was hard")

    async def explode(*_args, **_kwargs):
        raise RuntimeError("provider is down")

    monkeypatch.setattr(summarize, "update", explode)
    with caplog.at_level("ERROR"):
        await summarize.update_quietly(alice, thread.id)

    assert "summarization failed" in caplog.text
    assert [m.content for m in await _history(alice, thread.id)][-1] == "Go on."


async def _history(claims: Claims, thread_id):
    from mani.db import pool

    async with pool.as_user(claims) as conn:
        return await messages_db.recent_for_context(conn, thread_id, ALICE, CONTEXT_WINDOW)


async def test_a_concern_pauses_a_running_framework_for_that_turn(alice, model):
    """The specification: avoid continuing the framework until the safety concern has been
    addressed. The model is told, gets no stage question to ask, and cannot advance or open
    a framework on this turn - the framework resumes where it stood once the concern passes."""
    scripted = model(
        Reply(
            text="Thank you for telling me. I'm with you.",
            prompts=[SmartPrompt(label="Try this", technique="thought_reframe")],
            state=TechniqueState(technique="abcde", step="consequences"),
        )
    )
    from mani.db import pool

    thread = await start(alice)
    async with pool.as_user(alice) as conn:
        await threads.set_technique_outcome(
            conn, thread.id, ALICE, "abcde", TechniqueOutcome.ACCEPTED,
            at_message_count=2, phase="belief",
        )

    turn = await send(alice, thread.id, "honestly I don’t want to be here anymore")

    sent = scripted.last_messages[-1]["content"]
    assert "safety: concern" in sent
    assert "active_framework" not in sent
    assert not any(line.startswith(("stage", "next_stage")) for line in sent.splitlines())
    assert not any(p.technique for p in turn.prompts)

    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE, STYLE_WINDOW)
    assert ctx.technique.phase == "belief"


async def test_a_new_chat_after_a_crisis_carries_the_flag_but_not_the_lock(alice, model):
    """New chat must not become a way round the crisis path, and must not lock someone out
    either: the next conversation opens, and the model is told to stay gentle and near
    support. What was said is never carried across - only that it happened."""
    scripted = model(Reply(text="I'm glad you came back. What is on your mind?"))
    from mani.db import pool

    first = await start(alice)
    await send(alice, first.id, "I am going to kill myself")  # the screen locks this thread

    async with pool.as_user(alice) as conn:
        second, created = await threads.create_or_reuse(conn, ALICE)
    assert created and second.id != first.id

    await send(alice, second.id, "hi again")
    assert "recent_crisis: yes" in scripted.last_messages[-1]["content"]


async def test_a_finished_framework_no_longer_counts_as_running(alice, model):
    """Retired means finished. The row stays so the cooldown can be measured from it, but it
    must not keep stripping every later technique button as though the framework were live."""
    model(
        Reply(
            text="Would you like to try another way of looking at it?",
            prompts=[SmartPrompt(label="Yes, let's try", technique="thought_reframe")],
            state=TechniqueState(technique="thought_reframe", step="offering"),
        )
    )
    from mani.db import pool

    thread = await start(alice)
    async with pool.as_user(alice) as conn:
        await threads.set_technique_outcome(
            # Finished long enough ago that the cooldown has passed: what this checks is that
            # the finished row no longer blocks offers, not the cooldown itself.
            conn, thread.id, ALICE, "abcde", TechniqueOutcome.ACCEPTED,
            at_message_count=-TUNING.offers.cooldown_after_complete, phase=None,
        )

    turn = await send(alice, thread.id, "something else happened today")
    assert [p.technique for p in turn.prompts if p.technique] == ["thought_reframe"]


async def test_tapping_decline_records_it_even_when_the_model_reports_no_state(alice, model):
    """After a decline there is no technique to report, so state: null is the model doing
    what the schema asks. The decline is the button's meaning, not the model's to confirm."""
    model(
        Reply(
            text="Want to try something?",
            prompts=[SmartPrompt(label="Try It", technique="abcde"),
                     SmartPrompt(label="Not right now", decline=True)],
            state=TechniqueState(technique="abcde", step="offering"),
        ),
        Reply(text="That's fine. What would help most right now?"),
    )
    from mani.db import pool

    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "I keep spiralling")
    await send(alice, thread.id, "Not right now")

    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE, STYLE_WINDOW)
    assert ctx.technique.outcome is TechniqueOutcome.DECLINED
    assert "active_framework" not in context.build(ctx, replies=REPLIES, tuning=TUNING)


async def test_an_empty_reply_fails_cleanly_and_stores_nothing(alice, model):
    """A reply with no words must fail as a retryable turn, not reach the
    messages_content_not_empty constraint as a 500."""
    model(Reply(text="  \n"))
    from mani.errors import ServiceError

    thread = await start(alice)
    with pytest.raises(ServiceError) as raised:
        await send(alice, thread.id, "hello")
    assert raised.value.retryable
    assert [m.role for m in await _history(alice, thread.id)] == ["mani"]  # the greeting only


async def test_an_imminent_action_waits_for_the_second_message_like_any_set(alice, model):
    """DBT STOP has no urgent case: a first message about an action about to be taken gets the same
    cooldown as every other, so nothing is offerable on it."""
    scripted = model(Reply(text="Before you send it, can we pause for a moment?"))
    thread = await start(alice)
    await send(alice, thread.id, "I am about to send a message I will regret")

    sent = scripted.last_messages[-1]["content"].splitlines()
    assert "cooldown_passed: no" in sent
    assert not [line for line in sent if line.startswith("framework_shortlist")]


async def test_a_new_chat_asks_how_the_person_wants_to_be_spoken_to(alice):
    thread = await start(alice)
    [first] = await _history(alice, thread.id)
    assert first.content == "Hi Al. It's MANI. How would you like me to speak with you today?"
    assert [o["label"] for o in first.prompt_options] == ["Directive", "Supportive", "Reflective"]


async def test_choosing_a_style_sets_it_and_opens_in_it_with_no_model_call(alice, model):
    """The client's cadence: greeting, style selection, then that style's opening question.
    The opener is fixed wording from the spec, so it costs nothing to say."""
    scripted = model(Reply(text="What is happening for you?"))
    from mani.db import pool

    thread = await start(alice)
    turn = await send(alice, thread.id, "Reflective")

    assert turn.content == "What's on your mind today?"
    assert turn.prompts == []
    assert scripted.calls == 0
    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE, STYLE_WINDOW)
    assert ctx.thread.conversation_style.value == "reflective"

    await send(alice, thread.id, "I keep going over an argument with my sister")
    assert "conversation_style: reflective" in scripted.last_messages[-1]["content"]


async def test_the_same_message_sent_twice_at_once_is_answered_and_paid_for_once(alice, model):
    """A mobile client retrying while the first request is still waiting on the model. Both
    used to pass the duplicate check, both paid for a generation, and the second returned a
    reply that was never stored."""
    import asyncio

    scripted = model(Reply(text="What has been the hardest part?"))
    real = orchestrator.client.complete

    async def slow(*args, **kwargs):
        await asyncio.sleep(0.3)  # long enough that the second request arrives mid-call
        return await real(*args, **kwargs)

    orchestrator.client.complete = slow
    try:
        thread = await start(alice)
        client_message_id = uuid.uuid4()
        first, second = await asyncio.gather(
            send(alice, thread.id, "work has been hard lately", client_message_id=client_message_id),
            send(alice, thread.id, "work has been hard lately", client_message_id=client_message_id),
        )
    finally:
        orchestrator.client.complete = real

    assert scripted.calls == 1
    assert first.message_id == second.message_id
    assert first.content == second.content


async def test_a_message_id_reused_in_another_chat_is_refused_not_answered(alice, model):
    """The key is per person, so a reuse in a second chat used to return the first chat's
    reply - a message from another conversation, and nothing written where it was sent."""
    from mani.errors import ErrorCategory, ServiceError

    model(Reply(text="What has been the hardest part?"))
    first_chat = await start(alice)
    client_message_id = uuid.uuid4()
    await send(alice, first_chat.id, "work has been hard lately", client_message_id=client_message_id)

    from mani.db import pool

    async with pool.as_user(alice) as conn:
        second_chat, _ = await threads.create_or_reuse(conn, ALICE)
    with pytest.raises(ServiceError) as refused:
        await send(alice, second_chat.id, "a different chat", client_message_id=client_message_id)
    assert refused.value.category is ErrorCategory.CONFLICT


async def test_two_summaries_started_together_pay_for_one(alice, monkeypatch):
    """A summary runs after the reply, in the background. A second message arriving before it
    has committed schedules another over the same messages - two generations, one kept."""
    import asyncio

    from mani import summarize
    from mani.llm.schema import Extraction

    calls = 0

    async def slow_summary(messages, schema, **kwargs):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.3)
        return client.Call(value=Extraction(summary="The user talked about work."),
                           call_id=uuid.uuid4())

    monkeypatch.setattr(orchestrator.client, "complete",
                        ScriptedModel(Reply(text="Go on.")))
    thread = await start(alice)
    await send(alice, thread.id, "work was hard")
    monkeypatch.setattr(summarize.client, "complete", slow_summary)

    await asyncio.gather(
        summarize.update_quietly(alice, thread.id), summarize.update_quietly(alice, thread.id)
    )
    assert calls == 1


async def test_past_the_daily_limit_a_turn_is_refused_before_anything_is_paid(
    alice, model, monkeypatch
):
    from mani.config import get_settings
    from mani.errors import ErrorCategory, ServiceError

    scripted = model(Reply(text="What has been the hardest part?"))
    monkeypatch.setattr(get_settings(), "daily_message_limit", 1)
    thread = await start(alice)
    await send(alice, thread.id, "work has been hard lately")

    with pytest.raises(ServiceError) as refused:
        await send(alice, thread.id, "and it's getting worse")
    assert refused.value.category is ErrorCategory.RATE_LIMITED
    assert scripted.calls == 1


async def test_a_crisis_is_still_answered_past_the_daily_limit(alice, model, monkeypatch):
    """The limit caps what can be spent, never whether someone in danger gets a reply: the
    safety screen runs first and answers with no model call at all."""
    from mani.config import get_settings

    model(Reply(text="What has been the hardest part?"))
    monkeypatch.setattr(get_settings(), "daily_message_limit", 1)
    thread = await start(alice)
    await send(alice, thread.id, "work has been hard lately")

    turn = await send(alice, thread.id, "I am going to kill myself")
    assert turn.crisis_detected


async def _state_row(thread_id) -> asyncpg.Record:
    from mani.db import pool

    async with pool.as_admin() as conn:
        return await conn.fetchrow(
            "select phase, outcome, ending_from, library_offered_since, stage_ledger "
            "from public.thread_technique_state where thread_id = $1",
            thread_id,
        )


async def _set_counts(thread_id, *, message_count: int, ending_from: int) -> None:
    from mani.db import pool

    async with pool.as_admin() as conn:
        await conn.execute(
            "update public.threads set message_count = $2 where id = $1", thread_id, message_count
        )
        await conn.execute(
            "update public.thread_technique_state set ending_from = $2 where thread_id = $1",
            thread_id, ending_from,
        )


def _ending(text: str, ending: str | None, step: str = "somatic_practice", **kwargs) -> Reply:
    return Reply(
        text=text, ending=ending, state=TechniqueState(technique="abcde", step=step), **kwargs
    )


async def test_a_choice_ends_the_framework_with_the_two_buttons_and_an_exercise(
    alice, model, monkeypatch, abcde_exercise
):
    """The model's own buttons never reach the person: the ending's two choices are written by
    the code, the state the same reply reports (a hold on somatic_practice) cannot write the
    framework back over its retirement, and the card is picked."""
    chooser = ScriptedChooser()
    monkeypatch.setattr(orchestrator.client, "choose_exercise", chooser)
    scripted = model(
        _ending("It is good you feel steadier. What would you like next?", "choice",
                prompts=[SmartPrompt(label="Something else")]),
        Reply(text="What is on your mind now?"),
    )
    thread = await start(alice)
    await _land_on(alice, thread.id, "somatic_practice")

    turn = await send(alice, thread.id, "my shoulders feel a bit looser")

    assert [(p.label, p.library) for p in turn.prompts] == [
        ("Chat More", None), ("Go to Library", "home"),
    ]
    assert chooser.calls == 1
    assert turn.exercise is not None
    row = await _state_row(thread.id)
    assert (row["phase"], row["ending_from"], row["library_offered_since"]) == (None, None, True)

    await send(alice, thread.id, "Chat More")
    sent = scripted.last_messages[-1]["content"].splitlines()
    assert "library_pending: yes" not in sent
    assert "conversation_phase: talking" in sent


@pytest.mark.parametrize("phase", ["somatic_practice", "somatic_checkin"])
async def test_keep_talking_ends_the_framework_with_no_buttons_and_no_exercise(
    alice, model, monkeypatch, abcde_exercise, phase
):
    """Someone who still feels bad, or declined the check feeling bad, is not handed a menu."""
    chooser = ScriptedChooser()
    monkeypatch.setattr(orchestrator.client, "choose_exercise", chooser)
    scripted = model(
        _ending("I am here. What is it that is still sitting with you?", "keep_talking", step=phase,
                prompts=[SmartPrompt(label="Chat More")]),
        Reply(text="Tell me more."),
    )
    thread = await start(alice)
    await _land_on(alice, thread.id, phase)

    turn = await send(alice, thread.id, "still not great honestly")

    assert turn.prompts == []
    assert turn.exercise is None
    assert chooser.calls == 0
    row = await _state_row(thread.id)
    assert (row["phase"], row["ending_from"], row["library_offered_since"]) == (None, None, True)

    await send(alice, thread.id, "it is my sister")
    sent = scripted.last_messages[-1]["content"].splitlines()
    assert "conversation_phase: talking" in sent
    assert "library_pending: yes" not in sent
    assert not any(line.startswith("active_framework") for line in sent)


async def test_a_declined_body_check_that_feels_fine_can_end_from_the_offer_stage(alice, model):
    model(_ending("Okay, that is fine.", "choice", step="somatic_checkin"))
    thread = await start(alice)
    await _land_on(alice, thread.id, "somatic_checkin")

    turn = await send(alice, thread.id, "no thanks, I feel fine")

    assert [p.label for p in turn.prompts] == ["Chat More", "Go to Library"]
    assert (await _state_row(thread.id))["phase"] is None


async def test_an_ending_the_model_sets_before_the_ending_is_open_changes_nothing(alice, model):
    model(Reply(text="What happened next?", ending="choice",
                state=TechniqueState(technique="abcde", step="belief")))
    thread = await start(alice)
    await _land_on(alice, thread.id, "belief")

    turn = await send(alice, thread.id, "she ignored my message")

    assert turn.prompts == []
    assert (await _state_row(thread.id))["phase"] == "belief"


async def test_a_reply_that_offers_the_body_check_is_not_also_the_end(alice, model):
    model(_ending("Would you like a short body check?", "choice", step="somatic_checkin"))
    thread = await start(alice)
    await _land_on(alice, thread.id, "closing")

    turn = await send(alice, thread.id, "yes, it feels a bit lighter")

    assert turn.prompts == []
    row = await _state_row(thread.id)
    assert row["phase"] == "somatic_checkin"
    assert row["outcome"] == TechniqueOutcome.ACCEPTED


@pytest.mark.parametrize("phase", ["closing", "somatic_checkin", "somatic_practice"])
async def test_the_model_sends_no_buttons_of_its_own_during_the_ending(alice, model, phase):
    model(_ending("Breathe in slowly. What do you notice?", None, step=phase,
                  prompts=[SmartPrompt(label="Chest"), SmartPrompt(label="Go to Library", library="home")]))
    thread = await start(alice)
    await _land_on(alice, thread.id, phase)

    turn = await send(alice, thread.id, "okay")

    assert turn.prompts == []


async def test_a_safety_concern_pauses_the_ending_instead_of_ending_it(alice, model):
    model(_ending("I am here with you. Tell me more about that.", "choice",
                  prompts=[SmartPrompt(label="Go to Library", library="home")]))
    thread = await start(alice)
    await _land_on(alice, thread.id, "somatic_practice")

    turn = await send(alice, thread.id, "I don\u2019t want to be here anymore")

    assert turn.crisis_detected is False
    assert turn.prompts == []
    row = await _state_row(thread.id)
    assert (row["phase"], row["outcome"]) == ("somatic_practice", TechniqueOutcome.ACCEPTED)


async def test_the_ending_starts_counting_once_and_a_step_back_cannot_restart_it(alice, model):
    from mani.db import pool

    model(
        _ending("Would you like a short body check?", None, step="somatic_checkin"),
        _ending("Breathe in for four. What do you notice?", None, step="somatic_practice"),
        _ending("Let us go back to how you feel. How is it now?", None, step="closing"),
        _ending("Glad it eased.", "choice", step="closing"),
    )
    thread = await start(alice)
    await _land_on(alice, thread.id, "closing")

    await send(alice, thread.id, "yes, a bit lighter")
    first = await _state_row(thread.id)
    async with pool.as_user(alice) as conn:
        count = (await threads.get(conn, thread.id, ALICE)).message_count
    assert first["ending_from"] == count

    await send(alice, thread.id, "yes please")
    assert (await _state_row(thread.id))["ending_from"] == first["ending_from"]
    await send(alice, thread.id, "I can see a lamp")
    stepped_back = await _state_row(thread.id)
    assert (stepped_back["phase"], stepped_back["ending_from"]) == ("closing", first["ending_from"])

    await send(alice, thread.id, "better now")
    assert (await _state_row(thread.id))["ending_from"] is None


async def test_a_framework_the_model_never_ends_retires_at_the_turn_cap_before_the_call(
    alice, model, monkeypatch, abcde_exercise
):
    chooser = ScriptedChooser()
    monkeypatch.setattr(orchestrator.client, "choose_exercise", chooser)
    scripted = model(_ending("Breathe in. What do you notice?", None,
                             prompts=[SmartPrompt(label="Chest")]))
    thread = await start(alice)
    await _land_on(alice, thread.id, "somatic_practice")
    await _set_counts(thread.id, message_count=30, ending_from=30 - 2 * TUNING.windows.ending_turn_cap)

    turn = await send(alice, thread.id, "I do not know")

    sent = scripted.last_messages[-1]["content"].splitlines()
    assert not any(line.startswith("active_framework") for line in sent)
    assert turn.prompts == []
    assert turn.exercise is None
    assert chooser.calls == 0
    row = await _state_row(thread.id)
    assert (row["phase"], row["ending_from"], row["library_offered_since"]) == (None, None, True)


async def test_one_turn_short_of_the_cap_the_ending_carries_on(alice, model):
    scripted = model(_ending("Breathe in. What do you notice?", None))
    thread = await start(alice)
    await _land_on(alice, thread.id, "somatic_practice")
    await _set_counts(thread.id, message_count=30, ending_from=30 - 2 * (TUNING.windows.ending_turn_cap - 1))

    await send(alice, thread.id, "I do not know")

    sent = scripted.last_messages[-1]["content"].splitlines()
    assert "active_framework: abcde" in sent
    assert (await _state_row(thread.id))["phase"] == "somatic_practice"


async def test_carrying_on_past_an_offer_is_i_want_to_keep_talking(alice, model):
    """muhammad, 2026-09-24: someone who types on without answering the offer has chosen to keep
    talking. Observed: "Would you like to try it?" came back on the very next reply, and the
    one after. A decline keeps no offer, so the reply goes out in the model's words."""
    offer = Reply(
        text="I have a sequence of questions that could help. Would you like to try it?",
        prompts=[SmartPrompt(label="Try It", technique="abcde"),
                 SmartPrompt(label="Tell me about this"),
                 SmartPrompt(label="Keep Chatting", decline=True)],
        state=TechniqueState(technique="abcde", step="offering"),
    )
    # What the model actually does: reports no answer either way, and makes the offer again.
    offered_again = offer.model_copy(update={
        "text": "You pick the phone back up. I have a sequence of questions that could help. "
                "Would you like to try it?",
    })
    model(offer, offered_again)
    from mani.db import pool

    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "my manager criticized me in front of everyone")
    turn = await send(alice, thread.id, "every time I try to start I pick the phone back up")

    # Its Try It and Keep Chatting went with the decline; a Tell me about this
    # answers nothing in particular and stays.
    assert [p.label for p in turn.prompts] == ["Tell me about this"]
    assert turn.content == offered_again.text
    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE, STYLE_WINDOW)
    assert ctx.technique.outcome is TechniqueOutcome.DECLINED


async def test_an_offer_they_typed_past_is_flagged_then_closed(alice, model):
    """The model is told, on the turn itself, that its offer is waiting and they typed instead;
    a reply that neither re-offers nor reports an answer has let it go, and so does the offer."""
    offer = Reply(
        text="I have a sequence of questions that could help. Would you like to try it?",
        prompts=[SmartPrompt(label="Try It", technique="abcde"),
                 SmartPrompt(label="Tell me about this"),
                 SmartPrompt(label="Keep Chatting", decline=True)],
        state=TechniqueState(technique="abcde", step="offering"),
    )
    scripted = model(offer, Reply(text="You pick the phone back up. What happens right before?"))
    from mani.db import pool

    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "my manager criticized me in front of everyone")
    await send(alice, thread.id, "every time I try to start I pick the phone back up")

    sent = scripted.last_messages[-1]["content"]
    assert "offer_waiting: yes" in sent
    # The offer is still open, so the offering stage is named, with every stage still to learn.
    assert "stage: offering" in sent.splitlines()
    assert not any(line.startswith("next_stage") for line in sent.splitlines())
    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE, STYLE_WINDOW)
    assert ctx.technique.outcome is TechniqueOutcome.DECLINED


async def test_asking_for_a_declined_framework_themselves_starts_it(alice, model):
    """Someone who carried on past an offer and then asks for that help themselves has said
    yes, even before the cooldown would let Mani offer it again. Observed: Mani began the
    questions in its own words while nothing was running."""
    offer = Reply(
        text="I have a sequence of questions that could help. Would you like to try it?",
        prompts=[SmartPrompt(label="Try It", technique="abcde"),
                 SmartPrompt(label="Tell me about this"),
                 SmartPrompt(label="Keep Chatting", decline=True)],
        state=TechniqueState(technique="abcde", step="offering"),
    )
    model(
        offer,
        Reply(text="You keep replaying it. Which part stays with you?"),
        Reply(text="Okay. We'll take it one step at a time together. What happened?",
              state=TechniqueState(technique="abcde", step="activating_event", accepted=True)),
    )
    from mani.db import pool

    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "my manager criticized me in front of everyone")
    await send(alice, thread.id, "I keep replaying it")
    await send(alice, thread.id, "actually I'd like some help looking at it")

    async with pool.as_user(alice) as conn:
        ctx = await threads.load_turn_context(conn, thread.id, ALICE, STYLE_WINDOW)
    assert (ctx.technique.framework_id, ctx.technique.outcome, ctx.technique.phase) == (
        "abcde", TechniqueOutcome.ACCEPTED, "activating_event",
    )


async def test_a_declined_framework_can_be_offered_again_after_a_few_replies(alice, model):
    """muhammad, 2026-09-24: after "Keep Chatting", Mani checks again after a few
    more messages - the same framework if it still fits best."""
    offer = Reply(
        text="We could look at what happened and what you told yourself about it. Would you like to try?",
        prompts=[SmartPrompt(label="Try It", technique="abcde"),
                 SmartPrompt(label="Tell Me More"),
                 SmartPrompt(label="Keep Chatting", decline=True)],
        state=TechniqueState(technique="abcde", step="offering"),
    )
    chats = [
        Reply(text=text) for text in (
            "What else has been on your mind about it?",
            "When does it come back to you most?",
            "Who was in the room when it happened?",
            "How did the evening go afterwards?",
        )
    ]
    model(offer, *chats, offer)
    thread = await start(alice)
    await send(alice, thread.id, "my manager criticized me in front of everyone")
    await send(alice, thread.id, "Keep Chatting")
    for text in ("it keeps coming back", "I replay it at night", "I can't let it go"):
        await send(alice, thread.id, text)

    again = await send(alice, thread.id, "maybe I do want to look at it")
    assert [p.technique for p in again.prompts if p.technique] == ["abcde"]


# The stage ledger: what the reply reports of each stage decides the stage Mani asks next.

OFFER_TO_TRY = Reply(
    text="I have a sequence of questions that could help. Would you like to try it?",
    prompts=[SmartPrompt(label="Try It", technique="abcde"),
             SmartPrompt(label="Tell me about this"),
             SmartPrompt(label="Keep Chatting", decline=True)],
    state=TechniqueState(technique="abcde", step="offering"),
)


def _stages(**statuses: str) -> list[StageReport]:
    return [StageReport(stage=stage, status=status) for stage, status in statuses.items()]


def _abcde_state(step: str, accepted: bool | None = None, **statuses: str) -> TechniqueState:
    return TechniqueState(technique="abcde", step=step, accepted=accepted, stages=_stages(**statuses))


def _ledger(row) -> dict[str, tuple[str, int]]:
    return {stage: (entry["status"], entry["turns"]) for stage, entry in row["stage_ledger"].items()}


async def _checked_notes(caplog) -> str:
    return " ".join(r.getMessage() for r in caplog.records if "checked reply" in r.getMessage())


async def test_tapping_yes_after_the_story_was_told_lands_on_the_first_stage_not_yet_known(
    alice, model, caplog
):
    """The event, what it meant and how it affected them were told before the offer, so the
    questions start at dispute, whatever step the reply names."""
    model(
        OFFER_TO_TRY,
        Reply(text="You were criticised and it made you feel small. What supports that belief?",
              state=_abcde_state("activating_event", activating_event="known", belief="known", consequences="known")),
    )
    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "my manager criticised me and I felt small and avoided everyone")
    caplog.set_level(logging.INFO)
    await send(alice, thread.id, "Try It")

    row = await _state_row(thread.id)
    assert (row["outcome"], row["phase"]) == ("accepted", "dispute")
    assert _ledger(row) == {
        "activating_event": ("known", 0), "belief": ("known", 0), "consequences": ("known", 0),
    }
    assert "the reported step differs from the stage the ledger gives" not in await _checked_notes(caplog)


async def test_a_partly_told_stage_is_the_one_asked_with_the_ones_before_it_known(alice, model):
    model(
        OFFER_TO_TRY,
        Reply(text="What did it come to mean to you?",
              state=_abcde_state("activating_event", activating_event="known", belief="partial")),
    )
    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "my manager criticised me in front of everyone")
    await send(alice, thread.id, "Try It")

    row = await _state_row(thread.id)
    assert row["phase"] == "belief"
    assert _ledger(row) == {"activating_event": ("known", 0), "belief": ("partial", 0)}


async def test_saying_yes_in_words_lands_on_the_same_stage_as_a_tap(alice, model):
    scripted = model(
        OFFER_TO_TRY,
        Reply(text="You were criticised and felt small. What supports that belief?",
              state=_abcde_state("activating_event", accepted=True,
                                 activating_event="known", belief="known", consequences="known")),
    )
    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "my manager criticised me and I felt small and avoided everyone")
    await send(alice, thread.id, "yeah let's do it")

    sent = scripted.last_messages[-1]["content"].splitlines()
    assert "offer_waiting: yes" in sent
    assert "stage_ledger: activating_event missing, belief missing, consequences missing, dispute missing, effective_new_belief missing" in sent
    row = await _state_row(thread.id)
    assert (row["outcome"], row["phase"]) == ("accepted", "dispute")


async def test_a_framework_asked_for_again_after_a_decline_starts_from_an_empty_ledger(alice, model):
    model(
        OFFER_TO_TRY,
        Reply(text="You keep replaying it. Which part stays with you?"),
        Reply(text="Okay. What happened?",
              state=_abcde_state("activating_event", accepted=True, activating_event="partial")),
    )
    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "my manager criticised me in front of everyone")
    await send(alice, thread.id, "I keep replaying it")
    await send(alice, thread.id, "actually I'd like some help looking at it")

    row = await _state_row(thread.id)
    assert (row["outcome"], row["phase"]) == ("accepted", "activating_event")
    assert _ledger(row) == {"activating_event": ("partial", 0)}


async def test_an_offer_and_a_decline_store_an_empty_ledger_whatever_the_reply_reports(alice, model):
    model(
        Reply(**{**OFFER_TO_TRY.model_dump(), "state": _abcde_state("offering", activating_event="known")}),
        Reply(text="Sure, we can just talk."),
    )
    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "I keep spiralling")
    assert _ledger(await _state_row(thread.id)) == {}

    await send(alice, thread.id, "Keep Chatting")
    row = await _state_row(thread.id)
    assert (row["outcome"], row["phase"], _ledger(row)) == ("declined", None, {})


async def test_asking_about_the_offer_stores_no_ledger_and_keeps_it_open(alice, model):
    model(
        OFFER_TO_TRY,
        Reply(**{**OFFER_TO_TRY.model_dump(), "state": _abcde_state("offering", activating_event="known")}),
    )
    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "I keep spiralling")
    await send(alice, thread.id, "what would that involve?")

    row = await _state_row(thread.id)
    assert (row["outcome"], row["phase"], _ledger(row)) == ("offered", "offering", {})


async def test_the_stage_follows_the_ledger_not_the_step_and_a_correction_reopens_a_stage(
    alice, model, caplog
):
    """A reply jumping ahead by step records nothing of it. One that reports an earlier stage
    as only partly known, because they took back what they said, moves the stage back."""
    model(
        Reply(text="What supports that belief?", state=_abcde_state("effective_new_belief", dispute="missing")),
        Reply(text="Let's go back to what it meant. What did it come to mean?",
              state=_abcde_state("dispute", belief="partial")),
    )
    thread = await start(alice)
    await _land_on(alice, thread.id, "dispute")
    caplog.set_level(logging.INFO)

    await send(alice, thread.id, "I am not sure")
    row = await _state_row(thread.id)
    assert row["phase"] == "dispute"
    assert "the reported step differs from the stage the ledger gives" in await _checked_notes(caplog)

    caplog.clear()
    await send(alice, thread.id, "actually it did not mean that")
    row = await _state_row(thread.id)
    assert row["phase"] == "belief"
    assert _ledger(row)["belief"] == ("partial", 0)
    assert "moved the stage back: belief" in await _checked_notes(caplog)


async def test_a_stage_the_code_passed_stays_passed_when_the_reply_reports_it_short_of_known(alice, model):
    model(Reply(text="What did it come to mean?", state=_abcde_state("belief", belief="missing")))
    thread = await start(alice)
    await _land_on(alice, thread.id, "consequences", {
        "activating_event": LedgerEntry(status=StageStatus.KNOWN),
        "belief": LedgerEntry(status=StageStatus.PASSED, turns=4),
    })

    await send(alice, thread.id, "I do not know")

    row = await _state_row(thread.id)
    assert row["phase"] == "consequences"
    assert _ledger(row)["belief"] == ("passed", 4)


async def test_a_passed_stage_answered_on_the_ask_after_its_pass_is_recorded_known(alice, model):
    """The reply on the turn that passes a stage still asks it, so their next answer is judged."""
    model(Reply(text="What makes it seem true?", state=_abcde_state(
        "dispute", consequences="known", dispute="missing",
    )))
    thread = await start(alice)
    await _land_on(alice, thread.id, "dispute", {
        "activating_event": LedgerEntry(status=StageStatus.KNOWN),
        "belief": LedgerEntry(status=StageStatus.KNOWN),
        "consequences": LedgerEntry(status=StageStatus.PASSED, turns=3),
    })

    await send(alice, thread.id, "I keep away from people when they gather in the office")

    row = await _state_row(thread.id)
    assert row["phase"] == "dispute"
    assert _ledger(row)["consequences"] == ("known", 3)


async def test_a_stage_answered_on_its_first_turn_moves_on_that_turn(alice, model, caplog):
    model(Reply(text="What makes it seem true?", state=_abcde_state("dispute", consequences="known")))
    thread = await start(alice)
    await _land_on(alice, thread.id, "consequences", {
        "activating_event": LedgerEntry(status=StageStatus.KNOWN),
        "belief": LedgerEntry(status=StageStatus.KNOWN),
    })
    caplog.set_level(logging.INFO)

    await send(alice, thread.id, "It makes me feel depressed and anxious")

    row = await _state_row(thread.id)
    assert row["phase"] == "dispute"
    assert _ledger(row)["consequences"] == ("known", 1)
    assert "passed by the cap" not in await _checked_notes(caplog)


async def test_a_stage_answered_on_its_second_turn_moves_on_that_turn(alice, model):
    model(
        Reply(text="How has it affected you?", state=_abcde_state("consequences", consequences="partial")),
        Reply(text="What makes it seem true?", state=_abcde_state("dispute", consequences="known")),
    )
    thread = await start(alice)
    await _land_on(alice, thread.id, "consequences", {
        "activating_event": LedgerEntry(status=StageStatus.KNOWN),
        "belief": LedgerEntry(status=StageStatus.KNOWN),
    })

    await send(alice, thread.id, "It is hard")
    assert (await _state_row(thread.id))["phase"] == "consequences"

    await send(alice, thread.id, "I feel anxious all day")

    row = await _state_row(thread.id)
    assert row["phase"] == "dispute"
    assert _ledger(row)["consequences"] == ("known", 2)


async def test_a_reply_naming_another_framework_is_ignored_and_the_stage_is_held(alice, model, caplog):
    model(Reply(text="What supports it?", state=TechniqueState(
        technique="dbt_stop", step="stop", stages=_stages(stop="known"),
    )))
    thread = await start(alice)
    await _land_on(alice, thread.id, "dispute")
    caplog.set_level(logging.INFO)

    await send(alice, thread.id, "I am not sure")

    row = await _state_row(thread.id)
    assert (row["outcome"], row["phase"]) == ("accepted", "dispute")
    assert set(_ledger(row)) == {"activating_event", "belief", "consequences", "dispute"}
    assert _ledger(row)["dispute"] == ("missing", 1)
    assert "ignored state: not the running framework" in await _checked_notes(caplog)


async def test_a_running_turn_with_no_state_holds_the_stage(alice, model, caplog):
    model(Reply(text="Tell me more."))
    thread = await start(alice)
    await _land_on(alice, thread.id, "consequences")
    caplog.set_level(logging.INFO)

    await send(alice, thread.id, "it was hard")

    row = await _state_row(thread.id)
    assert (row["outcome"], row["phase"]) == ("accepted", "consequences")
    assert _ledger(row)["consequences"] == ("missing", 1)
    assert "no stages reported on a running turn" in await _checked_notes(caplog)


async def test_a_reply_that_completes_the_ledger_moves_to_closing_and_drops_its_buttons(alice, model):
    model(Reply(
        text="That is a fairer way to see it. How does it sit now?",
        prompts=[SmartPrompt(label="Chat more")],
        state=_abcde_state("effective_new_belief", effective_new_belief="known"),
    ))
    thread = await start(alice)
    await _land_on(alice, thread.id, "effective_new_belief")

    turn = await send(alice, thread.id, "maybe I did my best")

    assert turn.prompts == []
    row = await _state_row(thread.id)
    assert row["phase"] == "closing"
    # The ending cap counts from the last own phase, so a framework stuck on closing retires too.
    assert row["ending_from"] == await _message_count(alice, thread.id)


async def _message_count(alice, thread_id) -> int:
    from mani.db import pool

    async with pool.as_user(alice) as conn:
        return (await threads.get(conn, thread_id, ALICE)).message_count


async def test_a_stage_still_not_known_at_the_cap_is_passed_and_the_next_one_asked(alice, model, caplog):
    model(Reply(text="What did it come to mean to you?", state=_abcde_state("belief", belief="partial")))
    thread = await start(alice)
    await _land_on(alice, thread.id, "belief", stage_ledger={
        "activating_event": LedgerEntry(status=StageStatus.KNOWN),
        "belief": LedgerEntry(status=StageStatus.PARTIAL),
    })
    caplog.set_level(logging.INFO)

    await send(alice, thread.id, "I am not sure")
    row = await _state_row(thread.id)
    assert (row["phase"], _ledger(row)["belief"]) == ("belief", ("partial", 1))

    for turn in range(TUNING.windows.stage_turn_cap - 2):
        await send(alice, thread.id, f"hard to say {turn}")
    assert (await _state_row(thread.id))["phase"] == "belief"

    await send(alice, thread.id, "I do not know")

    row = await _state_row(thread.id)
    assert row["phase"] == "consequences"
    assert _ledger(row)["belief"] == ("passed", TUNING.windows.stage_turn_cap)
    assert "passed by the cap: belief" in await _checked_notes(caplog)


async def test_no_stage_holds_the_thread_past_the_cap_whatever_the_model_reports(alice, model):
    """A model that never reports a stage still reaches closing, after every stage has had its turns."""
    model(Reply(text="Tell me more."))
    thread = await start(alice)
    await _land_on(alice, thread.id, "activating_event", stage_ledger={})
    bound = len(ABCDE_STAGES) * TUNING.windows.stage_turn_cap

    for turn in range(bound - 1):
        await send(alice, thread.id, f"hm {turn}")
    assert (await _state_row(thread.id))["phase"] == "effective_new_belief"

    await send(alice, thread.id, "hm")
    row = await _state_row(thread.id)
    assert row["phase"] == "closing"
    assert {status for status, _ in _ledger(row).values()} == {"passed"}


async def test_a_concern_turn_leaves_the_stage_and_its_count_as_they_were(alice, model):
    model(Reply(text="I am here with you. Tell me more about that.",
                state=_abcde_state("dispute", belief="known", consequences="known")))
    thread = await start(alice)
    stored = {"activating_event": LedgerEntry(status=StageStatus.KNOWN),
              "belief": LedgerEntry(status=StageStatus.PARTIAL, turns=2)}
    await _land_on(alice, thread.id, "belief", stage_ledger=stored)

    await send(alice, thread.id, "honestly I don\u2019t want to be here anymore")

    row = await _state_row(thread.id)
    assert (row["outcome"], row["phase"]) == ("accepted", "belief")
    assert _ledger(row) == {"activating_event": ("known", 0), "belief": ("partial", 2)}


async def test_try_it_on_a_concern_turn_is_kept_and_the_next_turn_is_the_accepting_one(alice, model):
    model(
        OFFER_TO_TRY,
        Reply(text="I hear you, and I'm right here with you.", crisis=Crisis(reason="hopelessness"),
              state=_abcde_state("dispute", activating_event="known", belief="known")),
        Reply(text="What makes that belief feel true?",
              state=_abcde_state("activating_event", activating_event="known", belief="known", consequences="known")),
    )
    thread = await past_the_opening(await start(alice))
    await send(alice, thread.id, "my manager criticised me and I felt small and avoided everyone")

    await send(alice, thread.id, "Try It")
    row = await _state_row(thread.id)
    assert (row["outcome"], row["phase"], _ledger(row)) == ("accepted", "offering", {})

    await send(alice, thread.id, "I am okay, let's go on")
    row = await _state_row(thread.id)
    assert row["phase"] == "dispute"
    assert _ledger(row) == {"activating_event": ("known", 0), "belief": ("known", 0), "consequences": ("known", 0)}


@pytest.mark.parametrize(("turns_short_of_the_cap", "retired"), [(0, True), (1, False)])
async def test_a_framework_held_on_closing_retires_at_the_ending_cap(alice, model, turns_short_of_the_cap, retired):
    model(_ending("How does it sit now?", None, step="closing"))
    thread = await start(alice)
    await _land_on(alice, thread.id, "closing")
    turns_since_closing = TUNING.windows.ending_turn_cap - turns_short_of_the_cap
    await _set_counts(thread.id, message_count=30, ending_from=30 - 2 * turns_since_closing)

    await send(alice, thread.id, "I do not know")

    assert (await _state_row(thread.id))["phase"] == (None if retired else "closing")


async def test_from_closing_on_the_reported_stages_and_steps_before_it_change_nothing(alice, model):
    model(Reply(text="What did it mean?", state=_abcde_state("belief", belief="missing")))
    thread = await start(alice)
    await _land_on(alice, thread.id, "closing")

    await send(alice, thread.id, "hm")

    row = await _state_row(thread.id)
    assert row["phase"] == "closing"
    assert set(_ledger(row)) == set(ABCDE_STAGES)
    assert {status for status, _ in _ledger(row).values()} == {"known"}


async def test_a_running_turn_records_the_kept_stages_and_the_stored_stage_on_its_call_row(alice, model):
    """What the reply reported, as the guard kept it, and the stage the code stored, so a run can be
    read turn by turn after it ends. The off list entry never reaches the row."""
    from mani.db import pool

    model(Reply(text="What did it come to mean to you?",
                state=_abcde_state("belief", activating_event="known", belief="partial", closing="known")))
    thread = await start(alice)
    await _land_on(alice, thread.id, "activating_event", stage_ledger={})

    turn = await send(alice, thread.id, "my manager criticised me in front of everyone")
    assert (turn.reported_stages, turn.stage) == ({"activating_event": "known", "belief": "partial"}, "belief")

    async with pool.as_admin() as conn:
        call_id = await llm_calls.record(
            conn, purpose=llm_calls.Purpose.CHAT, model="test/model", outcome=llm_calls.Outcome.OK,
            usage=llm_calls.Usage(), latency_ms=1, user_id=ALICE, thread_id=thread.id,
        )
    await orchestrator.link_call(
        call_id, turn.message_id, reported_stages=turn.reported_stages, stage=turn.stage
    )

    async with pool.as_admin() as conn:
        row = await conn.fetchrow(
            "select message_id, reported_stages, stage from admin.llm_calls where id = $1", call_id
        )
    assert dict(row) == {
        "message_id": turn.message_id,
        "reported_stages": {"activating_event": "known", "belief": "partial"},
        "stage": "belief",
    }


async def test_a_turn_with_no_framework_running_or_offered_records_no_stages(alice, model):
    model(Reply(text="That sounds like a long day. What happened?"))
    thread = await start(alice)

    turn = await send(alice, thread.id, "I had a hard day")

    assert (turn.reported_stages, turn.stage) == (None, None)
