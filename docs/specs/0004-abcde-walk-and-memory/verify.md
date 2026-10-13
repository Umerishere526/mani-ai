# Verify: The ABCDE walk and its memory · spec 0004 · 2026-10-13
_Steps derived from spec 0004 acceptance criteria. `/check verify` runs these; `/test` locks the durable ones._

## UI / manual
Run in the chat tester against the local backend (`cd chat-tester && streamlit run app.py`) after `python scripts/seed.py`, with `AI_DEBUG_MODE` on so the sidebar shows "What Mani knows". These spend the client's credit, so only with muhammad's yes.

- [ ] Directive. Say only how you feel for three messages, then accept the offer → "A is for Activating Event." then the client's missing line with your feeling word → AC-1, AC-6
- [ ] Answer A with an event → the next reply opens "B is for Belief." then the client's B question as written; no letter line before it, nothing before it → AC-1, AC-2
- [ ] Supportive. Before the offer, say the event and what you started telling yourself; accept → A is the client's Supportive confirm line with your event; the sidebar shows activate and belief stored → AC-3, AC-4
- [ ] Reply "yes" → "B is for Belief.", one sentence with your belief, then one of the four confirm phrases → AC-4, AC-7
- [ ] Reply "no" → no letter line, Mani says it misunderstood and asks; reply with a new belief → "C is for Consequences." → AC-8
- [ ] On C, answer "I don't know" twice → the second moves on to D with D's letter line → AC-2
- [ ] Say no to an offer, keep chatting, then ask for it back → A renders as on any start, with what you said before → AC-3
- [ ] On D, say "actually it started when they moved my desk" → the reply stays on D; the sidebar shows activate with the desk words → AC-8, AC-9
- [ ] Reflective. Seed A and B before the offer, accept → reaching B shows your belief and a confirm phrase, never B's question. (Memory past 20 messages is proved by the scripted 25 message test below, since the two tries rule keeps a live stage short.) → AC-4, AC-9
- [ ] Finish E → the body check in as before; the store is still there in the sidebar after the run retires → AC-2, AC-10
- [ ] Mention wanting to hurt yourself while on C → the reply stays with you, the sidebar store and stage do not change → AC-10

## Automated
- [ ] `pytest` green, including `test_a_turn_costs_exactly_one_provider_call` → AC-11
- [ ] Unit: the merge (higher replaces, lower ignored and logged, `corrected` replaces words, empty or unknown stage ignored) → AC-9, AC-12
- [ ] Unit: confirm phrase pick is stable per thread and never equals the previous stage's → AC-7
- [ ] Integration: A to E with nothing known, seeded walk, plain no, corrected, earlier correction, 25 message memory, concern turn, retire keeps the store → AC-1 to AC-10
- [ ] `grep` finds no `with_ledger_step`, `ledger_stage`, or "never say a stage's letter" in `backend/` → AC-13
- [ ] Logs from a scripted run contain no stored `said` text → AC-12
- [ ] `scripts/scenario_check.py` flags a stage reply without its intro (run once with a scripted model) → AC-1

## Value sourcing (added by /develop, 2026-10-13)
One step per row of the spec's Value sourcing table, each varying the source so a wrong one shows. The live ones spend the client's credit, so only with muhammad's yes; the scripted ones cost nothing.

- [ ] Change one `intro` in `abcde.md`, reseed, reach that stage → the reply opens with the changed line; revert and reseed → Letter line
- [ ] A reply that stays on a stage (a plain no) → no letter line; the next move → letter line again → Whether to show the letter line
- [ ] Set the row to `accepted` at `offering` with SQL, send anything → the reply is A's letter line and the stage is `activate` → Start turn
- [ ] Send `agreed` on a stage reached as an ask → the stage stays and the log says `stage answer invalid: agreed`; two `not_yet` in a row → it moves → The step
- [ ] Seed A as `possible`, then as `known`, in each of the three styles → the same client `confirm` line for that style, with the stored words in the slot → A known or possible (event and client line)
- [ ] Accept with a feeling word, then without one → `missing` with the word, then `ask` for the style, logged `slot empty` → A missing (feeling word and its fallback)
- [ ] B known with a model sentence that ends in "?" → the question is dropped and the phrase follows; with no usable sentence → "You mentioned {said}." → B to E known, the naming sentence
- [ ] Two threads reaching B, C and D → each thread keeps its own phrase per stage, and B, C and D never repeat back to back → The confirm phrase
- [ ] Reach C with nothing stored, in each style → C's `ask` for that style, word for word → B to E missing
- [ ] Seed D as `partial`: a gap question with "?" is sent; a text with none falls back to D's `ask`, logged `gap asks nothing` → Partial
- [ ] Say "no" to a confirm → the model's own follow up, no letter line → After a no
- [ ] Read the `[ctx]` `next:` line before and after a turn that stores B as known → it names B's branch from the store before the turn; the render logs `branch changed` when the turn itself changed it → What the model writes
- [ ] Switch the thread's style (PATCH `conversation_style`) mid walk → the next stage's client lines come in the new style → Style
- [ ] Store a stage, then send 25 messages with no updates → `[ctx]` still lists its words and status → Stored words in [ctx]
- [ ] Put the event only in the thread summary (older than the 20 message window), then accept → A is the confirm line with that event (live run; it checks how seeding over or under reports) → Seed

## First live run fixes (added by /debug and /develop, 2026-10-13)
From muhammad's Directive run on thread ca968cbd, where a yes to A's check stayed on A.

- [ ] Seed A before the offer, tap Try it, answer A's check with just "yes" → the next reply opens "B is for Belief." and the sidebar shows the stage on belief → AC-2, AC-4
- [ ] Every stage reached is one paragraph: "A is for Activating Event. From what you've shared, ..." with no blank line after the letter line → AC-1
- [ ] Event words stored with a capital ("The client changes...") read lowercase inside A's line; words starting "I" or "I'm" keep the capital → AC-4
- [ ] `pytest tests/unit/test_schema.py::test_no_stage_field_reads_a_yes_to_a_check_as_the_start_turn tests/unit/test_walk.py::test_their_words_inside_a_line_start_lowercase_except_i` → both pass → AC-1, AC-2, AC-4
