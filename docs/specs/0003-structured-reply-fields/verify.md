# Verify: Structured reply fields · spec 0003 · updated 2026-10-12
_Steps derived from spec 0003 acceptance criteria. `/check verify` runs these; `/test` locks the durable ones._

## UI / manual
Run in the chat tester against the local backend (`cd chat-tester && streamlit run app.py`) after `python scripts/seed.py`. These spend the client's credit, so only with muhammad's yes.

- [ ] Supportive, five messages about a coworker → the offer is the client's two line ABCDE template word for word, only the `<...>` parts changed, then "Would you like to try it?", with Try it, Tell me more, Keep chatting → AC-2
- [ ] Same in Directive → one line template, no lead line → AC-2
- [ ] First message in any style → no offer, the reply ends on a question → AC-1, R1
- [ ] Tap Tell me more → the client's five step explanation in the thread's style, then the permission question, with Try it and Keep chatting → AC-4
- [ ] Type "no thanks" to an offer → the client's Keep chatting line for the style with their words in its slot, no buttons → AC-4
- [ ] Type something new instead of answering → Mani follows it in its own words, no buttons; three replies later an offer may come again → AC-4
- [ ] Tap Keep chatting → declined, whatever the reply says → AC-4
- [ ] Type "yes let's do it" → the first stage question, already past any stage their earlier words answer → AC-4
- [ ] After E: say "a bit calmer, it's in my chest" → the client's chest practice for the style, word for word, no buttons → AC-5
- [ ] At the check-in: "not sure where" → Mani's first sentence then the client's where question, with Chest, Head, Stomach, Somewhere else; tap Head → the head practice → AC-5
- [ ] At the check-in: "I'd rather not" → the client's decline line with Chat More and Go to Library → AC-5, AC-6
- [ ] At the check-in: "my chest hurts and I can't breathe" → the client's safety line, no practice, no buttons → AC-5
- [ ] After the practice: "it calmed then came back" → the client's returning text with Chat More and Go to Library → AC-5, AC-6
- [ ] A reply that only says "keep chatting or go to the library" mid route → no buttons → AC-6
- [ ] "Honestly I don't want to be here anymore" while an offer is open or on the body route → only Mani's text, no template, no buttons, the stage held → AC-12
- [ ] Backend log for an offer turn → a line `moment chatting: offer_answer None, body None, offered abcde`, and none of their words from the slots → AC-10

## Commands
- [ ] `cd backend && source .venv/bin/activate && pytest` → all pass, integration tests not skipped (only the 4 JWKS auth skips) → AC-1 to AC-10, AC-12
- [ ] `pytest tests/integration/test_turn.py -k one_provider_call` → one call per turn → AC-8
- [ ] `pytest tests/unit/test_abcde_content.py -k costs_less_prompt` → the supportive open offer turn is under 35,752 characters (30,718 on 2026-10-12) → AC-9
- [ ] `grep -rn "re.compile" mani | grep -v safety.py` → only the patterns listed under "Kept on purpose" → AC-7
- [ ] `python scripts/seed.py` then start the app → loads; with a framework seeded without branch ids it refuses, naming the missing branch → AC-5 (migration risk)
- [ ] After muhammad's yes: `python scripts/scenario_check.py` → every offer and Keep chatting line matches the client's template, the `answering_the_offer` group runs a no, a moved on and a yes through the body route, and the summary reports how many replies carried offer words in their own text → AC-11

## Value sourcing (each value's source, varied at the edge that breaks if it is wrong)
- [ ] Moment: an offered row with no buttons showing (Tell me more answered on a concern) still takes a typed yes → `context.moment`, `pending_offer`
- [ ] Offer field: present only from the person's third message, and absent again inside the cooldown after a decline → `offer_window`
- [ ] Slot descriptions: switch style and read the schema sent → each style's own `<...>` text, Directive with no `lead_line` → the style's templates
- [ ] Framework: `heading_toward` naming an unknown id, or the one just finished → no offer, `offer unusable` logged → registry, finished row
- [ ] Template and style: the rendered offer changes with `conversation_style` → `offering.offer[style]`, `resolve_style`
- [ ] Explain: Tell me more in each style → `offering.explain[style]` of the offered row's framework
- [ ] Keep chatting: `their_words` empty → the model's text and a `keep chatting unusable` note → `offering.keep_chatting[style]`
- [ ] Body branch: each id sends its own `somatic.md` text in the thread's style → branch `id`
- [ ] Place tap: tapping Somewhere else gives the elsewhere practice whatever the reply reported → stored label to body value
- [ ] Check-in question: moving from E to the check-in replaces Mani's question with the style's check-in → `somatic_checkin.ask[style]`
- [ ] Handoff: shown once; a retiring turn after it was shown carries none → `_handoff`, `_offered_handoff`
- [ ] First sentence: no_place after a reply that opens with a question keeps no question of the model's → `first_sentence`

## Acceptance-criteria coverage
- AC-1 … the moment and schema steps, `test_each_moment_carries_only_the_fields_that_mean_something_in_it`, `test_the_moment_is_read_from_the_database_and_the_safety_screen_alone`
- AC-2 … the Supportive and Directive offer steps · AC-3 … the unknown or finished framework step
- AC-4 … Tell me more, no, moved on, Keep chatting tap, yes · AC-5 … the body route steps · AC-6 … the handoff steps
- AC-7 … the grep · AC-8 … the one call test · AC-9 … the prompt size test · AC-10 … the log step
- AC-11 … the scenario check run, owed · AC-12 … the concern step
