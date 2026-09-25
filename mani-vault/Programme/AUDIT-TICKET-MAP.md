# Audit-to-ticket cross-reference

Generated from live Linear state on 2026-09-24, after checking every commit since 2026-09-18
against the tickets and verifying the work against the code and test suites (517 passed,
4 skipped — see MYM-149 for why the skips matter).

**Linear is the source of truth.** This file is a navigational summary, not a second tracker.
When the two disagree, Linear wins and this file is stale.

**Projects:** `30 Day Plan(14 Sep to 14 October)` and `MANI Complete Backlog`, both on team
Mymani.

---

## The one thing that reframes everything below

The backend was **ported**; `mobile/` and `web/` were **rebuilt from scratch**.

The original 2026-09-08 audit was written against an old Turborepo monorepo — `apps/backend`,
`apps/mobile`, `packages/api`, tRPC, pnpm. None of that exists. The backend became a FastAPI
service that owns the whole request path; `web/` is a separate Next.js admin app; `mobile/` is
an Expo app with no API layer wired up yet.

So findings fall into three kinds, and conflating them produces false confidence:

| Kind | Meaning | Example |
|---|---|---|
| **Fixed** | The concept survived the port and the problem is closed in current code | Cross-user message read — now filtered by verified JWT *and* enforced by RLS |
| **Dissolved** | The architecture that made it possible no longer exists | Auth between backend and AI service — there is no second service |
| **Not yet built** | The vulnerable code was never rewritten, so it cannot be "fixed" | Admin auth callback — no callback route exists |

A dissolved finding is not an achievement, and a not-yet-built one is not a regression.

---

## Week 1 — complete

61 tickets, all Done. This is the security foundation, the FastAPI port, and the conversational
engine, verified against code and tests rather than assumed from status.

**Security and data isolation:** MYM-6, MYM-7, MYM-8, MYM-9, MYM-10, MYM-11, MYM-13, MYM-14,
MYM-15, MYM-30, MYM-69, MYM-70, MYM-71, MYM-72, MYM-129.

**Model-output trust boundary:** MYM-17, MYM-18, MYM-19, MYM-20, MYM-21, MYM-125.

**The port itself:** MYM-34, MYM-35, MYM-36, MYM-37, MYM-39, MYM-40, MYM-41, MYM-43, MYM-124.

**Conversational engine:** MYM-50, MYM-98, MYM-100, MYM-103, MYM-113, MYM-121, MYM-122,
MYM-123, MYM-126, MYM-127, MYM-128.

**Data integrity and prompt composition:** MYM-24, MYM-28, MYM-29, MYM-60, MYM-61, MYM-62,
MYM-63, MYM-64, MYM-65, MYM-66, MYM-67, MYM-68, MYM-87, MYM-89.

**Tooling and dependencies:** MYM-16, MYM-23, MYM-44, MYM-46, MYM-76, MYM-94.

MYM-113 was closed on 2026-09-24 but belongs here: migration 002 (2026-09-16) populated every
framework's stages and activation data. It lives as `jsonb` on `admin.frameworks`, not the
separate tables the ticket proposed.

### Two closed tickets the code has since moved past

Left Done so Week 1 records what was closed then; each carries a comment and a Week 2 link.

- **MYM-28** (summarisation) — closed 2026-09-18, but no summary had ever succeeded: every call
  404'd on the pinned provider. Actually fixed 2026-09-23 → **MYM-139**.
- **MYM-126** (clinical note) — the field was removed 2026-09-22: paid for every turn, read by
  nothing, and storing it needs a retention rule → **MYM-134**.

### Deliberate deviations, canceled rather than closed

- **MYM-38** (auth between backend and AI service) — no second service exists to authenticate
  to. The only inbound boundary is client→FastAPI, protected by JWT verification.
- **MYM-45** (technique selection tool) — framework selection is deterministic scoring in
  `router.py`, not a model tool call. No extra call per turn, assertable without a provider,
  and no model-supplied id to validate. The one real tool call is the exercise hand-off
  (MYM-44).
- **MYM-111** (route-then-speak, two calls per turn) — contradicts ADR-002. Safety runs first
  deterministically (MYM-123), routing is in process (MYM-122), and `[ctx]` carries the stage.

---

## Week 2 — in progress

**Done (18), all untracked until 2026-09-24:**

- **Security:** MYM-130 (thread ownership in RLS on four tables), MYM-131 (summaries and
  framework state backend-only, typed `[ctx]` disarmed), MYM-132 (production refuses to boot
  without secrets; secrets never printed), MYM-133 (endpoint auth tested over the wire),
  MYM-136 (account deletion endpoint, profile row on signup), MYM-137 (crisis screen catches
  phone typing and passive ideation).
- **Turn correctness:** MYM-138 (retries and concurrent sends), MYM-139 (summaries succeed),
  MYM-140 (framework lifecycle, safety-concern pause, recent-crisis flag).
- **Conversation design, per the client's specs:** MYM-134 (clinical note removed), MYM-135
  (AI-layer audit fixes), MYM-141 (opening, offers, endings), MYM-143 (Chat More / Go to
  Library enforced; Thought Reframe finishes), MYM-144 (client's second doc).
- **Memory:** MYM-142 (patterns across conversations, ADR-005).
- **Measurement and tooling:** MYM-145 (client-scenario rehearsal), MYM-146 (chat-tester on
  real Supabase Auth).
- **Mobile:** MYM-147 (conversation-style picker, PR #4 on `main`, simulated locally and not
  wired to the API).

**In progress:** MYM-25 (daily limit built, off by default until set to 300), MYM-42 (needs a
decision: the before/after comparison is impossible now the old path is gone), MYM-99 (the
framework-end half is enforced; the no-framework end is undecided), MYM-105 (styles and
personas done; they still measure too close), MYM-106 (some checks deterministic, others not),
MYM-114 (local only), MYM-148 (feelings-first questions, uncommitted).

**Todo, found during the reconciliation:** MYM-149 (four admin-auth tests skip under JWKS, so
admin-only is currently unverified over HTTP), MYM-150 (let a person see and erase their
memory), MYM-151 (schedule the idle memory fold).

**Not started from the original Week 2 plan:** MYM-22 (CI), MYM-26 (exercise-level targeting;
the backend half landed with MYM-44), MYM-27, MYM-31, MYM-32, MYM-33.

---

## Still open

**Ops floor.** MYM-101 and MYM-22 (no CI anywhere), MYM-102 (crisis recall never measured
against realistic language — the deterministic screen is unit-tested, the model's judgement is
not). Crisis resources and the approved safety protocol are still empty and are muhammad's to
supply.

**Conversational engine, next tranche.** MYM-104 (the vague-reply pivot: `threads.vague_streak`
exists and nothing writes it), MYM-107, MYM-108, MYM-109, MYM-110, MYM-112.

**Mobile.** MYM-26, MYM-27, MYM-31, MYM-32, MYM-33. MYM-32 (no error boundary) was
**reproduced** in the rebuild rather than carried over — it is a live bug in current code, not
a stale finding.

**Deployment.** MYM-47, MYM-48, MYM-49.

**Web admin.** MYM-12 (Week 3); MYM-73 and the Admin Portal milestone in the Backlog.

**Backlog project** retains store readiness (MYM-78 to MYM-82; MYM-80's backend half is done
in MYM-136, and the in-app screen is what remains), the admin portal (MYM-74, MYM-91,
MYM-115 to MYM-117), MYM-83 (data retention, which memory now makes more pressing),
MYM-118 (generated types), MYM-119 (durable summaries), MYM-120, MYM-97, and the remaining
mobile findings.

---

## Superseded findings worth closing in Linear

These describe code that no longer exists. They are not fixed and not open — they are moot, and
leaving them in the backlog inflates it with work nobody will ever do:

MYM-53, MYM-54, MYM-55, MYM-56, MYM-58, MYM-59, MYM-96 (old `AuthProvider`, `RootNavigator`,
React Query setup — none present in the rebuilt mobile app), MYM-52 (no audio feature yet),
MYM-77, MYM-85, MYM-92, MYM-95 (old monorepo tooling), MYM-88, MYM-90, MYM-91 (attestation,
app-level encryption and an admin auth callback that were never rebuilt).

**MYM-57** is the exception in that cluster: `ChatDrawer`'s uncancelled timers were
consolidated into one helper in the rebuild, but that helper still never calls `clearTimeout`
(`mobile/src/components/chat/chat-drawer.tsx`, rechecked on `main` 2026-09-24). Still a real
bug.

---

## Keeping this file honest

Regenerate it from Linear rather than editing it by hand — it drifted badly last time because
it was maintained in parallel with the tracker instead of derived from it. A stale
cross-reference is worse than none, because it creates confidence that nothing checked.

The 2026-09-24 pass found six days of work (14 commits, a merged PR) with no ticket at all.
Ticketing the work as it lands is cheaper than reconstructing it from `git log` afterwards.
