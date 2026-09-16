> **ARCHIVED — evidence, not instructions.** Point-in-time record. Parts of this are
> superseded; see `README.md` in this folder for exactly which. Current instructions live
> in `../START-HERE.md`, and where the two disagree, that one wins.

# Mani — Technical Foundation Assessment

Prepared for review. Covers the mobile application, backend, database, dependencies,
deployment configuration and documentation, with a recommended remediation plan.

---

## 1. Bottom line

**The foundation is sound. The security model is not, and needs work before this product
should carry real users.**

Those two statements are both true and they are not in tension. The parts of a system that
are expensive to change later — the data model, the module boundaries, the contract between
app and server — are in good shape here. The problems are concentrated in a small number of
implementation decisions, the most damaging of which is fixed by *switching on protection
that has already been built and is sitting unused*.

We identified **four critical, eleven high, and roughly forty lower-severity findings**. Two
of the critical findings were confirmed by reproducing them against a running instance
rather than inferred from reading code.

**We do not recommend a rebuild.** Section 5 sets out why, in terms of the architecture
rather than as an assertion. That recommendation held after every stage of the review,
including the final mobile pass.

**What we do recommend** is a four-phase programme, beginning with a short, tightly scoped
set of fixes that close the confirmed data-exposure issues — days of work, not weeks —
followed by the operational groundwork that must exist before the larger structural change
is safe to attempt.

---

## 2. What was examined, and how

| Area | Basis of assessment |
| --- | --- |
| Mobile application (React Native / Expo) | 114 source files; the twelve largest read in full, the remainder covered by static analysis and targeted pattern checks |
| Backend (Next.js, tRPC) | All service, data-access, security and routing code read directly |
| Database | All 24 migrations plus live verification of schema, policies, privileges, indexes, functions and triggers against a running instance |
| Dependencies | Full dependency graph, vulnerability audit, framework version validation |
| Deployment & infrastructure | Every configuration file in the repository |
| Documentation | All project documentation compared against actual code behaviour |

Findings were verified rather than assumed. Where a conclusion rests on reading code but
was not executed, this document says so. Where behaviour was reproduced against a running
system, it is marked **confirmed**.

The one area we were unable to complete was per-method error handling inside the backend
service layer. We expect this would add further moderate findings; we do not expect it to
change any conclusion in this document.

---

## 3. How to read the severity ratings

This matters, because "four critical findings" invites the wrong conclusion.

Severity here measures **consequence if exploited**, not **structural depth**. A finding is
critical because the data involved is sensitive, not because the system cannot express the
fix. The four critical findings are, in remediation terms, changes of roughly five to ten
lines each, plus two database policy changes.

That is the central observation of this assessment: **the defects are severe in consequence
and shallow in structure.**

---

## 4. Findings requiring a decision

The complete register runs to fifty-plus items. Below are the ones that need a decision
from you, rather than simply being scheduled. Each carries a recommended course, an
alternative where there is a genuine trade-off, and the reasoning.

---

### 4.1 Access controls are enforced in application code rather than by the database

**Severity: Critical** · Confirmed

The system authenticates users correctly, then queries the database using a privileged
connection that deliberately bypasses the database's own row-level security. Protection
therefore depends on every individual data-access method remembering to filter results to
the signed-in user.

Row-level security policies **do exist in this database and are correctly written**. They
are simply never consulted on the application's own code path.

Two methods did not apply the filter. We confirmed that one of them allows a signed-in user
to retrieve another user's complete conversation history, including sensitive disclosures.
A second issue in the same family allows writing into another user's conversation.

**Recommended solution.** Construct the per-request database connection from the signed-in
user's own credentials, so row-level security applies automatically to every query. Reserve
the privileged connection for genuinely administrative operations, under a distinct name so
its use is visible in code review. Then tighten the table-level permissions granted to
signed-in users, which are currently broader than the application needs.

**Alternative, with the trade-off stated.** Audit every data-access method and add the
missing filters, leaving the architecture unchanged. This is faster to implement and lower
risk in the short term. The trade-off is that it fixes the two known instances without
fixing the cause — correctness continues to depend on every future method remembering, with
no mechanism to catch a lapse. Given that the review found two lapses in the current code,
we do not think that assumption is safe to keep.

**Reasoning.** The recommended change is small — a different construction of one object,
plus permission changes — but it moves enforcement from a convention that must be
remembered to a control that cannot be forgotten. It also works *with* the existing design
rather than against it: the policies are already written and correct. This is the highest-
leverage change in the entire assessment.

**Recommendation: do the immediate filter fixes now (Phase 0) and the structural change in
Phase 2.** These are complementary, not alternatives — the first stops the exposure this
week, the second prevents its recurrence.

---

### 4.2 A database function is callable without authentication

**Severity: Critical** · Confirmed reachable

A database function introduced to make message writes properly atomic runs with elevated
privileges, accepts the user and conversation identifiers as parameters, and performs no
validation that the caller owns either. Execution permission was granted more broadly than
intended, including to unauthenticated callers.

We confirmed the function is reachable without authentication. We did not write any data;
the probe was constructed to fail at a database constraint precisely so that nothing would
be modified.

**Recommended solution.** Add ownership validation inside the function and withdraw
execution permission from unauthenticated callers.

**Alternative.** None worth presenting. This is a small, self-contained correction with no
design trade-off.

**Reasoning.** Worth noting for context rather than blame: this function was added to solve
a genuine correctness problem — ensuring a user message and its response are stored
together or not at all. That reasoning was sound and the atomicity it provides should be
kept. The permissions attached to it were the error, not the approach.

---

### 4.3 The crisis safeguard is enforced in the mobile app

**Severity: Critical** · Confirmed by code review

When the system detects that a user may be at risk, it records this and instructs the app
to stop accepting further messages on that conversation. The check that actually stops the
conversation exists **only in the mobile application**. The server does not refuse
requests on a flagged conversation, and in fact reports the conversation as unflagged on
its normal response path. Separately, the flag itself can be altered by the user, because
table permissions are broader than intended.

There is also a related issue in how the flag survives internal retries: the system
regenerates a response in several circumstances — for instance if the first attempt
included formatting that should not reach the user — and a regenerated response can
silently lose the risk signal the first attempt carried.

**Recommended solution.** Make the server the authority: refuse further messages on a
flagged conversation at the API boundary, stop reporting a flagged conversation as
unflagged, restrict which fields a user may modify, and ensure the risk signal is
evaluated before any regeneration can discard it.

**Alternative, with the trade-off stated.** Keep enforcement in the app and simply correct
the reported flag and the field permissions. This is less work. The trade-off is that the
safeguard remains dependent on the client behaving correctly — which does not hold for an
out-of-date app version, a failed network response, or any non-app caller.

**Reasoning.** We rate this critical on product and duty-of-care grounds as much as
security grounds. For a product in this category, a safeguard that a client can decline to
apply is not a safeguard. The server-side fix is a guard clause at one entry point plus a
permissions change — this is inexpensive relative to its importance.

---

### 4.4 Conversation memory is not working as designed

**Severity: High** · Confirmed by code review

The system is designed to summarise older parts of a conversation so the assistant retains
context beyond the most recent messages. In practice this feature requires a credential
that is not listed in the project's own environment template, the resulting error is
suppressed, and no summary is ever produced. Conversation history is therefore capped at
the most recent messages with nothing replacing what falls away.

A second, related issue: once a summary *does* exist, the query that loads history has no
upper bound, so cost per message grows without limit as a conversation lengthens.

**Recommended solution.** Decide which provider should perform summarisation — the code and
the project's own configuration currently disagree — align the two, add the missing bound,
and stop suppressing the failure so it is visible if it recurs.

**Alternative.** Disable the feature explicitly until it is wanted. This is legitimate and
honest, and preferable to the current state where the feature appears configured but does
nothing. The trade-off is a known product limitation on long conversations instead of an
unknown one.

**Reasoning.** Either option is acceptable. The unacceptable state is the present one,
where the behaviour is invisible: nothing in the system reports that memory is not working.

---

### 4.5 The mobile app cannot recover from a failed start

**Severity: High** · Confirmed by code review and measurement

The application loads seven custom font files — approximately 1.4 MB — before it will
render anything, and the loading step discards its own error signal. If font loading fails
for any reason, the app displays a loading indicator indefinitely: there is no timeout, no
retry, and no path to a degraded but working screen.

The application also has no error boundary of any kind, so any unexpected error in
rendering removes the entire interface rather than a single screen.

This is the most likely explanation for a loading failure observed during this review, in
which the app remained on its loading screen for several minutes before the platform
reported a generic failure.

**Recommended solution.** Allow the app to start with system fonts if custom fonts fail,
and add a single error boundary with a retry option, reporting to error monitoring.

**Alternative.** A one-line change to the start-up condition, allowing the app to proceed
when font loading has definitively failed. This converts an indefinite hang into a working
app with fallback typography and can be done immediately.

**Reasoning.** Typography is a presentation concern and should never be able to prevent the
product from starting. We would take the cheap fix immediately and the error boundary in
the same phase, because together they change the failure mode from "the app is broken" to
"the app told me something went wrong" — which every subsequent phase of work benefits
from.

---

### 4.6 Sessions can silently fail to persist on Android

**Severity: High** · Confirmed by measurement

Sign-in state is stored in the device's secure storage, which on Android has a practical
size limit per stored value. The application stores the entire session — including the user
profile collected during onboarding — as a single value. We measured this:

| Session contents | Size | Against the platform limit |
| --- | --- | --- |
| Newly signed-in user | 1,861 bytes | 187 bytes of headroom |
| After completing onboarding | 1,999 bytes | 49 bytes of headroom |
| With a password reset in progress | 2,080 bytes | **Exceeds the limit** |

Compounding this, the display name a user chooses has no length limit anywhere in the
system, and the failure to save is suppressed in production builds.

**Impact.** An Android user who completes onboarding and then begins a password reset — or
who simply chooses a long display name — will be signed out every time they reopen the app,
with nothing reported anywhere.

**Recommended solution.** Store only the long-lived credential in secure storage and keep
the short-lived one in memory, removing the size pressure entirely. Add a length limit to
the display name, and stop suppressing storage failures.

**Alternative, with the trade-off stated.** Limit the display name and stop storing
reset-in-progress state in the user profile. This is about ten lines of work and restores
roughly 100 bytes of headroom. The trade-off is that it manages the margin rather than
removing the constraint — the problem returns if the stored profile grows again.

**Reasoning.** We would take the cheap option first because it is quick and the exposure is
live on Android today, and schedule the storage change with other mobile work. The one part
we would not defer is making the failure visible; a silent sign-out loop is very difficult
to diagnose from support reports alone.

---

### 4.7 There is no continuous integration, monitoring, or rate limiting

**Severity: High, cumulative**

The repository contains no automated checks on changes — no build, type, test or database
migration verification runs when code is modified. There is no error monitoring in either
the app or the backend, and no limit on how frequently the paid AI service can be called.

The practical consequence is that today it is not possible to answer questions such as
*"is the crisis safeguard working in production?"* or *"why did the AI service cost
increase?"*

**Recommended solution.** Automated checks on every change; error monitoring in the app and
the backend; a request limit per user; and a staging environment where database and
permission changes can be rehearsed.

**Alternative.** Introduce automated checks and error monitoring only, deferring the
request limit. The trade-off is accepting unbounded AI cost exposure for longer — a
commercial risk rather than a safety one, and a reasonable thing to sequence if budget is
the constraint.

**Reasoning.** We treat this as a prerequisite rather than an improvement. The structural
access-control change in 4.1 and the internal reorganisation in 4.9 are the two highest-risk
changes in this plan. Attempting either without automated checks, a staging environment or
error monitoring is how a security fix becomes an outage. **This work should be scheduled
before the structural phase, not after it.**

---

### 4.8 A dependency is carrying most of the project's critical vulnerabilities

**Severity: High**

The dependency audit reports 191 advisories, of which six are critical. **Four of those six
arrive through a single dependency**, included to support a device-attestation feature that
is disabled by default, cannot currently be enabled because the app-side implementation was
never completed, and has no test coverage.

Most of the remaining advisories are in development tooling and never reach production, so
the headline number overstates the production risk.

**Recommended solution.** Decide the feature's future. If device attestation is wanted,
complete it. If not, remove the dependency.

**Alternative.** Keep the dependency and accept the advisories, on the basis that the
vulnerable code paths are not exercised. Defensible technically, but it means carrying four
critical advisories through any future security review or customer questionnaire in support
of functionality that does not work.

**Reasoning.** We recommend deciding rather than deferring, because the current position is
the worst of both: the cost of the dependency without the benefit of the feature.

---

### 4.9 One component concentrates most of the remaining risk

**Severity: High, structural**

A single file of approximately 1,600 lines handles conversation context assembly, calls the
AI service up to six times per message through five separate retry conditions, maintains a
therapeutic-technique state machine, and performs eight further database writes that are
not covered by a transaction. If any of those later writes fails, the messages are saved
while the conversation's state is only partly updated.

It carries the majority of the remaining high-severity findings, and none of its retry
paths are covered by a test.

**Recommended solution.** Extract three pieces without changing the architecture: the
technique state machine, with explicit validated transitions; the retry logic, as a defined
sequence with a retry budget; and the write sequence, as a single transaction. Write tests
against each piece before moving it, using the existing test suite as the safety net.

**Alternative, with the trade-off stated.** Fix the individual defects in place and leave
the structure alone. Faster, and each fix is small. The trade-off is that the file remains
the hardest part of the system to change safely, and the next set of defects in it will
cost the same to find. This is a deliberate decision about future development pace rather
than immediate risk.

**Reasoning.** We recommend the extraction, but **not urgently and not first**. It is the
right investment once automated checks exist to protect it. Nothing here is misdesigned —
the component is simply doing too much in one place to be reasoned about or tested
effectively.

---

### 4.10 Documentation describes an application that no longer exists

**Severity: Moderate, but unusually cheap to fix**

The project's own technical documentation describes a navigation structure the app does not
have, references two screens that do not exist, and instructs developers to modify two
configuration files that no code reads. Two further documented behaviours do not match the
implementation.

**Recommended solution.** Correct the documentation and delete or connect the unused files.

**Alternative.** None worth presenting.

**Reasoning.** We would normally treat this as housekeeping. We are raising it because this
codebase is developed with AI assistance, and these documents are supplied to those tools
as authoritative context. Incorrect documentation here is not merely unhelpful — it
actively directs work in the wrong direction. It is the cheapest item in this assessment
and one of the better-value ones.

---

### 4.11 Framework versions and platform currency

**Severity: Moderate**

The mobile framework is three major versions behind current. One core library was manually
patched to accept a slightly different version of a related package — the patch is minimal
and correct, but must be re-created on every framework upgrade. One package is used without
being declared, and is present in two different versions.

**Recommended solution.** Treat the framework upgrade as a single planned migration, not as
individual package updates. Retire the manual patch as part of it.

**Alternative.** Defer. Reasonable in the short term; the cost of deferral rises over time
as the gap widens, and one currently-used media library is removed in later framework
versions, so the upgrade will eventually be forced rather than chosen.

**Reasoning.** Explicitly worth warning about: the dependency report appears to show
thirteen individually outdated packages. It does not. Those packages move together as one
framework release, and updating them individually will break the application. This should
be one deliberate piece of work.

---

### 4.12 Data handling and privacy posture

**Severity: Requires your judgement, not only ours**

The product stores mental-health conversations, including explicit disclosures of risk, as
plain text. Against that:

- The access-control findings in 4.1 and 4.2 meant those records were readable by other
  signed-in users, and writable without authentication.
- Conversation identifiers and context are written to production logs without restriction.
- The administrative interface exposes complete conversation transcripts, protected only by
  an administrator role, with no record of who viewed what.
- A diagnostic setting returns the AI model's internal reasoning to the app.
- There is no data-retention policy, no retention mechanism, and no anonymisation path
  anywhere in the system.

One control is genuinely well implemented: deleting a user account correctly removes all of
that user's conversations, messages, summaries and activity. That was verified against the
live database and it was not accidental.

**Recommended solution.** Restrict logging of identifiers and conversation content; add
access logging to the administrative transcript view; define and implement a retention
policy; and confirm the diagnostic setting is disabled in production.

**Alternative.** Sequence the retention work after the access-control fixes, on the basis
that exposure is the more urgent risk. We think that is the right sequencing.

**Reasoning, stated plainly.** The technical remediation above is well understood and
straightforward. What we are not in a position to advise on is whether the confirmed
exposure of sensitive personal data — even in a pre-launch system with a small number of
records — carries notification or assessment obligations for you. **We recommend putting
this in front of whoever advises you on data protection, with the facts as recorded here,
and we would not defer that conversation until after the technical fixes are complete.**

---

## 5. Why we are not recommending a rebuild

Four critical findings in a system handling sensitive health data is a legitimate reason to
ask whether the foundation should be replaced. We tested that question rather than assuming
an answer, and the reasoning is set out below.

### The findings reduce to a small number of causes

Fifty-plus findings are not fifty-plus problems. They resolve into six causes:

| Cause | Share of risk |
| --- | --- |
| Access control enforced in application code rather than by the database | Roughly 40% of severity-weighted risk |
| Safeguards enforced in the app and inferred from AI output | Product-critical |
| One component doing too much | Sets the limit on future development pace |
| No operational tooling — checks, monitoring, limits | Systemic, but additive to fix |
| Documentation and configuration drift | Low cost, quick to correct |
| Mobile resilience gaps | Localised, three are single-file changes |

Correcting the first cause alone removes the majority of the severity-weighted risk.

### The expensive parts are the correct parts

A rebuild is justified when the things you *cannot* cheaply change are wrong. Ranked by how
costly they are to change later:

| Layer | Cost to change later | Assessed state |
| --- | --- | --- |
| Database schema and data model | Very high — requires migrating live data | **Sound** |
| Module boundaries and dependency structure | Very high — affects everything | **Correct** |
| Contract between app and server | High | **Well defined and enforced** |
| Separation of server code from the app bundle | High | **Correctly enforced** |
| Access-control mechanism | **Low** | **Wrong** |
| Internal structure of one component | Moderate | **Overgrown, not misdesigned** |
| Operational tooling | Low — purely additive | **Absent** |
| Documentation | Very low | **Out of date** |

The problems sit in the inexpensive rows. That is the opposite of the profile that justifies
starting again.

### The critical fixes are small

Each of the four critical findings is a change of roughly five to ten lines of code, or a
single database policy change. They are severe because of what the data is, not because the
system is incapable of expressing the correction.

### Nothing found is a limitation of the technology chosen

No finding in this review reduces to "the chosen framework cannot do this" or "the data
model cannot represent this". Every finding is a decision made within a design that can
accommodate the correct decision. The most significant finding is notable in this respect:
the database protections needed to prevent it **are already written and already correct** —
they are simply not being used. The fix is to start using what has already been built.

### What would have changed our view

For completeness, the conditions under which we would have recommended a rebuild, none of
which hold:

- A data model requiring migration of live data — the schema is sound
- Boundaries so entangled that changes cascade unpredictably — boundaries are clean and
  automatically enforced
- A technology unable to meet the product's requirements — no such case found
- No test coverage to make refactoring safe — 666 tests exist, and we verified they test
  real behaviour rather than mocked behaviour
- Business logic duplicated across the mobile app — not present
- A mobile application without coherent structure — specifically re-examined at the end of
  this review; it is conventional and coherent

### The caveat, stated clearly

"No rebuild" is not "low risk". The severity is real, two critical findings were reproduced
against a running system, and the product handles disclosures of risk to life. Our claim is
narrower and should be read exactly as written:

> The defects are severe in consequence and shallow in structure. Rebuilding would spend the
> remediation budget re-deriving the parts that are already correct, while leaving the
> access-control model — the actual problem — untouched.

---

## 6. Proposed order of work

Sequenced by severity **and** dependency. Each phase is independently deliverable. The
ordering reflects what must exist before later work is safe to attempt.

### Phase 0 — Close the confirmed exposure

**Estimated: days. No refactoring; narrowest possible changes.**

| # | Item | Why in this position |
| --- | --- | --- |
| 1 | Apply the missing ownership filter to conversation history retrieval | Closes the confirmed cross-user data exposure. Smallest change, largest effect |
| 2 | Add ownership validation to the elevated database function; withdraw unauthenticated access | Closes the confirmed unauthenticated write path |
| 3 | Add the ownership condition to the message-write policy | Same family as 1 and 2; independent of both |
| 4 | Restrict which conversation fields a user may modify | Prevents the safeguard flag being altered |
| 5 | Enforce the crisis safeguard at the API boundary | Independent of 1–4; the safety control |
| 6 | Correct the administrative sign-in link path | One-line fix to a currently broken login route |
| 7 | Align conversation-memory configuration; add the missing query bound | Stops unbounded cost growth |
| 8 | Allow the app to start when font loading fails; add an error boundary | Converts the current Android failure into a legible error, which all later phases benefit from |

**Dependencies: none.** All eight items are independent of one another and of later phases,
which is why they come first.

### Phase 1 — Establish the safety net

**Estimated: one to two weeks. Prerequisite for Phase 2.**

| # | Item |
| --- | --- |
| 9 | Automated checks on every change: build, types, tests, database migrations |
| 10 | Bring the code-quality gate to passing so it becomes a usable signal |
| 11 | Error monitoring in the mobile app and the backend |
| 12 | Request limiting on the AI endpoint |
| 13 | Staging environment for rehearsing database and permission changes |
| 14 | Correct the deployment configuration inconsistencies |
| 15 | Interim fix for the Android session-persistence issue |
| 16 | Remove unrestricted logging of conversation identifiers and context |

**Why before Phase 2.** Items 17 and 19–22 below are the highest-risk changes in this plan.
Attempting them without automated checks, a staging environment or error monitoring is the
single most likely way to convert this remediation into an incident. **We would not begin
Phase 2 before Phase 1 is complete.**

### Phase 2 — Structural correction

**Estimated: two to four weeks. Highest leverage in the plan.**

| # | Item | Depends on |
| --- | --- | --- |
| 17 | Move access control to the database: per-user connections, so row-level security applies | Phase 1 (staging, monitoring) |
| 18 | Withdraw the now-unnecessary direct table permissions | Item 17 proven in staging |
| 19 | Extract the technique state machine, with tests written before it is moved | Phase 1 (automated checks) |
| 20 | Validate AI-supplied values before they are used as identifiers or stored | Item 19 |
| 21 | Reorganise the retry logic; ensure the risk signal is evaluated before any retry | Item 19 — retry conditions read state-machine state |
| 22 | Make the write sequence for a message a single transaction | Items 19–21, which relocate the write sites |

The dependency chain here is real and should not be resequenced: 17 makes 18 safe; 19 must
precede 21; 22 comes last because the earlier items move the code it touches.

### Phase 3 — Reduce carrying cost

**Ongoing; can run in parallel with Phase 2.**

| # | Item |
| --- | --- |
| 23 | Resolve the device-attestation dependency: complete the feature or remove it |
| 24 | Mobile framework upgrade as one planned migration, including the media library replacement and retiring the manual patch |
| 25 | Remaining moderate mobile findings |
| 26 | Remove unused files, dependencies and redundant database indexes |

### Phase 4 — Documentation and governance

| # | Item |
| --- | --- |
| 27 | Correct the technical documentation; remove or connect the unused configuration files |
| 28 | Data-retention policy and mechanism; access logging on the administrative transcript view |
| 29 | Cost and usage monitoring for the AI service |

**Note on sequencing:** item 27 is the cheapest item in the entire plan and can be done at
any point. It appears last only because nothing else depends on it — not because it should
wait. The data-protection consultation referenced in 4.12 should begin immediately and does
not belong to any phase.

---

## 7. Summary of recommendations by disposition

| Disposition | Items |
| --- | --- |
| **Keep as-is** | Monorepo structure and dependency direction; the shared app/server contract; separation of server code from the app bundle; database schema, migrations and indexing; the encryption implementation; prompt version management; the design-token system; client credential storage; the chat screen's failure and retry handling; the transactional message-write approach; the test suite as a refactoring safety net |
| **Fix** | The four critical findings; the eleven high-severity findings; ten mobile findings; the deployment, quality-gate and documentation issues |
| **Restructure** | Access-control mechanism (highest leverage); the oversized conversation component, into three pieces; validation of AI-supplied values; conversation-state handling; the mobile authentication context |
| **Replace** | The device-attestation dependency; the app start-up gate; one misconfigured configuration lookup; the mobile framework version and its deprecated media library |

The short **Replace** column is itself a finding. Very little here needs to be thrown away.

---

## 8. Open items and limitations

Recorded so this assessment can be relied upon accurately.

1. **Backend service-layer error handling was not completed.** We expect further moderate
   findings; we do not expect any conclusion in this document to change.
2. **The Android start-up failure is diagnosed but not yet confirmed on a device.** The
   mechanism is established by code review and measurement. A device log during a failed
   start would confirm it definitively, and we recommend capturing one.
3. **Findings labelled as reviewed rather than reproduced** are supported by direct reading
   of the code, database schema or configuration. Where we reproduced behaviour against a
   running system, this document says "confirmed".
4. **No load, performance or penetration testing** was carried out. The scalability comments
   in this assessment are architectural judgements, not measurements. Our expectation is
   that the current infrastructure is adequate at the anticipated scale and that cost per
   AI interaction, not infrastructure, is the binding constraint.
5. **This assessment covers code and configuration only.** It does not cover the hosting
   accounts, access management, third-party contractual terms, or clinical safety review.
