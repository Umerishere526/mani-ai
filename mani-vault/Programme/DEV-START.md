# DEV START — road to production, live users, and the store releases

> **New here? Read [[START-HERE]] first.** It carries the current route, the phase order, and
> the first file to write. This document is the deeper programme roadmap behind it.

> **For agentic workers:** this is a **program roadmap**, not a task-level implementation
> plan. Per-stage plans with bite-sized TDD steps get written when that stage starts, using
> `superpowers:writing-plans`, against code read fresh at that time. Do not treat the
> stage bodies here as executable step lists.

Undated filename on purpose — this is a living document, updated as stages close, not a
session note. Companions: [[2026-09-08-repo-audit]] (findings),
[[2026-09-08-technical-assessment]] (judgment), [[2026-09-08-mobile-review-and-consolidation]]
(verdict + order of work), [[2026-09-09-fast-api-infra-from-scratch]] (the AI service split),
[[2026-09-13-fundamental-review]] (what the audits did not look for),
[[2026-09-14-architecture-decisions]] (decisions), [[ai-service-contract]] (the v1 contract).

> **Substantially revised 2026-09-14.** The sequencing below was written before
> [[2026-09-13-fundamental-review]] found that the crisis path does not function and that
> in-app account deletion does not exist, and before the decisions in
> [[2026-09-14-architecture-decisions]]. Where the two disagree, the decisions document wins.
> The headline changes: the crisis path comes before everything (it is product work, not AI
> work), the database is rebuilt from scratch rather than migrated, and the FastAPI split moves
> to fourth in the order rather than first.

**Goal:** get Mani to a state where it can carry real users on both stores, with security
and safety enforced server-side, an admin portal that is actually usable and authoritative,
and the AI layer running as an independent FastAPI service.

**Tech stack:** unchanged where it is correct — Expo/React Native, Next.js, tRPC + zod,
Supabase/Postgres, Turborepo. Adding: FastAPI (Python) for the AI/agent layer, CI, error
tracking, rate limiting, a staging environment.

---

## The headline, stated plainly

**This cannot take live users or go to store review in its current state**, and the reason
is not polish. Verified against the working tree today (2026-09-10, all three re-checked
because the audit was two days old):

- **C1 is still live.** `packages/api/src/routers/messages.ts` still calls
  `ctx.services.messages.list(input.threadId, input.limit, input.cursor)` with no
  `ctx.userId`. The audit reproduced this: signed in as one user, read another user's full
  transcript including a suicidal-ideation disclosure.
- **C3 is still live.** `crisisDetected: false` is still hardcoded at
  `apps/backend/src/services/messages.ts:351` and `:1602`, and `chat()` still never reads
  `thread.crisisDetected` on entry. The crisis lock exists only in `ChatScreen.tsx:299`.
- **There is still no CI.** No `.github` directory.

Add C4 (an *unauthenticated* caller can reach `insert_message_pair` and write forged
`role: 'mani'` turns into a stranger's conversation) and the picture is: in a mental-health
product, cross-user readable transcripts, forgeable therapist turns, and an advisory-only
crisis lock. Those are reasons not to have real users yet, not backlog items.

**The asymmetry that sets the whole order of work:** every server-side fix deploys
instantly and rolls back instantly. A binary in users' hands does not — store review adds
days, and you cannot recall a build. So store submission is the *last* gate, not the first,
and nothing ships to a store until the safety and authorization model is server-authoritative.

---

## The argument for not doing FastAPI first — recorded, not accepted

> **Resolved 2026-09-14 — the ordering was revisited and changed.** The FastAPI split is still
> happening; it now sits fourth in the order rather than first, behind the crisis path, the
> schema rebuild, and the regeneration-cost fix. The four risks below are what drove that, and
> risk 1 in particular was sharpened: the thing worth moving is not `llm.ts` (a provider
> adapter) but the six repair loops in `messages.ts` — and those should become deterministic
> code rather than model calls, which removes most of the reason to move them at all. See
> [[2026-09-14-architecture-decisions]].

Recorded in [[2026-09-09-fast-api-infra-from-scratch]]: scope is AI/agent only, protocol is
REST/JSON, driver is tool calling and growth into an agent. That decision stands. *(SSE was
part of the original protocol decision and was dropped 2026-09-14 — no streaming in v1.)*
Its **position in the sequence** is the thing this document adds, and it argues against
building it now:

1. **The thing you would be moving is not yet movable.** `services/messages.ts` is ~1,600
   lines of procedural flow with six regeneration triggers, a technique state machine
   encoded in six nullable `threads` columns, and eight non-transactional writes per turn.
   Porting that across a network boundary into a second language does not simplify it — it
   relocates it somewhere harder to debug, with a language boundary in the middle. Decompose
   it in TypeScript first, behind the 666 existing tests, then move a clean boundary.
2. **Tool calling makes the #1 product-safety defect worse.** H3 already proves the
   self-reported `crisis` field gets silently dropped when a cosmetic regeneration replaces
   the response object. Every additional model round-trip is another place it can be lost.
   Adding tool-calling rounds on top of a droppable safety signal multiplies the failure
   mode. Crisis must be authoritative *before* the agent work, not after.
3. **Unvalidated model output is already causing damage.** `prompts[].technique` is
   `z.string().optional()` and `state.technique` is used directly as
   `TECHNIQUE_PHASES[technique]`. Tool calling vastly expands what the model asserts (tool
   names, arguments, ids). Closing that trust boundary is a prerequisite, not a follow-up.
4. **Per-turn cost is already unbounded and unmeasured.** Up to six LLM calls per turn
   against a ~34 KB system prompt, no rate limiting, no cost telemetry, and once
   summarisation fails the history fetch loses its `.limit()`. Agent loops multiply turns.
   Building the agent before there is a retry budget and cost telemetry means finding out
   from the OpenRouter bill.

So: **FastAPI comes after the chat core is sound, and before the store release.** It is
Stage D below, with a strangler constraint that makes an AI-first order survivable.

*2026-09-14: this conclusion held, and the order was tightened further. The current order is
crisis path → schema rebuild → kill the regeneration waste → ai-service v1. Stage D's scope
also changed: the service is stateless and the backend keeps persistence, so the orchestrator
does not move. See [[2026-09-14-architecture-decisions]] and [[ai-service-contract]].*

---

## The chat core — what must be solved, in dependency order

This is the part muhammad flagged as the product itself, so it gets the most precise
ordering. Each item states why it must precede the next.

### 1. Crisis becomes server-authoritative — C3, H3, H2

The safety control, and a hard prerequisite for everything agentic.

- Gate `chat()` on `thread.crisisDetected` at entry; stop returning `crisisDetected: false`
  for a thread already flagged (`services/messages.ts:351`, `:1602`).
- Move the crisis check **ahead of** the regeneration pipeline, or carry the `crisis` field
  forward across retries so a quality retry cannot discard it (H3).
- Column-restrict the `threads` UPDATE grant so a user cannot `PATCH crisis_detected` back
  to false (H2).
- This is the one code path that warrants near-100% branch coverage. None of the
  regeneration paths are currently covered at all.

**Why first:** it is the highest-consequence defect in the product, and items 4 and Stage D
both add model round-trips that can drop the signal.

### 2. Model-output trust boundary — H8, H7, M10

Every model-supplied value that becomes a key, an index, a persisted enum, or a
control-flow input gets validated against a closed set at the boundary.

- `state.technique` / `state.step` → zod enums, not object index keys. Today an unknown
  technique makes `validatePhaseTransition` return `{isValid: true}`, and the prototype-key
  case (`"toString"`) was flagged as a suspected 500.
- H7: absence of `state.accepted` is currently treated as an explicit decline, which nulls
  phase tracking mid-exercise. Make it a real tri-state.
- M10: `title` is `.max(50)` in the schema but sliced to 100 downstream — a 55-char title is
  a hard `generateObject` failure, so the user loses the entire turn over a thread label.

**Why second:** it is the prerequisite for tool calling, and it is cheap.

### 3. Extract the technique state machine — RC3, H6, L7

Its own module with an explicit, validated transition table. **Write the tests against it
before moving it** — the existing suite is the safety net and this is where it earns out.

Fix while extracting:
- **H6 is a conversation-quality bug, not just a data bug.** A merely *offered* technique is
  written to `techniques_offered`, which is rendered to the model as "already tried — do NOT
  offer again" and used as the duplicate-regeneration blocklist. With only two techniques in
  the library, one declined offer of each **permanently exhausts both for the rest of the
  thread** — and if the user later asks for one by name, the model's correct offer trips the
  duplicate check and gets regenerated away. Worth checking whether this is what recent
  prompt-tuning has been fighting.
- L7: `techniques_offered` receives both display names (`"ABCDE"`) and ids (`"abcde"`) and
  dedupes by exact string, so the same technique gets listed twice.

**Why third:** the regeneration triggers read state-machine state, so this must be a
testable unit before item 4 touches them.

### 4. Regeneration → a policy chain with a retry budget

**Six** ad-hoc trigger sites, each restarting from the pristine message array, up to six LLM
calls per turn — and with the AI SDK's own `maxRetries: 2` on top, a worst case of ~21 provider
calls for one user message, measured at ~570K tokens across three messages. Replace with one
named policy chain, an explicit retry budget, and a single re-validation pass.

*Revised 2026-09-14: all six checks are **deterministic post-checks** — dedupe an array, strip a
string, correct the `state` field. None needs a model call at all. Do this in TypeScript before
the port; it is roughly a 20× cost reduction and there is no sense porting the expensive
version. See [[ai-service-contract]].*

**Why fourth:** depends on 3, and must precede Stage D — agent tool rounds and regeneration
rounds compound multiplicatively on both latency and cost.

### 5. Turn persistence becomes atomic

Extend the existing `insert_message_pair` RPC (or wrap in one transaction) to cover the
message pair *and* the thread-state writes — currently one atomic write followed by eight
unprotected ones. Replace the two read-modify-write array appends
(`addTechniquesOffered`, `appendResponseStyle`) with single-statement `array_append` /
jsonb concatenation to close the lost-update races.

**Why fifth:** it touches every write site items 1-4 move, so it goes last among the
orchestrator work. An agent loop with mid-flight state makes partial-write states much more
likely, so this must land before Stage D.

### 6. Context continuity — H4, H5 (parallelizable with 3-5)

- **Summarisation is dead** in any deployment following `.env.example`: `summary.ts` requires
  `OPENAI_API_KEY`, which is not in that file, and the throw is swallowed by a background
  catch. So from turn 21 the model has no knowledge of the first half of the conversation.
  For an emotional support product, forgetting what someone told you twenty messages ago is
  a core product failure, not a nice-to-have.
- The seeded `summarization` prompt is never read by any code path — editing it and
  re-seeding does nothing. Decide: wire it up, or delete it and stop documenting a workflow
  that has no effect. Same for `title_generation.md`.
- H5: once a summary *does* exist, the history fetch drops its `.limit()`, so a thread with
  a stale checkpoint sends every message after it on every turn, unbounded.

**Why parallel:** different code path from the orchestrator internals, so it does not
contend with 3-5.

---

## Constraints, confirmed 2026-09-10

These change the sequencing below, so they are recorded before it:

- **Solo build.** Others advise; nobody else writes code. The stage estimates inherited from
  [[2026-09-08-mobile-review-and-consolidation]] assumed a team — read them as months of
  calendar time, not weeks.
- **Inherited codebase.** Built by a previous developer from roughly January to March 2026;
  muhammad picked it up after. This is why every assessment lands on repair rather than
  rewrite: the expensive layers (module boundaries, the tRPC contract, the schema, the
  encryption) are sound.
- **No live users.** Beta testers only, on local-style setups. C1 and C4 are therefore
  *not* an active incident with disclosure implications — they are must-close-before-anyone-real.
  Still worth closing immediately, because together they are about half a day.
- ~~**AI-first by choice.**~~ **Revised 2026-09-14.** The AI-first ordering was reopened and
  changed. The FastAPI split proceeds, but fourth: after the crisis path, the schema rebuild,
  and the regeneration-cost fix. Two things drove the change — [[2026-09-13-fundamental-review]]
  found the crisis path non-functional (four help links with no handler, an empty-string reply,
  escalation still a TODO), and none of that work lives in the layer being moved, so deferring
  it behind a months-long migration buys nothing.
- **Beta data is disposable.** Confirmed 2026-09-14. This is what makes the schema rebuild
  possible, and that window closes permanently once real users exist.
- **Non-technical people will edit prompts.** Confirmed 2026-09-14. This decides the prompt
  source-of-truth question (open question 5) in favour of the admin portal, and turns portal
  governance into required work rather than a nicety.

## Sequencing — solo

Revised from the team-shaped Phase 0-4 ordering. Each stage is independently shippable.

> **Superseded in part, 2026-09-14.** The current order is: **crisis path and store blockers →
> schema rebuild (with RLS) → kill the regeneration waste → ai-service v1 → cut over → v2
> registry and tools → v3 worker.** The stages below remain accurate as descriptions of the
> work; what changed is their order and, for Stages D and F, their scope. Stage A's exploit
> fixes now ride along with the crisis path since both are small server-side diffs.
> [[2026-09-14-architecture-decisions]] carries the reasoning.

### Stage A — Close the exploits · about half a day · before any Python is written

Small diffs, no refactoring, and no reason to carry them while building something new on
top:

1. C1 — pass `ctx.userId` through `messages.list` → service → `getForThread` (~5 lines)
2. C4 — `auth.uid()` validation inside `insert_message_pair`; revoke `anon` EXECUTE
3. C2 — `WITH CHECK` on `messages` INSERT validating thread ownership
4. H2 — column-restrict the `threads` UPDATE grant
5. H1 — allow-list `/admin/auth/callback` in `proxy.ts` (one line; magic-link admin login
   is currently dead and password login masks it)

Items 1-4 are independent of each other and close both reproduced exploits.

### Stage B — Prerequisites of the AI work · first tasks of the agent build

These are not general remediation deferred into the AI track — they are load-bearing for
tool calling, and would have to be written anyway. Doing them first avoids building the
agent on top of a known-broken control-flow boundary and then redoing it.

- **Chat-core item 1, crisis server-authoritative** (C3, H3, H2). An agent loop is
  regeneration with more steps. H3 already proves the self-reported crisis field is dropped
  when a retry replaces the response object; more round-trips means more drops.
- **Chat-core item 2, model-output trust boundary** (H8, H7, M10). Tool calling *is* model
  output used as control flow. `state.technique` is already an unvalidated object index —
  extending that pattern to tool names and arguments compounds the same defect in the same
  code.

### Stage C — Minimum operational floor · deliberately narrower than the team-shaped list

Solo and pre-launch, most of the original "build the net" list can wait. These four cannot,
because an agent has more failure modes and more cost surface than what exists today:

- **Error tracking** on the backend. You cannot debug an agent in production without it, and
  an agent fails in more ways than a single model call.
- **Cost telemetry** — tokens and LLM call count per turn, before agent loops multiply the
  current six-calls-per-turn ceiling.
- **Rate limiting** on `messages.chat` (`ctx.deviceId` is already collected and unused).
- **Minimal CI** — a GitHub Action running `tsc --noEmit` plus the test suites. An hour of
  work, and it is the safety net for every refactor in Stage E.

**Explicitly deferred while solo:** `pnpm lint` to zero (419 errors, days of work, no
functional gain right now — leave the gate out of CI until the errors are cleared), a
staging Supabase project, and mobile error tracking. Revisit all three before Stage H.

### Stage D — FastAPI: strangle `llm.ts` first, not `messages.ts`

> **Revised 2026-09-14.** The instinct below was right but the framing was wrong. `llm.ts` is a
> provider adapter, not the AI layer — the agent logic is the six repair loops in `messages.ts`.
> Settled scope now lives in [[ai-service-contract]]: ai-service owns prompt composition, the
> model call, and output validation; it is **stateless** and the backend keeps every database
> write, so the orchestrator does not move. Also decided: no streaming in v1, the OpenRouter key
> lives in ai-service's environment rather than the database, prompt content is read from
> Postgres read-only, and background work runs as a second process type in the same Python
> codebase rather than a separate service. Before any of this, kill the regeneration waste in
> TypeScript — worst case is ~21 provider calls per turn today, and there is no sense porting
> the expensive version.

The load-bearing decision for this stage. **Move the model call, not the orchestrator.**

`apps/backend/src/services/llm.ts` is thin and contained: a composed prompt goes in,
structured JSON comes out. Moving it to FastAPI is self-contained and testable, and the
TypeScript orchestrator keeps working — it simply calls Python for the model call instead of
the AI SDK. Tool calling then gets built in Python incrementally, and `services/messages.ts`
shrinks as the agent grows.

Starting from the orchestrator instead forces a choice between porting ~1,600 tangled lines
to Python in one move, or running two chat implementations side by side and reconciling them
later. Both are bad, and both are especially bad solo.

Design questions from [[2026-09-09-fast-api-infra-from-scratch]] that must be answered
before writing Python. **All but two are now resolved** — see [[ai-service-contract]]: no
streaming in v1; the service is stateless; summarisation moves as `POST /v1/summarize`; prompt
composition lives in ai-service, reading the prompt tables read-only. **Still open:** the
hosting platform (a container platform — Fly/Railway/Cloud Run — **not** Lambda-style, which
reproduces the timeout ceiling being escaped, and it must support two process types from one
image), and whether `AI_DEBUG_MODE` reasoning output survives for the `conversation-test` skill.

Also settled there: tools read Supabase read-only and never call back into Next.js, and
signed-URL generation stays in `services/exercises.ts` with the agent returning ids.

Parity gate: run `conversation-test` / `conversation-review` before and after each move and
require equivalent behaviour. The tooling already exists; use it as the acceptance bar.

### Stage E — Chat core decomposition · as the agent grows

Chat-core items 3-6, in that order: extract the technique state machine (tests first),
regeneration becomes a policy chain with a retry budget, turn persistence becomes atomic,
context continuity (H4/H5) in parallel.

Under the strangler approach these are not a separate phase so much as the work that
progressively empties `services/messages.ts` as logic moves into the Python agent. The
dependency order still holds: the state machine must be a testable unit before the
regeneration triggers that read it are touched, and atomic persistence goes last because it
touches every write site the earlier items move.

### Stage F — Make Postgres the authorization authority

- Build the per-request `publicClient` from the **user's JWT** rather than the service-role
  key, so RLS applies on the app path. Reserve service-role for genuinely cross-user admin
  work, injected under a distinct name so its use is visible in review.
- Then revoke table-level DML from `authenticated` once the above is proven — the code says
  mobile never talks to PostgREST directly, so this eliminates the whole C2/H2/L1 class.
- Pin `search_path` on the three `SECURITY DEFINER` functions.

This converts "every method must remember a `userId` filter" into "the database enforces
it", making C1 structurally impossible rather than individually patched. Stage A patches the
symptom; this removes the class.

~~**Do not attempt this without a staging environment**, which Stage C deferred. Bring the
staging Supabase project back before starting here — this is the single riskiest migration
in the document and rehearsing it is not optional.~~

**Revised 2026-09-14 — this stage moves early and its risk largely disappears.** Beta data is
disposable, so the database is being rebuilt from scratch rather than migrated
([[2026-09-14-architecture-decisions]] #1). RLS therefore gets *written correctly the first
time* instead of migrated under traffic, which was the entire source of the risk. Do it as part
of the schema pass. This window never gets cheaper, and it is the change that makes C1
structurally impossible rather than individually patched.

### Stage G — Admin portal: live, authoritative, and in sync

Called out because "live and perfectly set up" is not the current state:

- H1 — magic-link login is broken (Stage A fixes it); password login works, which is why
  nobody noticed
- M5 — the decrypted provider API key is serialized into the RSC payload; `ProviderForm` is
  a client component receiving the whole `provider` object, so the plaintext key reaches the
  browser even though the field renders empty
- L2 — `ADMIN_EDITING_ENABLED` gates only rendering; the five mutating server actions never
  check it, so an admin can POST directly
- No access logging on the transcript viewer. For this product category that is not optional
- M7/M8 — the auth callback uses the service-role key where every comparable path uses anon,
  and builds a redirect from an unvalidated query param
- **The prompt sync loop is undefined** — see open question 5 below

### Stage H — Store release · last, because it is the only irreversible step

Not covered anywhere in the existing journal, so recorded here. Verify each against current
store policy at submission time rather than trusting this list:

- **EAS build fails today.** `app.json` references `googleServicesFile` twice and those
  files are absent from the repo. Hard blocker for any store build.
- `eas.json` defines three build profiles with **no `channel` on any**, while `app.json`
  sets `updates.url` — OTA mapping is unwired, and `expo-updates` is itself unused and
  version-skewed between root and mobile.
- MOB-7 — `UIBackgroundModes: ["audio"]` is missing while the player requests
  `staysActiveInBackground: true`. Meditation audio will stop on lock/background on a real
  build. Invisible in Expo Go. Decide deliberately: add the mode, or set the flag false.
- **In-app account deletion** — Apple requires it where account creation exists. The DB
  cascade is correct and verified; confirm it is actually reachable from the UI.
- **Privacy disclosures** (App Privacy / Play Data Safety) must be accurate about storing
  mental-health conversation content — sensitive-category data.
- **iOS privacy manifest** (`PrivacyInfo.xcprivacy`) for required-reason APIs and
  third-party SDKs.
- **Health-app review scrutiny.** An emotional-support app that claims crisis detection will
  get reviewer attention on whether the crisis path actually works and whether helpline
  resources are surfaced. C3 must be closed long before this — which it will be, at Stage B.
- Expo SDK 54 → 57 as one deliberate unit migration (`expo-av` → `expo-audio` comes with
  it), and re-derive or retire the `react-native` patch. Do **not** bump Expo packages
  individually.
- `firebase-admin` carries four of the six critical advisories for App Check, which is off
  by default and whose client side is an unimplemented TODO. Implement it or remove it —
  carrying it as-is is not defensible either way, and it is a poor thing to ship.

### Stage I — Governance, ongoing

Data-retention policy plus an enforcing migration; log redaction; LLM cost telemetry
(tokens and call count per turn, alerting on regeneration rate); correcting the fictional
navigation section in root `CLAUDE.md`; deleting or wiring the two dead prompt files.

Item: **the doc corrections are the cheapest thing on this entire list and can be done at
any time.** In an AI-assisted codebase every session ingests `CLAUDE.md` as ground truth, so
a false statement there is an active defect.

---

## Open questions — these gate real planning

1. ~~Are there already live users?~~ Resolved — beta testers only, no live users. See
   Constraints above.
2. ~~Does the FastAPI split come before or after the chat core?~~ Resolved twice. First as
   AI-first; then **revised 2026-09-14** — the split proceeds but sits fourth, behind the crisis
   path, the schema rebuild, and the regeneration-cost fix. Scope settled in
   [[ai-service-contract]].
3. ~~Solo or team?~~ Resolved — solo.
4. **Still open, and it gates Stage H: what is the regulatory and claims posture?** Is Mani
   positioned as wellness, or does any copy make a clinical or therapeutic claim? This drives
   GDPR special-category handling, whether a DPA is needed, and how store review treats the
   app. It also determines whether "therapy transcripts" is the right framing for the stored
   data. Note that `techniques.md` already implements two named CBT protocols
   (`thought_reframing`, ABCDE), so the prompts themselves carry therapeutic framing whether
   or not the store listing does — those need to agree before submission, because
   inconsistency between listing, copy, and behaviour is what gets a health-app review
   rejected. Worth asking one of the people advising muhammad who has legal or clinical
   standing, not settling from engineering judgment.
5. ~~**Which direction wins for prompts — markdown or the admin portal?**~~ **Resolved
   2026-09-14: the admin portal is the source of truth; markdown becomes bootstrap-only for a
   fresh database.** The deciding factor was confirmation that non-technical people will add
   prompts over time — git-as-source would lock them out. Consequences, all now required work:
   `db:seed` must refuse to run against a populated database; the version-snapshot write must
   become fatal rather than silently publishing while losing history; deletion must stop
   cascading version history away; and the portal needs draft → publish plus a preview that
   runs the evals. See [[2026-09-14-architecture-decisions]] #7 and #8.
6. **Is there a per-user LLM cost ceiling?** Up to six regeneration calls per turn today, and
   with the SDK's own retries a worst case of ~21 provider calls per message. Agent loops would
   multiply it, and there is no rate limiting or telemetry. A number here shapes the retry
   budget in chat-core item 4. **Still open.**
7. **Who operates the admin portal, and does transcript access need an audit trail for
   compliance rather than just good practice?** Affects how much Stage G weighs.
8. **Did the Thursday deliverable in [[2026-09-08-mobile-review-and-consolidation]] happen,
   and did anything come out of it that changes priorities?** Context I do not have.

---

## Verified today (2026-09-10)

Re-checked rather than trusted, because the audit is two days old and the only commits since
are prompt work:

| Claim | Status |
| --- | --- |
| C1 — `messages.list` omits `ctx.userId` | **Still live**, confirmed in `packages/api/src/routers/messages.ts` |
| C3 — `crisisDetected: false` hardcoded | **Still live** at `services/messages.ts:351` and `:1602` |
| CI exists | **No `.github` directory** |
| Exercise library size | 18 exercises |
| Prompt corpus size | 5,731 words across five files (~7-8k tokens) |
| Runtime prompt source | The **database**, via `promptsDb.list()` cached in `services/prompts.ts:46-67`; markdown is seed input only |
