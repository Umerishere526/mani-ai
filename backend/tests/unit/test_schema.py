# ABOUTME: Checks the reply shape sent each turn is chosen by the moment, and that a loose value
# ABOUTME: is read as null rather than failing the turn, which would cost a call and the message.

from mani.llm.schema import Moment, Reply, Slots, as_reply, reply_for

SLOTS = Slots(going_through="what they are going through", lead_line="a warm line", their_words="their words")
CORE = {"reasoning", "style", "picture", "text", "title", "crisis"}
# Where a stage can be answered or a yes can start one (spec 0004).
STAGE = {"stage_updates", "stage_answer"}
# Where the walk can start or move, so the stage it reaches is judged (thread 4b93d612, 2026-10-14).
REACH = STAGE | {"next_stage"}


def fields(moment: Moment, **flags) -> set[str]:
    return set(reply_for(moment, slots=SLOTS, **flags).model_fields)


def test_each_moment_carries_only_the_fields_that_mean_something_in_it():
    assert fields(Moment.CONCERN) == CORE
    # Mani's own conversation (CHATTING) has a reply shape of its own, ConversationReply; its check is made there.
    assert fields(Moment.CHECK_OPEN) == CORE | {"heart", "check_answer", "heading_toward", "offer"}
    assert fields(Moment.CHECK_OPEN, declined_row=True) == CORE | {
        "heart", "check_answer", "heading_toward", "offer", "offer_answer", *REACH}
    # A stage turn speaks in the chat's voice: no reasoning pass and no reply shape (muhammad, 2026-10-27).
    assert fields(Moment.IN_STAGES) == (CORE - {"reasoning", "style"}) | REACH | {"options"}
    assert fields(Moment.OFFER_OPEN) == CORE | {"offer_answer", "their_words", "options", *REACH}
    assert fields(Moment.BODY) == CORE | {"body", "options"}


def test_the_offer_slots_are_described_in_the_clients_words_and_a_style_without_a_lead_line_has_none():
    supportive = reply_for(Moment.CHECK_OPEN, slots=SLOTS).model_json_schema()
    offer = supportive["$defs"]["Offer"]["properties"]
    assert offer["going_through"]["description"] == "what they are going through"
    assert offer["lead_line"]["description"] == "a warm line"
    directive = reply_for(
        Moment.CHECK_OPEN, slots=Slots(going_through="what they are going through"),
    ).model_json_schema()
    assert set(directive["$defs"]["Offer"]["properties"]) == {"going_through"}


def test_mani_writes_its_text_before_reading_the_person_into_fields():
    """Structured output is generated in schema order. With the understanding, the set heading toward
    and the shape written first, the reply came out as a case note ("can make it hard to separate one
    piece of feedback from…", live 2026-10-13). Only reasoning and the answers that decide the moment
    come before the text; inside a framework the stage fields do too; the set comes before the offer."""
    fields = list(Reply.model_fields)
    for before in ("reasoning", "check_answer", "heart", "offer_answer", "stage_updates", "stage_answer", "next_stage"):
        assert fields.index(before) < fields.index("text"), before
    for after in ("picture", "heading_toward", "style", "offer"):
        assert fields.index("text") < fields.index(after), after
    assert fields.index("heading_toward") < fields.index("offer")
    # On the answer to a check, a yes is the offer, which replaces the text: the set and its slots come
    # first, or the model left the lead line empty (live, 2026-10-13).
    order = list(reply_for(Moment.CHECK_OPEN, slots=SLOTS).model_json_schema()["properties"])
    assert order.index("check_answer") < order.index("heading_toward") < order.index("offer") < order.index("text")


def test_a_field_outside_the_moment_cannot_reach_the_turn():
    """The model's reply is parsed in this turn's shape, so a field it was not sent is dropped."""
    shape = reply_for(Moment.IN_STAGES, slots=SLOTS)
    sent = shape.model_validate({"text": "t", "offer_answer": "yes", "body": "chest"})
    reply = as_reply(sent)
    assert (reply.offer_answer, reply.body) == (None, None)


def test_an_off_list_answer_is_read_as_null_rather_than_failing_the_turn():
    shape = reply_for(Moment.OFFER_OPEN, slots=SLOTS)
    assert shape.model_validate({"text": "t", "offer_answer": "maybe"}).offer_answer is None
    assert Reply.model_validate({"text": "t", "body": "knee"}).body is None
    assert Reply.model_validate({"text": "t", "body": "chest"}).body == "chest"


def test_no_stage_field_reads_a_yes_to_a_check_as_the_start_turn():
    """Live, 2026-10-13: "Null on the turn they say yes" was meant for the yes to the offer, so a
    "yes" to A's check came back with stage_answer null in 3 of 3 replays and the walk stayed on A.
    The start turn is named as accepting the offer, never as a yes."""
    import json

    for moment, flags in ((Moment.IN_STAGES, {}), (Moment.OFFER_OPEN, {})):
        properties = reply_for(moment, slots=SLOTS, **flags).model_json_schema()["properties"]
        described = json.dumps({name: properties[name]["description"] for name in STAGE})
        assert "they say yes" not in described, moment
        assert "Null on" not in properties["stage_answer"]["description"], moment
