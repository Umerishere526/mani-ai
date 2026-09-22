# Audit-to-ticket cross-reference

Generated from live Linear state on 2026-09-18, after verifying every finding against the
current Python/FastAPI codebase rather than against ticket labels.

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

60 tickets, all Done. This is the security foundation, the FastAPI port, and the conversational
engine, verified against code and tests rather than assumed from status.

**Security and data isolation:** MYM-6, MYM-7, MYM-8, MYM-9, MYM-10, MYM-11, MYM-13, MYM-14,
MYM-15, MYM-30, MYM-69, MYM-70, MYM-71, MYM-72, MYM-129.

**Model-output trust boundary:** MYM-17, MYM-18, MYM-19, MYM-20, MYM-21, MYM-125.

**The port itself:** MYM-34, MYM-35, MYM-36, MYM-37, MYM-39, MYM-40, MYM-41, MYM-43, MYM-124.

**Conversational engine:** MYM-50, MYM-98, MYM-100, MYM-103, MYM-121, MYM-122, MYM-123,
MYM-126, MYM-127, MYM-128.

**Data integrity and prompt composition:** MYM-24, MYM-28, MYM-29, MYM-60, MYM-61, MYM-62,
MYM-63, MYM-64, MYM-65, MYM-66, MYM-67, MYM-68, MYM-87, MYM-89.

**Tooling and dependencies:** MYM-16, MYM-44, MYM-46, MYM-76, MYM-94.

### Two deliberate deviations, canceled rather than closed

- **MYM-38** (auth between backend and AI service) — no second service exists to authenticate
  to. The only inbound boundary is client→FastAPI, protected by JWT verification.
- **MYM-45** (technique selection tool) — framework selection is deterministic scoring in
  `router.py`, not a model tool call. No extra call per turn, assertable without a provider,
  and no model-supplied id to validate. The one real tool call is the exercise hand-off
  (MYM-44).

---

## Still open

**Ops floor — the real gaps.** MYM-25 (no rate limiting on chat send; the only mitigation is
send-idempotency, which is not a throttle), MYM-101 and MYM-22 (no CI anywhere), MYM-102
(crisis evaluation scenarios never run), MYM-114 (Supabase email confirmation).

**Conversational engine, next tranche.** MYM-104 through MYM-113 — pivot tracking, STRICT-mode
style rules, deterministic output constraints, one-question-per-turn, follow-up anchoring,
route-then-speak, trimming the technique library per turn, populating
`admin.framework_stages`, and deciding what Two Worry Buckets is.

**Mobile.** MYM-31, MYM-32, MYM-33. Note MYM-32 (no error boundary) was **reproduced** in the
rebuild rather than carried over — it is a live bug in current code, not a stale finding.

**Deployment.** MYM-42, MYM-47, MYM-48, MYM-49.

**Web admin.** MYM-12, MYM-26, MYM-27, MYM-73.

**Backlog project** retains store-readiness (MYM-74, MYM-78 through MYM-83), remaining mobile
findings, and newer items MYM-115 through MYM-120.

---

## Superseded findings worth closing in Linear

These describe code that no longer exists. They are not fixed and not open — they are moot, and
leaving them in the backlog inflates it with work nobody will ever do:

MYM-53, MYM-54, MYM-55, MYM-56, MYM-58, MYM-59, MYM-96 (old `AuthProvider`, `RootNavigator`,
React Query setup — none present in the rebuilt mobile app), MYM-52 (no audio feature yet),
MYM-77, MYM-85, MYM-92, MYM-95 (old monorepo tooling), MYM-88, MYM-90, MYM-91 (attestation,
app-level encryption and an admin auth callback that were never rebuilt).

**MYM-57** is the exception in that cluster: `ChatDrawer`'s uncancelled timers were
consolidated into one helper in the rebuild, but that helper still never calls `clearTimeout`.
Still a real bug.

---

## Keeping this file honest

Regenerate it from Linear rather than editing it by hand — it drifted badly last time because
it was maintained in parallel with the tracker instead of derived from it. A stale
cross-reference is worse than none, because it creates confidence that nothing checked.
