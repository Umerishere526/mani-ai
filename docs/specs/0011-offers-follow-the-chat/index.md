# 0011. Offers follow the chat, not a phrase list

**Date**: 2026-10-08
**Status**: In Progress
**Decision record**: [rationale.md](rationale.md) (context, premise notes, options considered, rationale, the router probe)

## Summary

Today Mani can offer a set of questions only if the router, a program that matches fixed phrases, found one of those phrases in what the person said. Plain sentences match nothing, so Mani offers nothing. This spec removes the phrase router: Mani decides from the Framework Index it already reads every turn which set fits, and only two safeguards stay in code, the grief veto and the cooldown that holds the first offer back until the person's second message. The urgent case for DBT STOP (an action about to be taken) goes too, so every set is offered on the same timing.

## Requirements

**User stories**:
- As a person who describes my situation in plain words, I want Mani to offer the set that fits what I said, even when I used none of a fixed list of phrases.
- As a person who has just lost someone, I want Mani never to offer Behavioral Activation, as today.
- As muhammad, I want no phrase list to maintain for what fits, so the fit lives in each framework's Starts when, Sounds like and Skip when lines and changes with a reseed.

**Acceptance criteria**:

- **AC-1**: No code decides which set may be offered. `[ctx]` has no `framework_shortlist` line on any turn, and `orchestrator.py` builds no shortlist. On the person's second message with no framework running, `cooldown_passed` is `yes` whether or not any phrase matched, so a message such as "I've been avoiding my friends because I've been overwhelmed, and I feel guilty about ignoring them" gets the same `[ctx]` offer facts as one that matched a phrase. A technique button for a framework in the registry is stored and shown on the turn, and `guards.check` is unchanged: an id not in the registry is still refused. What the model then chooses is told in the prompt (AC-7) and is not something a scripted test can show.
- **AC-2**: The scoring and ranking code is gone. `mani/chat/router.py` is replaced by `mani/chat/vetoes.py`, which holds `ruled_out(phrases_by_framework, messages) -> list[str]` (the ids, in the order given, of every framework with a phrase said as whole words in any of `messages`, matched with `safety.normalize` as today) and the whole word helper it needs. These no longer exist: `Signal`, `Rule`, `shortlist`, `urgent`, `_promote`, `_score_one`, `_fired`, `distinction_rules`, `distinction_problem`, `DISTINCTION_KEYS`, `Registry.distinctions`, `Registry.activations`, and the imports of them in `techniques.py` and `seed.py`. The comment in `rows.py` that calls `activation` the router's input says it holds the phrases that rule a framework out.
- **AC-3**: The grief veto behaves as today. `Registry` reads each framework's `never_offer_when_said` once per load into `Registry.vetoes` (a map of framework id to phrases). A value that is not a list of strings that are non empty after stripping is ignored whole for that framework, with one error logged per load naming the framework id and never a phrase, so a portal edit that skipped the seed cannot rule a framework out by single letters, and cannot flood the log. The orchestrator calls `vetoes.ruled_out(config.registry.vetoes, user_texts)` over the same messages as now (the context window of their messages plus this one). `[ctx]` carries `ruled_out: <ids>` while no framework runs and there is no safety concern, exactly as now.
- **AC-4**: The framework files carry no scoring data. `strong_signals`, `signals`, `redirects` and `distinctions` are deleted from all six files, with the comment blocks that explain them. Only `behavioral_activation.md` keeps an `activation:` block, holding `never_offer_when_said`; the other five files have no `activation:` key. In `scripts/seed.py`, `ACTIVATION_KEYS` is `{"never_offer_when_said"}`, `check_distinctions` and the distinction checks are gone, and the seed refuses a `never_offer_when_said` that is not a list of non empty strings, naming the file. A seed run rewrites `admin.frameworks.activation`, so stale keys leave the database on the next reseed, and the code reads only `never_offer_when_said` in the meantime.
- **AC-5**: There is no urgent case. The `urgent` parameter is gone from `context.cooldown_passed` and `context.build`, `cooldown_passed` is `yes` for a person with no framework when their own message count reaches `offers.clear_offer_after` (2) and not before, and `dbt_stop` has no phrase list. The model may offer `dbt_stop` on the second message like any set, when its Starts when line fits.
- **AC-6**: The `tuning` row loses its `router:` block (`router_min_exchanges`, `recency_weights`, `strong_weight`, `signal_weight`, `promoted_floor`). `RouterTuning`, `Tuning.router` and the helpers only they used in `mani/prompts/tuning.py` (`Weight`, `RecencyWeight`, `_never_increasing`, once nothing else imports them) are deleted. In `tests/unit/test_config_rows.py` the `TUNING_REFUSED` cases that edit `router` and the whole number weights test go. `Tuning` refuses unknown keys, so the code, the `tuning` row and the reseed ship in one change and in the order in *Migration plan*. The `description` in `tuning.md` drops "router weights".
- **AC-7**: The prompts say the new rule, once, in wording muhammad reviews before the reseed (drafts in *Feature design*): `mani_base.md` `offers`, and `response_format.md` `ctx` (`conversation_phase`, and the `framework_shortlist` line deleted). A search of `content/prompts/`, `mani/`, `tests/` and `scripts/` for `shortlist` finds nothing in code or content, and a mention in a comment or test name is renamed. `CTX_KEYS` loses `framework_shortlist` and `test_prompts_name_what_exists.REMOVED` gains it. The existing prompt contract tests pass.
- **AC-8**: The offer log stays and carries ids and one flag, never a word of what was said: `offer on thread <id>: <framework id> cooldown_passed: yes|no`, written on a turn where no framework was running and the reply carries a button with `technique` set. `on_shortlist` and `shortlist` leave it. The `heading_toward` log line and the field stay as they are.
- **AC-9**: The whole `pytest` passes with pristine output. The builder records, in the journal note, the passed, skipped and deleted counts before and after, and the database the integration tests ran against (the local Supabase), and checks that the integration tests were not skipped. The reseed runs only after muhammad accepts the wording, and his acceptance is recorded in the scope row's Tracer line, as spec 0010 did. In the same change, `backend/PORT-STATUS.md` is edited in place: the chat turn steps 2 and 3, the Frameworks paragraph, the four "Decisions in force" lines that name the shortlist, the router or a distinction (the grief veto line, the offer rule, the `activation.distinctions` sentence, and the spec 0007 deploy line), the client list line about phrase lists, and the "Offers under the shortlist gate are unmeasured" open item. `backend/docs/database-schema-reference.md` is updated for the `activation` column and the `admin.frameworks` row. `backend/docs/specs/README.md` no longer maps the client's "What MANI may hear" to the router. The scope's lines that describe the router or the shortlist as current are updated. The comment in `scripts/eval_conversations.yaml` that says an offer waits for the shortlist is corrected. `backend/docs/ai-layer-audit.md` is a dated snapshot with a banner and stays as it is. Scope feature 13's done line is updated (see *Follow-up*).

**Not in this spec**:
- Measuring what Mani offers on plain phrasing. muhammad chose scripted tests only (2026-10-08), so no real model run belongs to this spec. Measuring offers stays under feature 11.
- More word vetoes for the other five frameworks. The Skip when and Never lines are told, and the existing grief veto is the only coded stop.
- Crisis and the safety screen (feature 10). A safety concern still stops every offer through the `safety` line, as today.
- The stage ledger (spec 0010).

## Decision

**Chosen option**: Option 4: the model judges what fits from the Framework Index, and the router is cut down to the grief veto.

Mani offers any set in the Framework Index that its Starts when, Sounds like and Skip when lines say fits, minus `ruled_out`, once it has learned what Starts when names and `cooldown_passed` is `yes`. The phrase scoring, the distinction rules, the shortlist line, the urgent case and the router tuning are deleted.

**Implementation skills**: none (backend Python and seeded content only).

## Rationale

Reasoning and options: see [rationale.md](rationale.md).

## Feature design

**Data model**: no schema change and no migration. `admin.frameworks.activation` (jsonb, an object) goes on existing, holding at most one key, `never_offer_when_said`, a list of strings. The column stays because the veto reads it.

**State transitions**: none. The offer states (offered, accepted, declined) and their cooldowns are unchanged.

**Interface changes** (no HTTP change):

| Where | Before | After |
|---|---|---|
| `[ctx]`, no framework running | `framework_shortlist`, `ruled_out`, `cooldown_passed` | `ruled_out`, `cooldown_passed` |
| `cooldown_passed` for a first message about an action about to be taken | `yes` | `no`, like any first message |
| `mani/chat/router.py` | scoring, ranking, distinctions, urgency, veto | `mani/chat/vetoes.py`: the veto only |
| `tuning` row | `offers`, `router`, `windows`, ... | `router` block gone |
| Framework file frontmatter | phrase lists, redirects, distinctions, veto | the veto, in `behavioral_activation.md` only |
| Offer log | `on_shortlist`, `shortlist`, `cooldown_passed` | `cooldown_passed` |

**Prompt wording** (drafts; muhammad reviews before the reseed):

`mani_base.md`, the `offers` line that names the shortlist becomes the line below. The line before it ("Offer once you can tell which set fits, and do not keep talking once it is clear") already says not to hold an offer back, so this one does not repeat it:

```yaml
  - Offer a set from the Framework Index only once you have learned what its Starts when line names, and only when cooldown_passed is yes. Pick the one whose Starts when and Sounds like lines fit what they told you in their own words, not only the words of its examples. Never offer one its Skip when or Never lines rule out, or one that ruled_out names. If two fit, ask one question that tells them apart first. When they ask for a kind of help, ask about it and follow their answer rather than offering.
```

`response_format.md`, under `ctx`: the `framework_shortlist` line is deleted. `conversation_phase` changes so "understanding" no longer overrides the offer from the second message on:

```yaml
  conversation_phase: understanding means nothing offered yet, so ask one question from what they said until cooldown_passed is yes and a set fits, then offer as offers says. framework means the questions are running, so follow the stage. talking means an offer was declined or the questions finished.
```

The question step in the style guidance reads "Then offer or not, as cooldown_passed, ruled_out and offers say, and start differently from recent_openers." Nothing else names the shortlist.

**Value sourcing**:

| Action | Value | Source |
|---|---|---|
| Whether an offer may be made | `cooldown_passed` | `tuning.offers.clear_offer_after` and the count of their messages (`context.cooldown_passed`) |
| Which sets may not be offered | `ruled_out` ids | `vetoes.ruled_out` over `admin.frameworks.activation.never_offer_when_said` and the person's messages in the context window plus this one |
| Which set fits | the model's choice | the Framework Index (`admin.frameworks.body`, eight lines per framework) in the system prompt |
| Whether the offered id is real | registry membership | `guards.check` against `Registry` (unchanged) |
| The offer log's flag | `cooldown_passed` | `context.cooldown_passed` for the turn |

**Key invariants**:
- No code reads the person's words to decide what is offered, except the grief veto, which only rules a set out.
- A set the person's words rule out is never named as offerable: it is named in `ruled_out` and the prompt says never to offer it.
- A model supplied technique id that is not in the registry is never stored.

**Security model**: no new route and no new data. Conversation text is special category health data: the veto reads it in process as before, and the offer log carries ids and a flag only, so nothing about what was said reaches a log or Sentry.

**Failure and edge cases**:
- A malformed `never_offer_when_said` from a portal edit is ignored for that framework, with a logged error (AC-3).
- A reseed that has not run: the code reads only `never_offer_when_said`, so old keys in the database are harmless. The prompts change only on reseed, so until then the old prompt still tells the model to offer only from a `framework_shortlist` that is no longer sent, and the model offers nothing. The deploy order below prevents that.
- Two sets fit: the prompt says to ask one question that tells them apart before offering. No code decides.
- Safety concern: unchanged. The `safety` line stops every offer. A missing shortlist used to be what also withheld an offer on a first message, during a safety concern and while a framework ran. Those are now carried by `cooldown_passed: no`, the `safety` line, `guards.check` (which drops a technique button while a framework runs), and `ruled_out` being told only while none runs.
- An offered row the person has not answered is on the decline cooldown (4 messages), so `cooldown_passed` can turn `yes` while an offer stands. A reply that sets `state.accepted` to false turns that into a decline, so the risk is low, and this spec leaves it.

**Critical test scenarios** (a scripted model, as in `tests/integration/test_turn.py`; per the project rule these are few, and the ones that already exist are rewritten, not added to):
- A plain sentence at their second message: `[ctx]` has `cooldown_passed: yes` and no `framework_shortlist`, a scripted offer button for `behavioral_activation` is stored as an offer, and the log line carries ids and the flag only. This rewrites the existing shortlist tests in `test_turn.py` and `test_chat_context.py`, verifies **AC-1**, **AC-8**.
- The grief veto: a thread where they say a person died has `ruled_out: behavioral_activation` in `[ctx]`, and a `never_offer_when_said` that is a string is ignored with one error logged without the phrase (a `Registry` test), verifies **AC-3**.
- First message: "I am about to send a message I will regret" at their first message has `cooldown_passed: no`. This rewrites `test_an_imminent_action_is_offerable_on_the_first_message`, verifies **AC-5**.
- Seed refusals: `signals` or `distinctions` in a framework file is refused, as is a string `never_offer_when_said`, verifies **AC-4**.
- The seeded `tuning` row loads with no `router` key. The existing unknown key case already covers a row that still has one, verifies **AC-6**.
- Contract: `CTX_KEYS` and `response_format.md` `ctx` agree in both directions with `framework_shortlist` in neither, verifies **AC-7**.
- A button for an id not in the registry is still dropped (the existing guard test, kept), verifies **AC-1**.

## Migration plan

**Strategy**: no schema migration. One change, shipped whole.
**Phases**:
1. Build after spec 0010's changes are committed. Both specs edit `tuning.md`, `mani_base.md`, `response_format.md`, `context.py`, `orchestrator.py`, `seed.py` and `test_prompts_name_what_exists.py`, so building on top of uncommitted work would tangle them.
2. Local: code, the `tuning` row, the framework files and the prompts change together, then `python scripts/seed.py`, once muhammad has accepted the wording.
3. Order: the seed first, then the code. `cache._parsed` raises a config error when the `tuning` row does not match `Tuning`, so new code on the old row fails on its first load, and old code on the new row fails when its cached snapshot next expires (the seed does not clear the cache, and production reloads every 300 seconds). Seeding first and deploying straight after keeps old instances on their loaded snapshot until the new code lands. Locally, reseed and restart together; a test run against a database seeded by another branch fails the same way. Spec 0010 also edits `tuning.md`, so the two ship through one seed in one order.
4. Hosted: wait for the existing 011 to 017 reconciliation, as spec 0007 did.
**Rollback**: revert the commit and reseed. The content comes back from git and no data was touched.
**Risks**: the offers it removes the gate from are unmeasured (see *Consequences*).

## Build plan

The build approach is Tracer Bullet (scope header): the thin thread through every layer first, then the deletion.

1. Tracer. The orchestrator builds no shortlist and passes no `urgent`; `context.build` drops the `shortlist` and `urgent` parameters and the `framework_shortlist` line, and `cooldown_passed` loses its `urgent` branch; `CTX_KEYS`, the offer log, `mani_base.md` and `response_format.md` are updated with the drafted wording for muhammad's review; the scripted tests for the happy path, first message, contract and guard are written first and pass. The router code is still on disk but nothing calls its scoring, so this slice can be reverted alone. Satisfies **AC-1**, **AC-5**, **AC-7**, **AC-8**.
2. Remove the scoring. `router.py` becomes `vetoes.py` with `ruled_out`; `Registry` drops its distinctions; the orchestrator calls `vetoes.ruled_out`; `seed.py` keeps only the veto key and refuses a malformed one; the six framework files lose their scoring data; the `tuning` row, `RouterTuning` and `Tuning.router` go; `test_router.py` is deleted and its veto tests move to `test_vetoes.py`; the other tests that reach the deleted code are trimmed or rewritten: `test_techniques.py` (the `Registry.distinctions` and "distinction dropped" tests, replaced by one for the veto's validation), `test_seed_frameworks.py` (the `check_distinctions` import, the frontmatter fixture's phrase lists and the distinction cases), `test_config_rows.py` (AC-6), `test_chat_context.py` (the `Signal` import and the shortlist and cooldown tests), and `test_turn.py` (the shortlist, closest fit and urgency tests, around lines 307, 370, 389, 403 to 423, 930, 1201 and 1255). Satisfies **AC-2**, **AC-3**, **AC-4**, **AC-6**.
3. Close out. `PORT-STATUS.md` (flow, Frameworks paragraph, three decisions in force edited in place, client list, the unmeasured item), the schema reference, the eval yaml comment, a journal note under `mani-vault/Journal/`, the reseed after muhammad's yes on the wording, the full `pytest` with the integration count checked. Satisfies **AC-9**.

## Consequences

**Positive**:
- A plain sentence can now reach an offer, which it could not before (2 of 12 plain lines reached any set in the probe in `rationale.md`).
- The phrase lists, the scoring weights, the distinction rules and their seed checks are gone, nearly all of `router.py`, a block of `tuning`, and most of `test_router.py`. There is no list left to grow for what fits.
- Offers have one judge, the model reading the Framework Index, instead of a model and a phrase router that could disagree.
- Per turn work in the orchestrator drops: no scoring over the message window.

**Negative / tradeoffs**:
- Whether the model now offers the right set for plain phrasing is unmeasured, and this spec adds no measurement (muhammad's choice). Spec 0007 added the gate so the model could not offer a set the router saw no sign of, and nothing yet shows how often the model, left alone, would offer a set that does not fit. The guards left are the Starts when and Skip when text, the grief veto, the cooldown and the safety line.
- A person about to send a message they will regret gets no offer in their first message. DBT STOP waits for their second like every set. The client's overview says DBT STOP does not replace the established cadence, which agrees, but it is a change from what shipped.
- Skip when conditions other than grief are told, never checked. A model that offers Behavioral Activation to someone who is simply tired is not caught by code.
- A real deletion: the router's ranking and tests leave the working tree and live on only in git. The client's tie breaker table (ABCDE or Thought Reframe, Thought Reframe or ACT, Behavioral Activation or Structured Problem Solving, Structured Problem Solving or ACT, DBT STOP or another) is now carried only by the Skip when lines. Checked: every pair in that table is named on both sides today. The deleted `redirects` named a few more neighbours, but nothing read them, and the 220 character cap on a line leaves no room to add them.

**Neutral**:
- `heading_toward` stays a field the model writes and a line in the log. Nothing compares it with a router any more.
- No migration, no endpoint, no frontend change.

## Follow-up

- [ ] Measure offers per conversation on plain phrasing, and offers where Skip when applied, under feature 11, with muhammad's yes for each real run.
- [ ] Update scope feature 13. Its done line becomes: a plain sentence with no phrase from any list, such as the avoiding friends line, can be offered a fitting set at the person's second message; the grief veto still keeps Behavioral Activation from someone who has lost a person; the router's phrase lists, scoring and distinction rules no longer exist. Its open question about `heading_toward` is answered: no.
- [ ] After the build, `/sync` marks spec 0007's AC-7, AC-9, AC-10 and AC-11 as changed by this spec.
- [ ] Tell the client that Mani no longer matches phrases to decide what to offer, and that DBT STOP waits for the second message like the others (add to the client list in `PORT-STATUS.md`).
- [ ] If `heading_toward` is still read by nothing but a log line when feature 11 measures offers, decide then whether to drop it.
