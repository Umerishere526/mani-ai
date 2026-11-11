2026-11-10

# Production and harness audit: what the data says, and that the design is the suspect

Read-only audit of `backend/mani`, `backend/supabase`, `chat-tester`, the live API and its database. Nothing was
changed, no model call was paid for, no migration or seed was run. History, not rules. Proposals from it are not
decided: see the session's report to muhammad. "Inferred" marks what was not read directly.

## What production is (verified 2026-11-10)

- `mani-api-git-main-mymani.vercel.app` is Vercel project `mani-api` (team `mymani`), commit `959fb4b` = local `main`,
  region iad1, Fluid on. The Vercel MCP cannot see this project (it lists only the old `mani-backend`); the `vercel`
  CLI can.
- Its database is `aipgficduzufstilndbw` "mani-app": the burst of 2026-11-09 20:43 to 20:54 UTC is in both Vercel's
  request records and that project's `admin.llm_calls`; the other hosted project stopped at 2026-11-06 17:53.
  Migrations 000 to 035 all applied. The seven active prompt rows match `content/prompts/` (md5 of the body).
- Last 3,000 request records (2026-11-09 20:43 to 2026-11-10 15:40 UTC): no 5xx, no 429; 28 sends and 5 edits
  answered 409; the catch-up cron answered 200 every 5 minutes.
- `AI_DEBUG_MODE` is on (inferred: 371 of 374 traces carry `raw_reply`, 20 of 20 today). Every turn returns
  `understanding` and `trace` to the caller and stores the raw reply, and the turns composed by `compose_moment` get
  the Debug layer in the system prompt. Fine for testers, to be off before a real person signs up.
- `/docs` and `/openapi.json` answer 200 without auth. `SENTRY_DSN` is not among the production env names.

## Numbers (hosted database)

- 17 accounts, 7 with a thread, 6 with 20+ messages. 73 threads, 59 with 3+ messages from the person. All testers.
- 2026-11-09, 20:43 to 20:54 UTC: 1,034 chat and 856 reading calls with no user and no thread, each with a real
  generation id, through the live API (about 1,000 sends and 975 follow-ups in Vercel's records). A load run against
  production with the real model (inferred). It is 85% of all reading rows and half of all chat rows, so every
  figure must be filtered `user_id is not null`. See [[measure-before-tuning-prompts]], "test residue".
- People only, since 2026-11-06: chat p50 9.5 s, p95 19.7 s (175 calls). The reading after the reply p50 20.3 s,
  p95 56 s, and 13 of 91 timed out. Memory fold p50 29 s, 2 of 26 timed out.
- People only, all time: a chat call reads 10.6k input tokens (64% cached) and writes 655 (438 reasoning); a reading
  reads 18k and writes 1,288. The reading costs more than the reply and takes twice as long.
- 80 of 138 readings landed after the person's next chat call had started. On those turns the note was built
  without the reading of the message before, so the picture was two messages behind, not the one PORT-STATUS
  describes.
- List price of everything in `admin.llm_calls` is about $3. Cost does not constrain the model choice.
- Funnel: 36 of 59 real threads reached an offer, the first at the person's 8th message (median; 6 to 23).
  Inferred from the one-row-per-thread state table: about a third of the runs finished; a run takes 8 stage turns
  (median), 27 at most.
- Chat reply shapes (170 traced turns since 2026-11-04): window 43%, open_ask 27%, reflect 14%, insight 7%,
  acknowledge 3%, practical 0. The model set `asked_for_help` on 15 turns in 6 threads: 7 got a small idea, none the
  practical shape.
- The model set `frustrated` on 19 turns in 7 threads; 12 of them in two threads. One is a safety test of 2026-11-06
  where holding the concern through refusals is the decision in force. Two are from 2026-11-10, on the current
  prompts: in one the person objects first to being asked question after question and then to a reply that only
  said their words back. A self-report by the model: good for choosing what to read, not a rate.
- Reply checks: 17 of the 28 chat misses are "solution in chat" on phrases that are not solutions. Mostly noise.
- `thread_summaries` 0 rows, `crisis_events` 5 with none resolved (nothing writes it).

## The design reading

`mani/chat` holds 32 numeric thresholds, 37 regexes and, with `schema.py`, 148 dated references to one chat or
meeting. `converse.AGREED` and `SAID_YES` are phrase lists, against "No phrase lists judge the conversation"
(2026-10-09). A note line sent to the model ends "(the client meeting, 2026-11-05)". PORT-STATUS still describes
`converse.HELP_MOVES`, which a test asserts is gone.

The client's complaint classes that came back on three or more dates: wrong or shallow core (8 dates), asks again
(7), only questions and not helped (7), framework mechanics (7), offer timing (5), mirroring (5), tone (5), safety
(4), endings (4). Each return followed a recorded fix. Failure classes 1 and 3 of
[[failure-classes-from-later-branches-2026-10-21]] are still running: one transcript, one rule, no baseline.

Where help lives: the chat may give one small idea and never a fix, the two active frameworks look at a thought, and
Structured Problem Solving is paused. Practical help is Plan Next Step, after a thought framework. Helping in the
chat was built 2026-10-27 and reversed 2026-10-29 after the client's test.

## What exists for measuring, and what does not

- On `main`: `scripts/scenario_check.py` with 43 scripted conversations (263 fixed lines), regex and field-read
  flags, `--save`, `compare_runs.py`. No simulated person, no scored reading of comprehension or help, no stored
  baseline, no repeated runs, no prompt hash on a run or a call (`llm_calls.prompt_version_id` is always null).
- Unmerged, `agentic-implementation` (snapshot 2026-11-03, 33 commits behind `main`): prompt hashes printed by
  `scenario_check` and `seed.py --check`, a refusal to run on stale prompts, and
  `docs/superpowers/plans/2026-11-01-mani-evaluation-and-release.md` (typed run results, held-out cases, an offline
  validator, a side reviewer of transcripts).
- Unmerged, `feat/feedback-per-response` (2026-11-05): thumbs on a reply. The client had not decided on it.

## What was read directly

Aggregates, plus one sample: the 19 turns flagged `frustrated`, Mani's reply before each and the person's message,
cut to 260 characters, by SQL as `postgres`. That read is not in `admin.thread_reads`.
