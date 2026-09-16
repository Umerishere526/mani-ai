---
type: programme
status: accepted
date: 2026-09-16
apps: [backend]
tags: [conversation, prompts, frameworks, ai]
---

# Conversational architecture

How Mani decides what to say — style selection, framework routing, prompt assembly, and what
gets enforced in code rather than asked of the model.

**Scope: the conversational and prompt layer only.** No infrastructure changes. The port is
done and that layer is sound. One model call per turn, asyncpg direct to Postgres with RLS as
the enforcing layer, deterministic repairs instead of regeneration, the `public`/`admin` schema
split, additive migrations — none of these move.

**Source documents.** Kept as provenance and superseded by §1 of this document as the
implementation source of truth:

- *Directive. Supportive. Reflective.* — the three conversational styles and the cadence
- *Six Frameworks for App* — ABCDE, Thought Reframe, Behavioral Activation, Structured
  Problem-Solving, ACT Choice Point, DBT STOP; safety exception; per-stage specification
- *System Prompt* — the prompts as currently implemented
- *Mani Communication Engine* — the X-then-Y rules engine and the vague-reply pivot
- *Pacing Rules and Conversational Structure* — the Rule of One, validation, repetition, clarity

**They are not in the repository.** Nothing under `backend/` or `mani/` contains them, so the
~100 authored tone variants, the ~50 gold responses and the ~60 labelled negatives exist only
as attachments. **Commit them to `backend/docs/specs/` before step 4 of §9.** Until then the
framework content cannot be authored and the eval sets cannot be extracted.

---

## Where the code actually stands

Verified against the tree on 2026-09-16. Three of these are easy to assume are built and are
not.

- **`support_style` reaches the model as a single sentence.** `mani/prompts/composer.py:46` —
  `"They asked for a {support_style} style of support."` That is the entire implementation of
  *"Directive leads. Supportive accompanies. Reflective mirrors and explores."*
- **`admin.frameworks.body` is empty and unreachable.** `scripts/seed.py:25,34` seed `""`, and
  `seed.py:80-85` omits `body` from the upsert's `do update set` — so **re-seeding can never
  publish framework prose even once it is written**. `activation_conditions` is seeded, stored,
  and read by nothing. Framework text lives in a static `prompts/techniques.md` blob (11 KB)
  shipped in full on every turn regardless of state.
- **`tests/evals/` exists and is empty.** The four crisis scenarios have never run.
- **`mani/chat/crisis.py:35` `RESOURCES` is an empty list**, and crisis is self-reported by the
  model *after* it writes a reply (`orchestrator.py:231`). There is no pre-generation screen.
- **`mani/chat/greeting.py:9` hardcodes `"How can I support you today?"`** — the *supportive*
  opener, for everyone, regardless of `support_style`.
- **`mani/llm/schema.py` hardcodes content in three `Field` descriptions**, all of which are
  prompt surface: `TechniqueState.technique` names two framework ids (`:50`), `.step` lists
  both phase sequences (`:52-57`), and `Style.shape` names six response shapes (`:79-84`).
  `prompts/response_format.md` repeats the same lists.

What *is* built and is not to be revisited: one model call per turn (asserted in
`tests/integration/test_turn.py`), deterministic repairs with zero regenerations
(`mani/chat/repairs.py`), phase validation with `clamp` that fails closed on an unknown
framework or phase, `admin.llm_calls` logging with tokens and latency, RLS enforced through a
`mani_service` role, idempotency by `client_message_id`, one transaction per turn.

---

## 1. The eleven conflicts, resolved

The specifications contradict each other in eleven places, four of them load-bearing. A prompt
rewrite on top of contradictory rules produces a model thrashing between rules it cannot
simultaneously satisfy. Decisions 1–4 were made by muhammad; the rest follow from the documents.

| # | Conflict | Resolution |
|---|---|---|
| 1 | **When style is chosen.** Styles doc: every conversation. Comms Engine rule 1 + current DB: onboarding. | **Per conversation.** New `threads.conversation_style`. `profiles.support_style` stays as the onboarding answer and becomes the default offered. See §5. |
| 2 | **Style inside a framework.** Styles doc + Frameworks doc: maintained. Comms Engine rule 42: "ignore style rules". | **Maintained throughout.** The Frameworks doc specifies three tone variants for every stage — roughly 100, already written. Rule 42 is overruled; strike it from that document. |
| 3 | **Mirroring.** Pacing §2–3: never repeat verbatim, reflect the situation. Frameworks: mirror their language. Live prompt: exact words, no synonyms. | **Pacing governs.** Reflect the situation rather than replaying the wording — *and* every pre-framework turn ends with a question that narrows toward a framework. The Frameworks doc's mirror examples get rewritten to reflect rather than echo. |
| 4 | **Turn shape.** | **One model call.** See §2 and [[ADR-002-one-model-call-per-chat-turn]]. |
| 5 | **Style vocabulary.** Styles doc + Comms Engine: "Directive". Frameworks doc: "Direct solution". DB: `direct`. | **`direct` / `supportive` / `reflective`.** Settled by fact, not preference: `001_initial_schema.sql:158` already constrains `support_style` to those three. Normalise all documents and all new code to `direct`. |
| 6 | **Emotional labels.** Comms Engine rule 9: strip "scared, sad, overwhelmed". Live prompt + Frameworks §17: echo the user's own emotion word. | **Never introduce an emotion word the user did not use; their own words are permitted.** Rule 9 is a misstatement of this — as written it forbids saying "overwhelmed" back to someone who just said it. |
| 7 | **Every response opens with acknowledgment** (Pacing §2) vs **shape variety** (`mani_base.md`) vs **"no repetitive language patterns"** (Styles doc). | Variety wins. A mandatory opening *is* a repetitive pattern. Rewrite Pacing §2 as "acknowledge before asking", not "begin every response with". |
| 8 | **Framework entry timing.** Styles doc: 2–4 exchanges. Comms Engine: pivot after 2 vague replies. Live prompt: "genuinely exhausted what presence and curiosity can do". | **2–4 exchanges.** The live prompt's presence-check is deleted from `mani_base.md` — it is the single biggest behavioural change here, and while it stands no framework fires on time. |
| 9 | **Standalone mirrors.** Frameworks: never, always mirror + one question. Live prompt: "presence only" shape, and "if my last two responses ended with questions, this one must not". | **Scope them.** Inside a framework: always a question. Free conversation: variety permitted. They conflict only because they currently share one prompt. |
| 10 | **Two Worry Buckets** (Comms Engine) is a seventh exercise, not one of the six. | **A library exercise** — an `admin.exercises` row. No registry entry, no phase machine, no stage content. |
| 11 | **Greeting.** Styles doc: "Hi (nickname). It's MANI." then style selection. `greeting.py:9` hardcodes the supportive opener for everyone. | **Capsules on the greeting**, not a second message. See §5 — the two-step opening the previous draft assumed is blocked by the database. |

---

## 2. Turn shape: one model call

Decided in [[ADR-002-one-model-call-per-chat-turn]], which supersedes the route-then-speak
proposal in the 2026-09-15 draft of this document.

The argument for a router was that a stage-scoped prompt needs to know the stage, and at the
moment of *selection* nothing does. That holds, and the answer is not a second call:

- **While a framework runs**, the stage is in `public.thread_technique_state` and was declared
  by the previous turn's structured output. Stage-scoped composition needs no new call.
- **At selection**, the model writes from a compact framework index plus
  `activation_conditions` — enough to *offer*, which is all that turn does. Full stage content
  arrives on the next turn, once the choice is persisted.
- **Routing accuracy is still a number.** Run the router question as an offline eval against
  the routing set (§8). The metric does not require paying for the call in production.

The reversal path, if the eval says the index is not enough, is a router on `converse` turns
only. Do not take it pre-emptively.

---

## 3. Prompt architecture — the load-bearing decision

`composer.py:99-114` orders eight candidate layers and drops the falsy ones. The order is
`mani_base → techniques → user_context → [title_generation] → techniques_used →
response_format → debug → summary`. Two of those — `title_generation`, which appears on
exactly one turn, and `techniques_used`, which grows as frameworks are offered — are **volatile
and sit above `response_format`**, the largest layer at 13,624 characters. Everything behind a changed layer
falls out of the provider's cache, so today the biggest static block in the prompt is paid in
full on turns where a title is requested or a technique has been offered.

**The rule: the system prompt is ordered strictly by volatility, most stable first, and
anything that can change within a single conversation does not belong in it at all.**

**Zone A — global static prefix.** Identical for every user and every conversation:

```
mani_base → pacing → safety → framework_index → post_framework → response_format
```

**Zone B — per-conversation tail.** Stable for the life of one conversation, so it caches from
that conversation's second turn onward:

```
style_{direct|supportive|reflective} → user_context → debug
```

**Zone C — the `[ctx]` block** prefixed to the final user message. Volatile, and therefore free
of cache cost because nothing is cached behind it: the existing metadata from
`context.build()`, the rolling summary, `techniques_used`, the title instruction, and **the
active framework's payload** — its governing rules, the full stage list as ids plus one-line
goals, and full guidance for the current and next stage only, resolved to this conversation's
style.

**The framework body goes in Zone C, not the system prompt.** The stage changes on nearly every
in-framework turn. In the system prompt that would invalidate the prefix *and all conversation
history behind it*, precisely on the turns where the prompt is largest.

`prompts/techniques.md` is retired by this split: its governing rules become `post_framework`
in Zone A, its framework list becomes `framework_index`, and its per-framework prose becomes
the `stages` jsonb of §4, reaching the model through Zone C one framework at a time.

### What it actually costs

Sizes are exact, from `admin.prompts`. Tokens are at 4 characters per token, which the one
recorded `input_tokens` of 8,230 against 33,507 characters of system prompt corroborates.

| | Today | Free conversation | In framework |
|---|---|---|---|
| Zone A — static prefix | — | 7,450 | 7,450 |
| Zone B — per conversation | — | 200 | 200 |
| Zone C — `[ctx]` | ~250 | 250 | 875 |
| System prompt as it stands | 8,380 | — | — |
| **Total, excluding history** | **8,380** | **7,900** | **8,530** |
| **Cacheable** | **0 measured** | **7,650** | **7,650** |

**Raw token count barely moves. The entire benefit is the cached fraction**, and that fraction
has never been measured. `admin.llm_calls` holds two byte-identical rows from the scripted test
model, with `cached_input_tokens` at 0 on both. The plumbing is right — `llm/client.py:205-210`
asks OpenRouter for `usage: {include: true}` and reads `prompt_tokens_details.cached_tokens` —
so the field is blind only because no live turn has ever been recorded.

**Therefore step 0 of §9 is a caching spike**, before any reordering: two identical
back-to-back chat turns against `google/gemini-3-flash-preview`, then read
`cached_input_tokens`. It is an hour's work and it decides whether this section is worth doing.
If the number comes back 0, reordering buys nothing and the work becomes *cutting* the prompt
rather than arranging it.

### The cut that pays either way

`response_format.md` is 13,624 characters, the largest layer, and roughly two thirds of it —
`# Field Descriptions` through `## Library Navigation` — **restates the Pydantic `Field`
descriptions in `llm/schema.py`, which are already sent to the model as the JSON schema of the
structured output.** The same rules, twice, every turn.

Cutting that duplication is worth on the order of **1,700 tokens per turn, cached or not**, and
it is the only large saving in the prompt that does not depend on an unproven cache. Do it in
the same pass as the §4 removal of the hardcoded framework and shape lists, which live in the
same block.

What stays: `## User Message Format`, `# Constraints`, `## Tone`, `## Response Length`,
`## Security` and `# Self-Check`, along with `mani_base` in full. Those hold the word-for-word
audit and the no-adjectives list — the guardrails that stop replies sounding like a chatbot,
and the reason this is a targeted cut rather than a trim.

---

## 4. Content model: stages as jsonb on the framework row

`admin.frameworks.phases` is a `text[]` of stage names and prose lives in a markdown blob. That
cannot carry six frameworks specified to the depth of the Frameworks document.

**`admin.frameworks.stages jsonb not null default '{}'`**, keyed by phase id:

```jsonc
{
  "belief": {
    "purpose":    "…",   // §11 Purpose of Every Stage
    "listen_for": "…",   // §13 What MANI Is Listening for
    "ready_when": "…",   // §16 What Must Be Clear Before Proceeding
    "boundaries": "…",   // §18 Boundaries Within Every Stage
    "if_unclear": "…",   // unclear-answer handling
    "ask": {             // §15 Tone Variations — the ONLY style-varying leaf
      "direct": "…", "supportive": "…", "reflective": "…"
    }
  }
}
```

`purpose`, `listen_for`, `ready_when`, `boundaries` and `if_unclear` are clinical, not tonal —
they do not vary by style. **The composer emits one `ask`, resolved to the conversation's
style, never three.**

One additive column rather than three tables (`framework_stages`, `stage_tone_variants`,
`style_rules`, as the earlier draft proposed). It holds the same ~100 authored variants, and
costs no new RLS policies, grants, row models, repository modules or admin CRUD endpoints. The
runtime only ever reads one framework's blob; nothing queries across frameworks. If the admin
portal later needs per-stage editing, jsonb → tables is a mechanical migration.

Also required:

- **Populate `activation_conditions`.** It exists, is stored, and reaches nothing. It becomes
  the framework index's input, and under §2 it is what carries selection quality.
- **Fix `seed.py`'s upsert** to include `body` and `stages` in `do update set`, or re-seeding
  silently never publishes new content (`seed.py:80-85`).
- **Registry-drive `mani/llm/schema.py`.** Replace the hardcoded ids and phase lists at `:50`,
  `:52-57` and `:79-84` with a pointer to the index ("the framework id, exactly as listed in
  the Framework Index"). `repairs.py` already fails closed on both axes, so the description is
  guidance, not enforcement. **Cut the same lists from `prompts/response_format.md` in the same
  commit** or the fix is undone.

---

## 5. Style selection: capsules on the greeting

The previous draft called for a two-step opening — greeting, then a separate style-selection
message. **That is blocked by the database.** `public.create_greeting` raises `42501` if the
thread holds *any* message (`001_initial_schema.sql:609-610`), and it is the only way Mani's
opening line can be written, since `authenticated` holds no INSERT on `messages`.

The cheaper design avoids the problem rather than working around it: **the greeting carries
three capsules.** One Mani message, three tappable options in user voice. The person taps one;
that is their first user message; Mani's reply is the style-specific opener, written by the
model with the chosen style capsule already in Zone B.

This reuses machinery that already exists and is already tested:
`orchestrator.find_tapped_prompt` matches a tap by label against the most recent Mani message's
options, exactly as it does for technique offers. What it needs:

- A `style` field on `SmartPrompt`, validated against a closed set before it is persisted or
  used as control flow — the same discipline `technique` and `library` already follow.
- `create_greeting`'s signature widened to take `prompt_options jsonb`. A changed signature is
  a *new* function: `drop` the old one and `revoke all … from public` on the new one. Postgres
  grants EXECUTE to PUBLIC by default, and closing that is exactly what `001` was written to do.
- `threads.conversation_style`, written when the tap resolves.

`profiles.support_style` stays as the onboarding answer and is not overwritten — it becomes the
default, and the per-conversation choice overrides it.

### What the first screen returns, before and after

`POST /v1/threads/current`, first-time user. Today:

```jsonc
{ "thread": { "title": null, "message_count": 1, … },
  "messages": [ { "role": "mani",
                  "content": "Hi there. It's Mani. How can I support you today?",
                  "prompts": [] } ],
  "is_new": true }
```

One opener for everyone — and it is the *supportive* one, so a person who chose `direct` at
onboarding is greeted in a style they did not pick. After:

```jsonc
{ "thread": { "conversation_style": null, … },
  "messages": [ { "role": "mani",
                  "content": "Hi Sam. It's Mani.",
                  "prompts": [
                    { "label": "Tell me what to do",      "style": "direct" },
                    { "label": "Just be with me",         "style": "supportive" },
                    { "label": "Help me think it through","style": "reflective" } ] } ],
  "is_new": true }
```

The tap is an ordinary send. `find_tapped_prompt` matches the label, `threads.conversation_style`
is written, the matching capsule enters Zone B, and Mani's reply is the style-specific opener.

**Why this is worth doing.** Style stops being one interpolated sentence
(`composer.py:46`) and becomes structural instruction that changes who leads, how often Mani
asks rather than reflects, and how early a framework is offered. It costs **no extra model
call** — the capsules are static text on a message that was already being written — and no new
endpoint. `_history()` already marks the newest Mani message's buttons as live
(`routers/threads.py:75-79`), so the greeting's capsules render with no serializer change.

---

## 6. State machine

**`phases` becomes `[offering, …content…, somatic, closing]` for all six frameworks**, with a
CHECK that the last two are exactly that. Backfill before adding the constraint.
`validate_transition` and `clamp` need **zero changes** — they read `phases` positionally, so
two more entries are two more legal forward steps.

The `closing` capsules ("Chat More" / "Go to Library") are **substituted by `repairs.py`**,
not trusted to the model, which makes the existing `library_offered` branch fire with no new
plumbing.

### Two bugs that must be fixed before any of this

**1. `COOLDOWN_AFTER_COMPLETE = 45` has never applied.** `orchestrator.py:162-169` detects
completion by the string literal `GROUND = "ground"` and sets `clear_technique`, which
**deletes** the `thread_technique_state` row (`threads.py:250-255`). That destroys
`at_message_count`, so `context.build()` takes its `technique is None` branch
(`context.py:45-46`) and emits `cooldown_passed: yes`. **Frameworks can stack back-to-back
today**, and the branch has no test. The same DELETE also makes the `library_offered` update at
`threads.py:294-299` hit zero rows.

*Fix: retire the row by UPDATE (`phase = null`), never DELETE.* "Finished" becomes
`outcome = 'accepted' and phase is null`; "a framework is running" becomes
`technique is not None and technique.phase is not None`. **`ctx` must keep the retired row** —
`orchestrator.py:169` currently replaces it with `None`, which is what makes the cooldown
unreachable. `context.build()` needs no change: its `else` branch already computes the cooldown
from `at_message_count` and already guards the `current_phase` line on `if technique.phase`.
Costs no new grant — `grant select, insert, update on public.thread_technique_state` is
table-level (`001_initial_schema.sql:720`).

**2. Completion is a string literal.** `GROUND` cannot detect completion for a framework ending
on a different phase, and makes any appended phase unreachable. *Fix:
`Registry.is_final(framework_id, phase)` comparing against `phases[-1]`.*

*(An earlier claim that `authenticated` lacked DELETE on `thread_technique_state` was wrong. The
repo has a dedicated `mani_service` role holding it, and the `technique_state_delete` policy
exists. Disregard it.)*

---

## 7. Rules in code, not prompt text — and the honest limit

`repairs.py` corrects deterministically rather than regenerating. That is the right pattern and
it extends. But it extends **only as far as a safe correction exists**, and the previous draft
of this document overstated how far that is. Asking a model to audit its own output is the
least reliable way to enforce anything a diff can check; rewriting prose in code is a good way
to make a reply worse than the violation was.

So the rules split three ways.

**Substitute — a known-good replacement exists:**

| Rule | Source | Action |
|---|---|---|
| Closing capsules | Frameworks §closing | Code writes the two capsules; the model is not asked for them |
| Vague-reply pivot | Comms Engine | Model writes it, code verifies, code substitutes fallback text on failure |

**Correct or drop — already the pattern in `repairs.py`:** unknown technique id, phase clamp,
duplicate labels, the button just tapped, more than three capsules, over-long title. All
shipping.

**Measure, log and gate in eval — no safe automatic rewrite:**

| Rule | Source | Check |
|---|---|---|
| One question per turn | Pacing §1 | count `?` |
| No standalone mirror *inside a framework* | Frameworks §3 | no `?` while a framework is active |
| No introduced emotion words | Comms Engine 9 | emotion lexicon ∩ reply − user's message |
| No clinical labels | Frameworks §25 | wordlist: catastrophising, distortion, irrational, mind-reading |
| Forbidden words and phrases | System Prompt | `broken`, `weak`; `"you're so brave"`, `"you're so strong"` |
| Response length | Pacing §5, Frameworks §25 | sentence / character ceiling |
| No repeated question | Pacing §3 | similarity against prior Mani questions in the thread |
| No summarising several stages | Frameworks §25 | reply references more than one prior stage |

These are detected, counted into the repair-note log, and asserted against the ~60 labelled
negatives — **where they run with no model call at all**. A violation at runtime is a metric,
not a rewrite. If a rate stays high, the fix is the prompt text in Zone A, which is cached and
therefore nearly free to enlarge.

**The forbidden-word list was dropped at `repairs.py:29-33`** on the grounds that it collided
with mirroring: someone typing "I feel broken" made a caring reply unsendable. That reasoning
was wrong about the rule, not about the collision. The rule is that Mani must not *introduce*
those words — the Frameworks doc's own rule 24 permits mirroring non-emotional words back. So
the check has the same shape as the emotion-word check: **present in the reply and absent from
the user's message**. Restore it in that form.

**Two hazards in the pivot verifier.** It must test "no question *other than* the consent
question" — a bare `"?" in text` fires on the consent question itself and substitutes a
fallback over a correct reply. And the vague counter must not increment on the idempotency
short-circuit (`orchestrator.py:117-138`), which returns before any state is read.

**Drop or replace the `reasoning` field.** Six self-check steps written before every response
(`schema.py:138-147`), which the model then does not honour. Those checks belong in Zone A as
instruction or in `repairs.py` as mechanics.

---

## 8. Safety, and its boundary with crisis

`mani/chat/safety.py` — new, small, and **structurally complete with its content deliberately
blank**, the same discipline `crisis.py::RESOURCES` already follows. A `SafetyCategory`
StrEnum; `PROTOCOLS: dict = {}`; `LOCKS` defaulting to every category, so a clinician narrows
it rather than widens it; `protocol_for()` falling back to `crisis.CRISIS_REPLY` so the screen
is never blank. Nothing invented.

**Crisis and safety are disjoint and must stay so.** Crisis is imminent risk: it locks the
thread and writes an `admin.crisis_events` row. Safety is "do not run a framework now": it
changes routing and nothing else.

Two existing defects in the crisis path, in scope because this work touches them:

- **`_handle_crisis` returns without calling `threads.apply()`** (`orchestrator.py:366-402`),
  silently discarding every update the turn accumulated.
- **Crisis is self-reported after the reply is written.** The deterministic keyword screen the
  Frameworks doc asks for — *"place a safety assessment before framework selection"* — does not
  exist. Add it as a pre-generation screen; keep the model's judgement too, for the indirect
  expressions a keyword list cannot catch. Fail closed.

`admin.crisis_events` gains `category text` and `locked_thread boolean`, which widens
`mark_thread_crisis`. Same rule as §5: a changed signature is a new function — `drop`, then
`revoke all … from public`.

---

## 9. Sequence

0. **The caching spike** (§3). An hour, and it decides how much of §3 is worth doing.
1. **The two bugs in §6** — retire-by-update, `Registry.is_final` — with the tests they never
   had. Everything downstream is wrong without them.
2. **Migration `002`** — see §11 for the full plumbing, which is five places per column and
   silent at four of them.
3. **The `response_format` cut** (§3), which pays regardless of the spike's result, then the
   three-zone re-ordering if the spike says caching works. Measure `cached_input_tokens`
   before and after each.
4. **Framework content** — six `backend/frameworks/<id>.md` files with YAML frontmatter, loaded
   by `seed.py` reusing its existing `parse_prompt()` split. *Blocked until the specification
   documents are committed.*
5. **Extract the eval sets** in the same reading pass (§10). Makes every later step measurable.
6. **Style layer** (§5), then pacing and the vague-reply pivot, then safety (§8).
7. **The §7 validators**, checked against the negative set.

Exchange count needs no column: `threads.message_count // 2`, already in context.

---

## 10. Verification

- `pytest` and `scripts/test_db.sh --local` green.
  **`test_a_turn_costs_exactly_one_provider_call` must stay green** — it is the invariant.
- `test_turn.py::test_finishing_a_technique_clears_it_without_losing_the_turn` asserts
  `ctx.technique is None` after completion. Under retire-by-update that becomes a surviving row
  with `phase is null`. **Update the assertion; do not revert the fix** — losing the row is what
  makes the cooldown unreachable.
- New tests: somatic → closing → retirement, asserting `cooldown_passed: no` on the next turn;
  a two-vague-reply pivot asserting one call; a pivot whose reply fails verification, asserting
  the fallback was substituted and still one call; `ThreadUpdates(vague_streak=0)` not
  short-circuiting `apply()`.
- **`ThreadUpdates.__bool__` (`threads.py:228-232`) tests bare truthiness over a list.**
  `vague_streak = 0` is falsy, so a present-but-falsy field makes `apply()` return early and
  silently drop the title and style writes in the same turn. It must test `is not None`.
  `orchestrator.replace_technique()` (`:338-347`) has the same class of defect — it enumerates
  fields positionally and will silently reset any field added later. Replace it with
  `dataclasses.replace()`.
- **Routing accuracy** on the eval set, as a percentage, before and after every prompt change
  touching Zone A. The headline number, and the reason a router is not needed at runtime.
- **Negative set passes deterministically**, no model call. A validator that needs the model to
  catch a banned pattern is not a validator.
- **Style differentiation** — one scenario through all three styles, diffed. Structural
  difference (who leads, question cadence, when a framework is offered), not vocabulary.
- **Token budget** from `admin.llm_calls`: `cached_input_tokens / input_tokens` on turns 2+
  should move from ~43% to 85%+. If it does not, something volatile leaked above
  `response_format`. Plus a byte ceiling per prompt shape in `test_composer.py` — no tokenizer,
  no model calls.
- SQL assertions: column grants for both new thread columns, and `anon` EXECUTE false on the
  new `create_greeting` and `mark_thread_crisis` signatures.
- **Transcript review by a human.** The largest quality risk — stage-scoped guidance making
  frameworks feel scripted, against `techniques.md`'s own "not a script to follow in order" —
  appears in no token metric.

---

## 11. Migration 002, and how each change is proved

### What changes

| Change | For | Grant |
|---|---|---|
| `threads.conversation_style text` + CHECK `in ('direct','supportive','reflective')` | §5 | `grant update (conversation_style) … to authenticated` |
| `threads.vague_streak smallint not null default 0` | §7 pivot | `grant update (vague_streak) … to mani_service` **only** |
| `frameworks.stages jsonb not null default '{}'` | §4 | none — `admin.frameworks` is already the shared read-only catalog |
| `frameworks.phases` gains `somatic`, `closing`; CHECK the last two | §6 | none |
| `create_greeting(uuid, text, jsonb)` | §5 capsules | `drop` the 2-arg function, `revoke all … from public`, grant to `mani_service` |
| `mark_thread_crisis(…, category, locked_thread)` | §8 | same drop / revoke / grant |
| `crisis_events.category`, `.locked_thread` | §8 | none — `admin` is unreachable by the Data API |

**`vague_streak` goes to `mani_service`, not `authenticated`, on purpose.** It is a pacing
counter the backend maintains; a user who could write it could reset their own pivot and never
be moved off a vague loop. This is the rule from `.claude/SUPABASE.md` — a privilege only the
backend needs never goes to the user's role.

### The five places a column has to be added

`grant update (title, last_message_at, deleted_at) on public.threads`
(`001_initial_schema.sql:713`) is **column-scoped**. A new column inherits nothing.

| # | Place | If forgotten |
|---|---|---|
| 1 | `002_*.sql` — the column | Loud. Everything fails. |
| 2 | `002_*.sql` — the column grant | **Runtime `42501`, which rolls back the whole turn** — the message pair is lost, not just the style |
| 3 | `db/threads.py:22` `COLUMNS` | Silent. Never reaches `TurnContext`, reads as the default forever |
| 4 | `models/rows.py:58` `Thread` | Silent. `extra="ignore"` drops it on validation |
| 5 | `db/threads.py:211` `ThreadUpdates` + its `apply()` branch | Silent. Never written |

Four of the five fail silently, and #2 fails in the most expensive way available. `ThreadOut`
in `models/api.py:15` is a sixth if the client needs to render the value.

### Two existing hazards this trips

- **`ThreadUpdates.__bool__` (`db/threads.py:228-232`) tests bare truthiness over a list.**
  `vague_streak = 0` is falsy, so a present-but-falsy field makes `apply()` return early and
  silently drop the title and style writes in the same turn. It must test `is not None`.
- **`orchestrator.replace_technique()` (`:338-347`) enumerates fields positionally** and will
  silently reset any field added later. Replace it with `dataclasses.replace()`.

### Reuse, do not duplicate

`models/rows.py:44-47` already defines `SupportStyle` as `supportive | reflective | direct`.
`conversation_style` is the same closed set and must reuse that enum. A parallel
`ConversationStyle` would be two spellings of one vocabulary, which is how conflict 5 in §1
started.

`prompts/cache.py:22` pins `REQUIRED_PROMPTS = ("mani_base", "techniques", "response_format")`.
Zone A adds `pacing`, `safety`, `framework_index` and `post_framework`, and **removes
`techniques`**. Update that tuple and seed every name in it in the same commit, or
`config.require()` raises `CONFIG_ERROR` and every turn 500s.

`models/rows.py:118` `Framework` needs a `stages: dict` field, or the registry cannot serve
what §4 stores.

### How each change is proved

Extend `tests/sql/test_grants.sql`, which already asserts this class of thing with
`has_column_privilege` and `has_function_privilege` (`:75-91`, `:155-219`):

```sql
-- the style is the user's to choose
select pg_temp.want('a user can choose their conversation style',
  has_column_privilege('authenticated','public.threads','conversation_style','UPDATE'), true);

-- the pacing counter is not
select pg_temp.want('a user cannot reset their own vague streak',
  has_column_privilege('authenticated','public.threads','vague_streak','UPDATE'), false);

-- a widened definer function is a NEW function, and PUBLIC gets EXECUTE by default
select pg_temp.want('anon cannot write a greeting',
  has_function_privilege('anon','public.create_greeting(uuid,text,jsonb)','EXECUTE'), false);
select pg_temp.want('a user cannot write a greeting either',
  has_function_privilege('authenticated','public.create_greeting(uuid,text,jsonb)','EXECUTE'),
  false);
```

Plus an assertion that the **old 2-argument `create_greeting` no longer exists** — a `create or
replace` with a new signature leaves the old one in place, still granted, still callable.

In pytest: one integration turn that writes `conversation_style` and asserts it survives the
round trip, which is the only thing that catches a missing grant, since #2 above is invisible
to unit tests.

### The authentication surface does not change

Worth stating plainly, because this is the part that must not drift:

- **No new endpoints.** Style selection rides on `POST /v1/threads` and
  `POST /v1/threads/current` through `StartOut.messages[].prompts`, which already exists, and
  the tap is an ordinary `POST /v1/threads/{id}/messages`.
- **Identity still comes only from the verified JWT.** `models/api.py` carries no `user_id` on
  any request body and none is added. The style is chosen by tapping a capsule, so the client
  names a *label*, not a user and not a privilege.
- **`SmartPrompt.style` is a model- and client-supplied identifier**, so it is validated against
  the `SupportStyle` closed set before it is persisted or used as control flow — exactly as
  `library` is validated against `LibrarySection` and `technique` against the registry.
- **Every write still runs through `UserConn`**, which sets `mani_service` and the caller's JWT
  claims, so RLS decides row ownership whether or not a query remembers its filter.

## 12. Offering an exercise when a framework ends

### Tool calling is not required, and would cost the invariant

A tool call is a round trip: the model asks, code answers, the model writes. That is two
provider calls minimum and a *variable* number in the general case, which is the failure mode
the port existed to remove and the reason [[ADR-002-one-model-call-per-chat-turn]] rejected
route-then-speak. It would buy nothing here, because **the answer is already known before the
model speaks.** The exercise that follows a completed framework is a lookup on a row the
backend has, not a judgement the model needs to make.

Tool calling would only earn its place if the catalog were too large to put in front of the
model and needed searching. The candidate set here is one to five rows. That is not retrieval.

### The flow

The `closing` phase (§6) already substitutes its capsules in `repairs.py` rather than trusting
the model. The exercise capsule is one of them, so **code chooses it end to end** and the model
is never asked for an identifier it could get wrong:

1. The turn reaches `closing`, which `Registry.is_final` now detects by position rather than by
   the string `"ground"`.
2. `repairs.py` builds two capsules: "Chat More", and the exercise — title and duration read
   from `exercises.for_framework(framework_id)`.
3. The capsule carries **`exercise_id`**, so the client deep-links to that exercise rather than
   dropping the person on a category screen to find it themselves.
4. `library_offered_since` records the offer — which **works only once the row is retired by
   UPDATE instead of deleted**, per §6. Today this write lands on a row the same turn destroyed.

Free-conversation library offers keep using `SmartPrompt.library` and a `LibrarySection`. The
two coexist: a section is "go and browse", an `exercise_id` is "here is the one that follows
what we just did."

### What it costs

One nullable column: **`admin.exercises.framework_id text references admin.frameworks(id)`**.
One framework may have several exercises (a three-minute and a ten-minute version); an exercise
belongs to one framework or to none. `null` is the ordinary library exercise — which is what
"Two Worry Buckets" becomes under §1 conflict 10. No join table, no new RLS, no new policy:
`admin.exercises` is already the shared read-only catalog.

`SmartPrompt` gains `exercise_id: uuid | None`, **validated against the catalog before it is
persisted or used as control flow** — the same discipline `technique` and `library` already
follow. It is validated even though code writes it, because the field is reachable by the model
and an untrusted identifier is untrusted whatever usually fills it.

### It cannot be tested end to end yet

**`admin.exercises` holds zero rows and no audio file exists anywhere in the repository.**
`mani/storage.py` signs paths to a bucket nothing has uploaded to. So this section is
implementable and unit-testable against a fixture catalog, and unverifiable in a real
conversation until the catalog and its audio land. Do not let a green test suite imply
otherwise.

## 13. Blocked on muhammad

Each of these is a judgement, not an engineering task.

1. **The specification documents themselves**, committed to `backend/docs/specs/`. Blocks
   step 4 and step 5.
2. **Safety protocol wording and the helpline list, per country.** `RESOURCES` is empty by
   design; a wrong number in a crisis panel is worse than no number.
3. **The somatic check-in wording.**
4. **Does `ground` survive alongside `somatic`?** Both existing frameworks end on a `ground`
   phase, and the somatic check-in may be the same move under another name. If it is, `ground`
   is renamed rather than followed, and the §6 CHECK constraint changes shape.
5. **Thought Reframe's stage mapping** — which of its five specified stages maps to which of
   the five persisted content phases (`surface, externalize, explore, land, ground`). It may be
   1:1; that is a clinical judgement, not a guess. Needed before `seed.py` is written.
6. **Rate limit and per-user cost ceiling** (unchanged from [[Backend|PORT-STATUS]]).
7. **The exercise catalog and its audio.** `admin.exercises` is empty and the bucket holds
   nothing, so §12 cannot be verified in a real conversation. Which exercise corresponds to
   which framework is also a clinical judgement, not a mapping to be guessed.
