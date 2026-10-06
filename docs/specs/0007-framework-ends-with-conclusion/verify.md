# Verify: body check in follows every framework · spec 0007 · updated 2026-10-05
_Steps derived from spec 0007 acceptance criteria. `/check verify` runs these; `/test` locks the durable ones._

## UI / manual
Run the chat tester (`cd chat-tester && source venv/bin/activate && streamlit run app.py`) against the running backend, after `python scripts/seed.py`.
- [ ] ACT Choice Point: play to the last stage and answer → the reply is a short conclusion in the person's words, then the body question, with exactly one question mark        → AC-2, AC-3
- [ ] Each of the other five frameworks: play to the last stage and answer → the body question comes straight after, with no closing question in between        → AC-1, AC-2
- [ ] ACT, Behavioral Activation, Problem Solving and DBT STOP: make the last answer name an action ("I'll pack my bag and go") → the body question is still asked        → AC-4
- [ ] ABCDE at `balanced`: answer "i don't know" → "That is fine. What is one thing about this that you do know is true?"; answer "i still don't know" → a conclusion that says it is okay not to know yet and writes no balanced thought, then the body question        → AC-5
- [ ] Thought Reframe at `reframe`: the same two answers give the same two replies        → AC-5
- [ ] At the last stage send "honestly I don't want to be here anymore" → no conclusion and no body question, and the stage stays where it was        → AC-2
- [ ] At the last stage send "I want to stop" → the client's line "You want to stop here. Would you like to continue chatting?" and no body question        → AC-2
- [ ] Run the same ending in Direct, Supportive and Reflective → the body question is the client's wording for that style, word for word        → AC-2 (value sourcing: the check in question)
- [ ] ABCDE and Thought Reframe: the balanced thought is asked as "what would you say is true about this?", and the evidence against question as "Is there anything you know that doesn't match that thought?" in every style, with no "fairer"        → AC-9
- [ ] A "not knowing" ending names one or two things the person said they know, in their words, and never says what they mean about them        → AC-3
- [ ] No conclusion starts with "It sounds like", names a feeling the person never used, or tells them what to do        → AC-3

## Commands
- [ ] `cd backend && source .venv/bin/activate && python scripts/seed.py` → six frameworks and five prompts load        → AC-1
- [ ] `cd backend && source .venv/bin/activate && pytest` → 1252 passed, 4 skipped, no warnings        → AC-1, AC-7
- [ ] `grep -rn "anything you would add" backend/content` → no match        → AC-1
- [ ] Real model read, only after muhammad says it may run: the two marked up chats in each style, three runs (18), and ABCDE with "I don't know" twice at `balanced` in each style, three runs (9) → every ending has one question mark, no feeling or size word the person never used, no "It sounds like", no repeated opener, and muhammad's read is recorded in the journal        → AC-3, AC-8

## Acceptance-criteria coverage
- AC-1 … no `closing` stage: content test, seed, grep · AC-2 … one message and no check in on a hold, a safety pause or a stop: integration tests, manual steps · AC-3 … what the conclusion says: unverified until the real model read · AC-4 … body check always asked: content test, manual step · AC-5 … gentler question for "I don't know": content test, integration test, manual steps · AC-6 … base prompt: `test_base_prompt` in pytest · AC-7 … tests follow the new shape: pytest · AC-8 … real model read: waits for muhammad
