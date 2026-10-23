# ABOUTME: Drives two separate chats against the running backend, one per framework.
# ABOUTME: Prints whether each reaches its stages, the body check-in, and Go to Library.

from __future__ import annotations

import uuid

import client as mani

# Tapped in this order when the button is actually offered. Library ends the route:
# the apps open the library instead of sending the label as a chat message.
ROUTE = (
    "Direct",
    "Try it",
    "Yes",
    "Chest",
    "Feel Better",
    "Yes, It Helped",
    "Go to Library",
)
MAX_TURNS = 24

ABCDE = [
    "My manager criticized my report in front of the whole team yesterday.",
    "He said the numbers were careless, and everyone was watching.",
    "I felt humiliated. I believed I am incompetent and that they all saw it.",
    "I went quiet for the rest of the meeting and replayed it all night.",
    "He has corrected my work before, which is what makes the belief feel true.",
    "The numbers were right, and two colleagues used them afterwards.",
    "One comment in one meeting does not mean I cannot do the job.",
    "Yes. That is the more realistic way I want to hold it.",
]

REFRAME = [
    "The thought going round is that I will never be good enough, no matter what I do.",
    "It is not one event. It shows up every time I finish something and still feel it was not enough.",
    "It hurts because I treat that thought as a fact about who I am.",
    "I want a brief look at the thought, not a long examination of one meeting.",
    "People have told me the work was solid, so the thought is not the only reading.",
    "A more balanced thought is that I can be good enough at this even when I feel unsure.",
    "Yes. That balanced thought is the one I want to keep.",
]


def choose(prompts: list[dict], target: str) -> str | None:
    """The button this turn should tap, or None when the next line should be typed.

    A matching framework is taken. A different framework is declined once; the caller
    records that and the next offer is taken, so the body route can still be reached.
    """
    by_label = {p.get("label"): p for p in prompts}
    offered = [p for p in prompts if p.get("technique")]
    if offered:
        match = next((p for p in offered if p.get("technique") == target), None)
        if match is not None:
            return match["label"]
        return None
    for label in ROUTE:
        if label == "Try it":
            continue
        if label in by_label:
            return label
    return None


def run(target: str, lines: list[str]) -> dict:
    session = mani.sign_up(f"cadence-{target}-{uuid.uuid4().hex[:8]}@local.test", "demo-password-123")
    api = mani.ManiClient(session=session)
    started = api.start_new_thread()
    thread_id = started["thread"]["id"]
    pending = list(lines)
    trace = []
    reached_library = False
    offered = None
    declined_other = False
    api.send_message(thread_id, "Direct")

    for turn in range(1, MAX_TURNS + 1):
        history = api.list_messages(thread_id)
        latest = next((m for m in reversed(history) if m.get("role") == "mani"), None)
        prompts = (latest or {}).get("prompts") or []
        offered_now = [p.get("technique") for p in prompts if p.get("technique")]
        tap = choose(prompts, target)
        if offered_now and tap is None and not declined_other:
            decline = next((p.get("label") for p in prompts if p.get("decline")), None)
            tap = decline
            declined_other = True
        elif offered_now and tap is None:
            tap = next(p.get("label") for p in prompts if p.get("technique"))
        if tap == "Go to Library":
            reached_library = True
            trace.append({"turn": turn, "sent": "(library opens)", "buttons": [p.get("label") for p in prompts]})
            break
        if tap is not None:
            sent = tap
        elif pending:
            sent = pending.pop(0)
        else:
            sent = "Yes, that matches what I mean."
        reply = api.send_message(thread_id, sent)
        buttons = [p.get("label") for p in reply.get("prompts") or []]
        techniques = [p.get("technique") for p in reply.get("prompts") or [] if p.get("technique")]
        if techniques and offered is None:
            offered = techniques[0]
        asking = [row.get("stage") for row in (reply.get("ledger") or []) if row.get("asking")]
        trace.append({
            "turn": turn,
            "sent": sent,
            "buttons": buttons,
            "asking": asking,
            "reply": (reply.get("content") or "").replace("\n", " ")[:160],
        })
        print(f"  {turn:02d} sent={sent!r} asking={asking or '-'} buttons={buttons or '-'}", flush=True)
        if reply.get("crisis_detected"):
            break
        if "Go to Library" in buttons:
            reached_library = True
            break

    stages = []
    for row in trace:
        for stage in row.get("asking") or []:
            if stage not in stages:
                stages.append(stage)
    return {
        "thread": thread_id,
        "offered": offered,
        "stages": stages,
        "library": reached_library,
        "turns": len(trace),
        "trace": trace,
    }


def main() -> None:
    print(f"backend {mani.API_BASE_URL}", flush=True)
    for name, lines in (("abcde", ABCDE), ("thought_reframe", REFRAME)):
        print(f"\n== {name} ==", flush=True)
        result = run(name, lines)
        print(
            f"offered={result['offered']} stages={result['stages']} "
            f"library={result['library']} turns={result['turns']}",
            flush=True,
        )


if __name__ == "__main__":
    main()
