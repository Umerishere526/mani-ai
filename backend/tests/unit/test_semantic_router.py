# ABOUTME: Which framework real messages route to, against the shipped exemplar vectors.
# ABOUTME: Query vectors are recorded, so this measures routing rather than the network.

import json
import pathlib

import pytest

from mani.chat import semantic_router as sr
from mani.chat import vectors

FIXTURE = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "routing_cases.json"


@pytest.fixture(scope="module")
def recorded() -> dict:
    return json.loads(FIXTURE.read_text())


@pytest.fixture(scope="module")
def index() -> vectors.FacetIndex:
    loaded = vectors.load()
    assert loaded is not None, "content/framework_vectors.json is missing: run scripts/embed_frameworks.py"
    return loaded


def embedder_for(recorded: dict):
    """Serves the recorded vector for a query, so no call leaves the machine."""
    table = recorded["queries"]

    def embed(texts: list[str]) -> list[list[float]]:
        missing = [t for t in texts if t not in table]
        if missing:
            raise AssertionError(
                f"no recorded vector for {missing[0]!r}; re-record tests/fixtures/routing_cases.json"
            )
        return [table[t] for t in texts]

    return embed


def route(messages, recorded, index):
    return sr.route(messages, index=index, embedder=embedder_for(recorded))


def test_every_recorded_case_routes_as_labelled(recorded, index):
    """The whole labelled set at once, so a threshold change shows its full cost."""
    failures = []
    for case in recorded["cases"]:
        result = route(case["messages"], recorded, index)
        matched = result.status is sr.RouteStatus.MATCH
        got = result.top.framework_id if result.top else None
        if case["expected"] is None:
            if matched:
                failures.append(f"offered {got} to {case['messages'][0]!r}")
        elif not matched or got != case["expected"]:
            failures.append(
                f"expected {case['expected']}, got {result.status.value}/{got} "
                f"for {case['messages'][0]!r}"
            )
    assert not failures, "\n".join(failures)


def test_nothing_is_offered_to_someone_who_needs_no_framework(recorded, index):
    """The property that matters most. A false match offers a framework to someone who did
    not need one; a false no-match costs one more question, which is cheap."""
    for case in recorded["cases"]:
        if case["expected"] is not None:
            continue
        result = route(case["messages"], recorded, index)
        assert result.status is not sr.RouteStatus.MATCH, case["messages"]


def test_no_match_carries_no_candidates(recorded, index):
    """No match is an answer, never a nearest neighbour to be rounded up."""
    for case in recorded["cases"]:
        result = route(case["messages"], recorded, index)
        if result.status is sr.RouteStatus.NO_MATCH:
            assert result.candidates == ()


def test_an_imminent_action_routes_without_embedding_anything(index):
    """Tense is the signal, so this is answered before the embedder and without it."""
    def explode(texts):
        raise AssertionError("imminent must not reach the embedder")

    result = sr.route(["I'm about to send her a message I'll regret"], index=index, embedder=explode)
    assert result.status is sr.RouteStatus.MATCH
    assert result.top.framework_id == "dbt_stop"
    assert result.top.time_critical


def test_a_provider_failure_is_no_match_not_an_exception(index):
    """Routing is best effort: a failed embedding costs the offer, never the turn."""
    def fails(texts):
        raise RuntimeError("provider is down")

    assert sr.route(["I keep putting it off"], index=index, embedder=fails).status is sr.RouteStatus.NO_MATCH


def test_no_vectors_is_no_match_not_a_crash(monkeypatch):
    """A missing vectors file degrades to "keep talking" rather than failing the turn.

    `index=None` cannot express this on its own: it is the parameter's own default, so it
    means "load the shipped file", and the test passed only while that file happened to
    match nothing. The absence is what has to be simulated.
    """
    monkeypatch.setattr(sr.vectors, "load", lambda *a, **kw: None)
    assert sr.route(["anything"]).status is sr.RouteStatus.NO_MATCH


@pytest.mark.parametrize("messages", [[], [""], ["   "]])
def test_an_empty_message_routes_nowhere(messages, index):
    def explode(texts):
        raise AssertionError("an empty message must not reach the embedder")

    assert sr.route(messages, index=index, embedder=explode).status is sr.RouteStatus.NO_MATCH


def test_the_query_is_their_opening_and_their_most_recent_messages(index):
    """The opening line names the situation, so it is always read: a window of the last two
    alone dropped it by the third turn and the conversation wandered. The middle is left out,
    so the query stays about what they came with and what they are saying now.
    """
    said = ["I am depressed", "it started after the breakup", "I keep replaying it", "yeah"]
    assert sr._query(said) == "I am depressed\nI keep replaying it\nyeah"
    # Nothing is repeated while the conversation is shorter than the window.
    assert sr._query(["I am depressed"]) == "I am depressed"
    assert sr._query(["I am depressed", "since the breakup"]) == (
        "I am depressed\nsince the breakup"
    )


def test_an_unrelated_opening_does_not_take_over_a_clear_conversation(recorded, index):
    """The opening is read, so it dilutes - it took this case from 0.81 to 0.58 - but a
    conversation that clearly points somewhere still routes there with room to spare."""
    messages = [
        "we talked about my sister last week",
        "I am behind on everything and do not know where to begin",
        "work, my landlord, and a family thing",
    ]
    result = route(messages, recorded, index)
    assert result.status is sr.RouteStatus.MATCH
    assert result.top.framework_id == "structured_problem_solving"


def test_routing_is_deterministic(recorded, index):
    case = recorded["cases"][0]
    first = route(case["messages"], recorded, index)
    second = route(case["messages"], recorded, index)
    assert first == second


def test_the_shipped_vectors_cover_every_framework(index):
    """A framework with no exemplars can never be routed to, which would be silent."""
    from scripts.seed import FRAMEWORKS_DIR, parse_framework

    authored = {parse_framework(p)["id"] for p in FRAMEWORKS_DIR.glob("*.md")}
    embedded = {f.framework_id for f in index.of_kind("exemplar")}
    assert authored == embedded, f"missing exemplar vectors for {authored - embedded}"


def test_the_vectors_match_the_framework_files(index):
    """Routing on vectors that no longer match the authored exemplars is worse than not
    routing, so staleness fails here rather than drifting in production."""
    from scripts.embed_frameworks import content_hash, facets

    assert not vectors.is_stale(index, content_hash(facets())), (
        "content/framework_vectors.json is stale: run scripts/embed_frameworks.py"
    )
