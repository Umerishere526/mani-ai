---
type: journal
date: 2026-11-05
tags: [journal, latency, vercel, understanding, memory, summary]
---

> Superseded 2026-11-13 — see [[threads-only-from-the-first-message-2026-11-13]] (how the memory fold is asked for: `memory_fold_pending` and `/v1/threads/{id}/memory-fold` are replaced by `/v1/threads/memory-fold` on New conversation)

# Nothing runs after the response any more (2026-11-05)

Five jobs ran with `fire_and_forget` after a response: Mani's reading of each chat message, the conversation
summary, the memory fold on a new chat, the trace and the call link. Vercel stops a function once its response is
sent, so 15 of 49 readings were cut off and memory folds never wrote a row
([[latency-where-the-wait-goes-2026-11-05]]). Running them inside the next turn was ruled out: the read-think-write
runner ([[read-think-write-2026-11-05]]) replays everything before the model call, which must make no network calls.

muhammad's choice: the app asks. The model work became requests of their own, which Vercel lets finish:

- A turn stores what it leaves (`pending_follow_up`: the reading's call, whether the summary is due), keyed by Mani's
  reply. The response says `follow_up_pending`; the app posts `.../messages/{reply id}/follow-up`, which runs both
  side by side, once. Every turn replaces it, so only the newest reply's waits.
- Starting a chat says `memory_fold_pending`; the app posts `/v1/threads/{id}/memory-fold`.
- The trace and the call link are database writes only, so the route awaits them before responding, side by side.
  That adds a few database round trips to each reply (iad1 to ca-central-1), tens of milliseconds.

`mani/background.py` is deleted. An app that never asks loses that work, so every client must make these calls; only
the chat tester does today. Moving to AWS later needs none of it undone.
