# Audit-to-ticket cross-reference

Maps every finding in the audit journal notes to the Linear ticket tracking it. The source
documents now live in `archive/` — they are evidence, not instructions.
Built 2026-09-11 after a manual gap-check found several findings had been missed on
the first ticket-writing pass. Use this to check coverage at a glance instead of
re-reading five markdown files by hand.

**Projects:** `30-Day` = "Production Readiness — 30 Day Plan" (MYM-6–49). `Backlog` =
"MANI Complete Backlog" (MYM-50–96).

**When adding a new finding or closing a ticket, update this file in the same change.**
An unmapped finding is exactly the failure mode this file exists to catch.

**Note (2026-09-14):** several tickets below are affected by decisions recorded in
[[2026-09-14-architecture-decisions]]. Re-triage these before working them:

| Tickets | What changed |
|---|---|
| MYM-62, MYM-63, MYM-64, MYM-69 | **Absorbed by the schema rebuild** (atomicity, lost-update races, technique state, JWT-scoped RLS). The tables are being rewritten, not migrated, so these stop being individual patches. |
| MYM-72 (M5 — decrypted key in RSC payload) | **Killed by decision #4.** The OpenRouter key moves to ai-service's environment, so it never reaches the admin portal at all. |
| MYM-73 (L2 — `ADMIN_EDITING_ENABLED` gates rendering only) | **Promoted to do-first.** It was low priority when only engineers used the portal; with the portal authoritative and non-technical editors on it, an ungated mutation matters. |
| MYM-92 (lint to zero) | Still deferred, but keep lint **out of the CI gate** until the 419 errors are cleared. |

---

## [[2026-09-08-repo-audit]] — Critical

| ID | Finding | Ticket | Project |
|---|---|---|---|
| C1 | `messages.list` omits `ctx.userId` — cross-user message read | MYM-6, MYM-7 | 30-Day |
| C2 | `messages` INSERT policy has no thread-ownership check | MYM-10 | 30-Day |
| C3 | Crisis lock is client-side only | MYM-13, MYM-14 | 30-Day |
| C4 | `insert_message_pair` RPC has no auth check, `anon` EXECUTE granted | MYM-8, MYM-9 | 30-Day |

## High

| ID | Finding | Ticket | Project |
|---|---|---|---|
| H1 | Admin magic-link login broken (`proxy.ts` allow-list) | MYM-12 | 30-Day |
| H2 | Users can clear their own `crisis_detected` flag | MYM-11 | 30-Day |
| H3 | Crisis flag discarded by response regeneration | MYM-15 | 30-Day |
| H4 | Conversation summarisation dead (missing `OPENAI_API_KEY`) | MYM-28 | 30-Day |
| H5 | Unbounded history fetch once a summary exists | MYM-29 | 30-Day |
| H6 | Technique offers recorded as if completed | MYM-20 | 30-Day |
| H7 | Missing `state.accepted` treated as explicit decline | MYM-19 | 30-Day |
| H8 | Model-supplied technique/step IDs never validated | MYM-17, MYM-18 | 30-Day |
| H9 | System-prompt injection via unbounded `nickname` | MYM-30 | 30-Day |
| H10 | Font loading gates app with no failure path (mobile) | MYM-33 | 30-Day |
| H11 | No error boundary anywhere (mobile) | MYM-32 | 30-Day |

## Medium — main table (M1–M12)

| ID | Finding | Ticket | Project |
|---|---|---|---|
| M1 | 606 eslint problems / 419 errors, `--max-warnings=0` | MYM-92 | Backlog |
| M2 | 12 env vars missing from `turbo.json` `globalEnv` | MYM-85 | Backlog |
| M3 | Backend `__tests__` excluded from eslint | MYM-92 | Backlog |
| M4 | App-attestation fails open on unrecognized `APP_AUTH_MODE` | MYM-88 | Backlog |
| M5 | Decrypted provider API key serialized into RSC payload | MYM-72 | Backlog |
| M6 | No rate limiting on `messages.chat` | MYM-25 | 30-Day |
| M7 | Admin auth callback uses service-role key instead of anon | MYM-91 | Backlog |
| M8 | Open redirect via unvalidated `redirectTo` in auth callback | MYM-91 | Backlog |
| M9 | `clearTechniquePhase` self-undoing within a request | MYM-64 | Backlog |
| M10 | `title` schema max(50) vs consumer slicing to 100 | MYM-21 | 30-Day |
| M11 | `[ctx]` block persisted and replayed verbatim; forgeable | MYM-67 | Backlog |
| M12 | `composeSystemPrompt` silently omits missing layers | MYM-65 | Backlog |

## Medium — database second pass (unlabeled in source)

| Finding | Ticket | Project |
|---|---|---|
| Up to 8 independent writes per chat turn, no transaction | MYM-62 | Backlog |
| Two read-modify-write lost-update races (offered techniques, response styles) | MYM-63 | Backlog |

## Medium — test quality (unlabeled in source)

| Finding | Ticket | Project |
|---|---|---|
| No `coverageThreshold` in any jest config | MYM-22 (note) | 30-Day |
| Degradation paths exercised without asserting their logs | MYM-16 (note) | 30-Day |
| Unconditional `console.debug`/`warn` in production router | MYM-23 (note) | 30-Day |

## Low — main table (L1–L7)

| ID | Finding | Ticket | Project |
|---|---|---|---|
| L1 | `authenticated` holds `TRUNCATE`/`DELETE` table-wide | MYM-70 | Backlog |
| L2 | `ADMIN_EDITING_ENABLED` gates rendering only, not server actions | MYM-73 | Backlog |
| L3 | User can forge a second `[ctx]` block to spoof cooldown state | MYM-67 | Backlog |
| L4 | API key comparison leaks configured length before constant-time check | MYM-88 | Backlog |
| L5 | `cursor: z.string()` instead of validated datetime | MYM-89 | Backlog |
| L6 | Encryption: IV_LENGTH 16 vs GCM standard 12, no key version/AAD | MYM-90 | Backlog |
| L7 | `techniques_offered` dedupe fails on display-name vs id mismatch | MYM-20 (bundled) | 30-Day |

## Low — database second pass (unlabeled in source)

| Finding | Ticket | Project |
|---|---|---|
| 3 `SECURITY DEFINER` functions with unpinned `search_path` | MYM-8 (30-Day, `insert_message_pair`) + MYM-71 (Backlog, other two) | Both |
| 6 redundant indexes | MYM-87 | Backlog |
| 3 unindexed `NO ACTION` foreign keys | MYM-87 | Backlog |
| `supabase gen types` produces spurious Prettier-only diff | MYM-86 | Backlog |

## Low — test quality (unlabeled in source)

| Finding | Ticket | Project |
|---|---|---|
| Property-based generators emit unreadable random strings | MYM-86 | Backlog |
| `test/setup.ts` substring-match suppresses `console.error` too broadly | MYM-86 | Backlog |

## Configuration issues (numbered list, repo-audit.md)

| # | Finding | Ticket | Project |
|---|---|---|---|
| 1 | `turbo.json` `globalEnv` missing vars | = M2 → MYM-85 | Backlog |
| 2 | Backend tests excluded from eslint | = M3 → MYM-92 | Backlog |
| 3 | `design-tokens` no eslint config | MYM-85 | Backlog |
| 4 | Vestigial `turbo.json` build config + `packages/api` dead `dist` config | MYM-85 | Backlog |
| 5 | `vercel.json`/README Vercel root conflict | MYM-85 | Backlog |
| 6 | `next.config.js` missing `@mani/design-tokens` in `transpilePackages` | MYM-85 | Backlog |
| 7 | `eas.json` no build channels | MYM-79 | Backlog |
| 8 | `[inbucket]` deprecated in Supabase CLI | **Not ticketed — deliberate.** Original audit says leave as-is; renaming breaks older CLIs. |
| 9 | `apps/mobile/package-lock.json` tracked despite gitignore | MYM-86 | Backlog |
| 10 | `supabase/.branches`, `supabase/.temp` tracked at repo root | MYM-86 | Backlog |

## Docs that contradict the code (numbered list, repo-audit.md)

| # | Finding | Ticket | Project |
|---|---|---|---|
| 1 | Root `CLAUDE.md` navigation section is fictional | MYM-84 | Backlog |
| 2 | `prompts/title_generation.md` is dead | MYM-28 | 30-Day |
| 3 | `prompts/summarization.md` is dead | = H4 → MYM-28 | 30-Day |
| 4 | "Constraints last" invariant breaks once a summary exists | MYM-66 | Backlog |
| 5 | `buildUserContext` drops "topics" from documented context | MYM-68 | Backlog |
| 6 | `ExpoGO(Setup).md` lists unused `expo-auth-session` as a dependency | MYM-93 | Backlog |
| 7 | README/CLAUDE.md say Next.js 15; actual is 16 | MYM-93 | Backlog |
| 8 | README cites nonexistent `.tool-versions` | MYM-93 | Backlog |
| 9 | Backend CLAUDE.md documents unused var, omits `OPENROUTER_API_KEY` | MYM-93 | Backlog |
| 10 | `seed.sql`/`seed-prompts.ts` reference wrong script name and directory | MYM-93 | Backlog |
| 11 | `NarcissisticDynamics` category has no exercises | MYM-27 | 30-Day |

## Suggested order of work, item 7 (repo-audit.md)

| Finding | Ticket | Project |
|---|---|---|
| JWT-scoped `publicClient` so RLS becomes the authority | MYM-69 | Backlog |

---

## [[2026-09-08-mobile-review-and-consolidation]] — Mobile findings

| ID | Finding | Ticket | Project |
|---|---|---|---|
| MOB-1 | Session silently fails to persist on Android (SecureStore limit) | MYM-31 | 30-Day |
| MOB-2 | Font loading gates app, no failure path | = H10 → MYM-33 | 30-Day |
| MOB-3 | No error boundary anywhere | = H11 → MYM-32 | 30-Day |
| MOB-4 | `AuthProvider`'s `useMemo` never memoizes | MYM-53 | Backlog |
| MOB-5 | `ensureAuthenticated` has no in-flight guard | MYM-54 | Backlog |
| MOB-6 | Reads a config key that doesn't exist (`extra.apiUrl`) | MYM-55 | Backlog |
| MOB-7 | Background audio requested but not permitted (iOS) | MYM-52 | Backlog |
| MOB-8 | Ref mutated during render (`RootNavigator`) | MYM-56 | Backlog |
| MOB-9 | Six uncancelled `setTimeout`s in `ChatDrawer` | MYM-57 | Backlog |
| MOB-10 | `retry: false` globally on queries | MYM-58 | Backlog |
| MOB-11 | LOW cluster — 8 minor findings | MYM-59 | Backlog |

## Keep/Fix/Restructure/Replace section

| Finding | Ticket | Project |
|---|---|---|
| RESTRUCTURE 1 — JWT-scoped authorization | = MYM-69 | Backlog |
| RESTRUCTURE 2 — extract state machine / regen chain / atomic persistence | MYM-60, MYM-61, MYM-62 | Backlog |
| RESTRUCTURE 3 — model-output trust boundary | = H8 → MYM-17, MYM-18 | 30-Day |
| RESTRUCTURE 4 — `[ctx]` block out of message body | = M11/L3 → MYM-67 | Backlog |
| RESTRUCTURE 5 — split `AuthProvider` into state/actions contexts | MYM-96 | Backlog |
| REPLACE — `firebase-admin`/App Check | MYM-75 | Backlog |
| REPLACE — Expo SDK 54→57, `expo-av`→`expo-audio` | MYM-76 | Backlog |
| REPLACE — hand-rolled `.env`-parsing publish script → `eas env` | MYM-95 | Backlog |
| Dead files (~19) / unused deps (11+5) / hoisted-only deps (4) | MYM-77 | Backlog |
| Reanimated version mismatch | **Not ticketed — ruled out.** Confirmed inert; audit says do not chase. |

---

## [[2026-09-09-fast-api-infra-from-scratch]]

| Finding | Ticket | Project |
|---|---|---|
| `supportStyle` captured at onboarding, never reaches the system prompt | MYM-50 | Backlog |

---

## Store readiness (not in original audit — identified during DEV-START planning)

| Item | Ticket | Project |
|---|---|---|
| Missing `googleServicesFile` blocks EAS builds | MYM-78 | Backlog |
| Account deletion reachability | MYM-80 | Backlog |
| App Store / Play Store privacy disclosures | MYM-81 | Backlog |
| iOS privacy manifest (`PrivacyInfo.xcprivacy`) | MYM-82 | Backlog |
| Data retention policy + enforcing migration | MYM-83 | Backlog |
| Access logging on admin transcript viewer | MYM-74 | Backlog |
| Next.js's own 14 high-severity advisories | MYM-94 | Backlog |

## Conversational design (identified during this planning pass, not the original audit)

| Item | Ticket | Project |
|---|---|---|
| Define + wire per-style conversational flow (supportive/reflective/direct) | MYM-50 | Backlog |
| iOS/Android UI-UX parity audit | MYM-51 | Backlog |
| iPad responsive layout | **Not ticketed** — explicitly declined by muhammad (rejected the tool call) |

### Conversational design, second pass (2026-09-11 — read the live prompt files + `messages.ts` again, not just the original audit)

| Item | Ticket | Project |
|---|---|---|
| Shape/voice repetition has no server-side check, unlike duplicate-technique/phase-skip which do | MYM-97 | Backlog |
| No tie-break rule when both Thought Reframing and ABCDE indicators are present | MYM-98 | Backlog |
| "Conversation end" library-offer branch has no code signal to trigger on — pure LLM inference, untestable | MYM-99 | Backlog |
| No regression suite for conversational-flow prompt rules despite 4 recent fix commits to the same files | MYM-100 | Backlog |

---

## [[2026-09-13-fundamental-review]] — NOT YET TICKETED

27 findings (`FR-1`–`FR-27`) covering missing subsystems rather than defective ones: the crisis
path's content and escalation, regulatory posture (account deletion, policy documents, subprocessor
data terms, retention, age scope, claims language), and system governance (no message→prompt-version
link, no cost accounting, no error tracking, orphaned eval suite).

**This section is deliberately unmapped.** Triage these into the 30-day plan and the backlog, then
replace this block with a finding-to-ticket table like the ones above.

---

## Known non-gaps — checked, deliberately not ticketed

Recorded so these don't get re-flagged as "missing" on a future pass:

- **`[inbucket]` deprecation warning** — leaving the config section name as-is is correct; renaming breaks Supabase CLI versions older than 2.117.
- **`react-native-reanimated` version mismatch** — confirmed inert three independent ways (no imports in `apps/mobile/src`, bundle only contains the unrelated `react-native-reanimated-table`). The original audit explicitly says not to chase this.
- **`metro.config.js` `disableHierarchicalLookup`** — intentional, required by the hoisted pnpm layout. Audit says document, not fix.
- **iPad-compatible layout** — was going to be ticketed, muhammad rejected the tool call live. Not in either project on purpose.

---

## Coverage check procedure

To verify this file is still complete after new audit work or new tickets:

1. Re-read each of the five source journal notes in full.
2. For every severity-tagged item (C#, H#, M#, L#, MOB-#) and every numbered list item, confirm a row exists above.
3. For every ticket created in Linear since this file was last updated, confirm it traces back to a row here (or add a new section if it's net-new work, like Store Readiness above).
4. Update the file in the same sitting — a stale cross-reference is worse than no cross-reference, because it creates false confidence.
