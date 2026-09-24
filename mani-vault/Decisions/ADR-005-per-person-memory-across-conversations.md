---
type: decision
status: proposed
date: 2026-09-23
apps: backend
tags: [decision, memory, health-data, privacy]
---

# ADR-005: Per-person memory across conversations

**Status:** proposed
**Affects:** backend

## Context

Mani knew nothing about a person beyond one conversation. The profile holds a nickname, onboarding
topics and a chosen style, and nothing learned from chatting was ever kept. muhammad asked for a record
of patterns about each person, such as when they feel low and the reason they gave, and how they cope.
It should update when a chat finishes and shape later replies. A new chat must still start with none of
the previous chat's messages.

What gets stored is special-category health data, so where it lives, who can read it and how long it
lasts are the decisions that matter. The storage mechanism is not.

## Options considered

### Option A: a column on `public.profiles`
- Pros: the simplest.
- Cons: a profile row is readable by its owner through the API and PostgREST, so the person could read,
  and through the column grants possibly write, what is kept about them. muhammad chose admin plus
  backend visibility, not self-service.

### Option B: a table in `admin`, written only by the backend
- Pros: `admin` is never exposed by PostgREST, and `authenticated` gets no grant on the table.
  `mani_service` reads and writes it with RLS scoping it to the caller's own row, so a query that
  forgets its filter still can't reach anyone else. It cascades away with the account.
- Cons: the person can't see or correct what is remembered (see Consequences).

### Option C: carry the previous chat's summary into the next chat
- Pros: no new model call.
- Cons: summaries are about events in one conversation, not patterns, and carrying them forward is
  exactly the "context from the previous chat" muhammad ruled out.

## Decision

Option B: `admin.user_memory`, one JSON row per person, added in migration 009.

- **What it records:** themes, when they feel low (and the reason they gave), when they feel better,
  what helps, what doesn't, and how they like the conversation to go. Entries are short, in their own
  words, and never a diagnosis or label.
- **What it never records:**
  - anything about wanting to die, disappear, not exist or self-harm;
  - names or identifying details;
  - anything from a thread flagged for crisis. The `recent_crisis` flag covers that, and it carries
    only the fact, never content.
- **When it's written:**
  - when the person starts a new chat, the previous chats are folded in;
  - a scheduled job (`scripts/fold_idle_threads.py`) folds any chat quiet for 24 hours.
  - Each fold is one model call (`purpose = memory_fold`). It reads only messages since the last fold,
    and holds a claim on the thread so two folds never overlap.
- **How it's used:** as a system-prompt layer after the per-user context, as patterns to choose an
  approach from. It is never quoted, never "I remember", and never a reference to a past conversation.
- **Who reads it:** the backend, and admins through `GET /v1/admin/users/{user_id}/memory`.
- **Retention:** until the account is deleted. Tested both ways: as `postgres`, and through real
  GoTrue deletion as `supabase_auth_admin`.

## Consequences

- **The person can't view or erase their memory**, short of deleting their account. Before launch,
  check this against data-access rights (GDPR Art. 15 and 17, or the equivalent where Mani ships). It
  may need a person-facing read and erase endpoint.
- **The memory goes into the system prompt on every turn.** It is bounded to 6 entries per list of
  160 characters each, and the fold treats the transcript as data rather than instructions. Model-written
  text in a system prompt is still an injection surface, the same as the thread summary.
- **The fold can still slip on wording.** In a live run it wrote "burden", which the person never said.
  The boundary rules reduce this but can't guarantee it.
- **Hosting has to run the idle job.** Without a scheduler, only "new chat" folds happen, and someone
  who never starts a second chat never gets a memory.
- **To reverse:** drop `admin.user_memory` and `threads.memory_folded_at`, remove the `user_memory`
  composer layer, and delete `mani/memory.py`. Nothing else depends on them.

## Links

- Related: [[ADR-002-one-model-call-per-chat-turn]]. The fold is a separate background call, never
  part of a turn.
- Journal: [[measure-before-tuning-prompts]]
