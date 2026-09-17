# Fundamental review — what the earlier audits did not look for

Date: 2026-09-13

The four audit documents from 2026-09-08/09 examined **things that exist and are wrong**: bugs,
gaps in authorization, config drift, duplicated logic. This pass asked a different question —
**what should exist and does not** — across safety design, regulatory posture, and system
governance.

Findings are prefixed `FR-` to avoid collision with the `C#/H#/M#/L#/MOB-#` scheme in the earlier
audits. **None of these are ticketed yet.**

Conclusion up front: the structural verdict from the earlier audits still holds — no rebuild is
warranted, the bones are sound. But four **subsystems the product's claims depend on are absent**,
not defective. Three of them are the first things an app-store reviewer, a data-protection
assessor, or a lawyer would ask about.

---

## Tier 1 — The crisis path is a shell

The app's entire safety claim rests on this path. It is UI with no content behind it.

| ID | Finding | Evidence |
|---|---|---|
| FR-1 | **The four help resources are dead buttons.** `ActionLink` takes an optional `onPress`; all four render without one. A user in crisis taps "Crisis helplines" and nothing happens. | `apps/mobile/src/components/crisis/CrisisDrawer.tsx:187-190`, `onPress?` optional at `:28` |
| FR-2 | **No helpline number, URL, or named service exists anywhere in the repo.** Strongest instruction given is "Call your local emergency number" — which is also the wrong route for suicidal ideation in most jurisdictions. | `CrisisDrawer.tsx:159-161`; no match for `988`/`741741`/`samaritans`/`lifeline` in `apps/` |
| FR-3 | **Mani goes silent at the moment of crisis.** The crisis return path sends `content: ''` and the input bar is replaced with "Chat is paused." The companion stops speaking at peak risk. | `apps/backend/src/services/messages.ts:1150` (and `:1231` on regeneration); `ChatScreen.tsx:469` |
| FR-4 | **Human escalation is an unimplemented TODO.** Nobody is alerted. No SLA on follow-up can be claimed. | `messages.ts:1145` — `// TODO: Flag for human review` |
| FR-5 | **The lock is escapable in one tap and unliftable otherwise.** Starting a new chat clears the flag client-side; the flagged thread itself has no unlock, appeal, or "reach a person" path. | `ChatScreen.tsx:149-150`; flag is per-thread, `20251229112753_add_crisis_detected_to_threads.sql:4` |
| FR-6 | **Crisis events are structurally unmeasurable.** One boolean column — no timestamp, no reason, no count. Repeat events overwrite silently. "How many crisis events last week, and how many were false positives?" cannot be answered, now or retroactively. | migration `:4-5`; only artifact is an ephemeral pino line at `messages.ts:1106` |
| FR-7 | **A crisis eval fixture exists and has never been run.** Four labelled scenarios including suicidal ideation and false-positive controls. Zero importers. The evals README claims crisis detection is verified; it is not. | `apps/backend/test/evals/scenarios.ts:64-85`; `test/evals/README.md:34` |
| FR-8 | **Admin sees a badge and nothing else.** No crisis filter, queue, sort, acknowledge, or notification. Flagged threads are found by scrolling. | `app/admin/chats/page.tsx:94`; search is email/ID only at `:24-25` |
| FR-9 | **The under-18 path routes minors to the same broken drawer** after telling them "help is available". "Child helplines" is the second dead link they would tap. | `apps/mobile/src/screens/OnboardingScreen/steps/Under18Step.tsx:189-198` |

## Tier 2 — Regulatory position is undefined, and two items are hard blockers

| ID | Finding | Evidence |
|---|---|---|
| FR-10 | **No account deletion exists anywhere.** Not a soft delete, not a hard delete — no endpoint, no UI. Apple has required in-app deletion since June 2022 (5.1.1(v)). This is an automatic rejection, and GDPR Art. 17 non-compliance. Cascades are already wired correctly, so the gap is purely that nothing calls it. | no match for `deleteUser`/`deleteAccount` in any `src`; cascades at `20251211000001:11`, `20251211000000:6`, `20251229140000:8`, `20260116000000:69` |
| FR-11 | **Terms and Privacy Policy are decorative text, and the documents do not exist.** Onboarding says "By continuing you accept the Terms of Service and Privacy Policy" — styled `<Text>`, no handler, no URL anywhere in the repo. Consent is claimed to documents the user cannot read. | `steps/SaveChatsStep.tsx:348-350`; no policy URL in `apps/mobile/src` or `apps/backend/src` |
| FR-12 | **Conversations route to the consumer Gemini API with no data-protection controls.** Provider routing is pinned to `google-ai-studio` (good), but no `data_collection: "deny"`, no zero-retention flag, no region constraint. Under default terms that permits human review and training use — on Article 9 special-category health data. | `apps/backend/src/services/llm.ts:144-148`; seeded config `supabase/seed.sql:253` |
| FR-13 | **Message content is stored plaintext.** The AES-256-GCM utility is used for provider API keys only — confirmed, three call sites. Transcripts rely solely on Supabase disk encryption. | `lib/security/encryption.ts:96` called from `lib/db/providers.ts:62,170,210` and `llm.ts:130` only |
| FR-14 | **Verbatim transcripts plus the model's private reasoning are logged.** Worst case logs user message, model text, reasoning, crisis flag and thread ID in one record. `summary.ts` logs the raw response at **`error` level, which is emitted in production**. No `redact` config on the logger. | `messages.ts:713-724`, `:627-636`; `summary.ts:129-132`; `lib/logger.ts:12-17` |
| FR-15 | **No data export or access mechanism** (GDPR Art. 15/20). A subject access request can only be served by manual DB extraction. | not found in `apps/`, `packages/`, `supabase/` |
| FR-16 | **Nothing ages out, ever.** No cron, no TTL, no `expires_at`/`deleted_at`, no cleanup script. Not merely no policy — no mechanism. | no `crons` key in `vercel.json`; no retention column in any migration |
| FR-17 | **Age gate is a self-declared tap placed after account creation and email collection**, with no DOB. Whether minors are in scope is undecided — and that decision drives COPPA / UK AADC / Play Families obligations. | `steps/AgeVerificationStep.tsx:166-177`; flow order in `OnboardingScreen/types.ts:1-13` |
| FR-18 | **Exercise copy makes efficacy claims on named conditions** — "calms anxiety", "resets your nervous system" — and a user-facing category is "Narcissistic Dynamics". This is the wording that decides which side of the wellness/medical line the product sits on. The in-app disclaimers themselves are good and correctly worded. | `library_audio/exercises.json:42,102`; `apps/mobile/src/constants/exerciseCategories.ts:12`; disclaimers at `TrustStep.tsx:143-148`, `CrisisDrawer.tsx:195-198` |

## Tier 3 — The system cannot explain, measure, or defend itself

| ID | Finding | Evidence |
|---|---|---|
| FR-19 | **No message can be traced to what produced it.** Prompts *are* versioned with working rollback — but there is no join key from a message to the prompt version, model ID, or parameters in force at generation time. `PromptConfig` carries no `id` or `version`, so it is structurally unavailable even to a logger. After an incident, you cannot say what the system was instructed to do. | `lib/db/messages.ts:286-344`; `packages/api/src/types/services.ts:55-61` |
| FR-20 | **Model output does not survive the request in production.** Reasoning, usage, finish reason all go to `logger.debug`; production log level is `info`. No error tracking of any kind. | `llm.ts:206-220`; `lib/logger.ts:12` |
| FR-21 | **No timeout, no fallback, no circuit breaker on the LLM call**, and 6 of 7 call sites are unguarded bare `await`s. A hung provider hangs the request to the platform limit. | `llm.ts:196-204`; unguarded at `messages.ts:781, 815, 995, 1032, 1091, 1181` |
| FR-22 | **A failed turn destroys what the user typed.** The input is cleared on send and the text is dropped on dismiss or non-retryable error. Someone who just typed something difficult has to type it again. | `ChatScreen.tsx:308, 236, 246-248, 264` |
| FR-23 | **Zero cost or token accounting.** `usage` is destructured and thrown into a debug log. One user turn can trigger up to six LLM calls, unmetered and unattributed. | `llm.ts:196` |
| FR-24 | **A real LLM-judge eval suite exists and never runs.** Separate jest config, not matched by `pnpm test`, and there is no `.github/` directory — nothing runs in CI because there is no CI. | `test/evals/behavioral.eval.ts:67-145`; `jest.config.js:6` |
| FR-25 | **`summary.ts` bypasses the entire provider architecture** — hardcoded `gpt-4o-mini`, hardcoded prompt string, direct `process.env.OPENAI_API_KEY`. A second provider dependency invisible to the admin portal. | `summary.ts:24, 30, 63-68, 288-298` |
| FR-26 | **The `summarization` and `title_generation` prompts in the admin portal are read by no code.** Admins can edit them, see a version bump, and change nothing. A phantom UI is worse than a missing one. | only `mani_base`, `techniques`, `response_format` are read — `services/prompts.ts:124, 131, 170` |
| FR-27 | **Prompt-version history writes are non-fatal, and delete cascades the history.** If the snapshot write fails the prompt still goes live and the prior content is gone. `deletePrompt`/`togglePromptActive` write no version row at all. No preview, dry-run, approval, or staged rollout; edits reach all users within 5 minutes. | `app/admin/actions.ts:132-143, 151-176`; cascade at `20241204000001:27`; cache TTL `services/prompts.ts:17-18` |

---

## What this changes about sequencing

`DEV-START.md` sequences Stage A (close the exploits) → Stage B (crisis authority + trust
boundary) → … → Stage D (FastAPI). That ordering was built from the earlier audits, which did not
know about Tier 1 or Tier 2.

Two specific corrections:

1. **Tier 1 precedes everything, including the exploits.** The exploits are reachable by someone
   who writes a script. Tier 1 is reachable by a beta tester having the worst night of their life.
2. **FastAPI cannot be validated until FR-19/20/23 exist.** There is no recorded input, output, or
   cost baseline to diff a Python rewrite against. The porting risk was never the orchestrator's
   size — it is that current behaviour is unmeasured, so "the new service behaves the same" is
   currently an unfalsifiable claim.

## What is genuinely sound

Recorded so this document is not read as more alarming than it is:

- Provider config is DB-driven for the chat path — switching providers is a DB edit, not a deploy.
- Prompt versioning and rollback work.
- A real LLM-judge eval harness exists; it needs wiring, not authoring.
- Delete cascades are correctly specified — account deletion is a trigger away, not a data-model change.
- No analytics or tracking SDKs anywhere. Nothing is being quietly harvested.
- The in-app disclaimers that do exist are well-written and correctly scoped.

## Status

Unticketed. These need to be triaged into the 30-day plan and the backlog, and added to
[[AUDIT-TICKET-MAP]] once ticket IDs exist.

**Updated 2026-09-14** — [[2026-09-14-architecture-decisions]] now carries decisions for
several of these, though none are implemented yet:

| Finding | Decision |
|---|---|
| FR-6 — crisis unmeasurable (bare boolean) | `crisis_events` table in the schema rebuild (#1) |
| FR-10, FR-16 — no deletion, no retention | Deletion path and retention columns in the schema rebuild (#1); deletion is also step 1 of the work order |
| FR-13 — message content plaintext | Not yet decided. Still open |
| FR-19, FR-20, FR-23 — no call log, no cost accounting | `llm_calls` table in the schema rebuild (#1); `usage` is a required field in [[ai-service-contract]] |
| FR-7, FR-24 — evals never run, crisis scenarios orphaned | Publishing a prompt runs the evals (#8); import the crisis scenarios |
| FR-25, FR-26 — `summary.ts` bypasses the provider system; two prompts read by no code | Summarization moves to `POST /v1/summarize`, wiring both prompts or deleting them |
| FR-27 — prompt governance holes | Becomes a required feature once the portal is authoritative (#8) |
| FR-1..FR-5, FR-9 — the crisis path | Step 1 of the work order. Nothing about it depends on the FastAPI migration |
| FR-11, FR-17, FR-18 — policy documents, age scope, claims posture | Still open. The claims/regulatory question gates store submission |
