# Production chat latency report: 2026-11-05

Read-only. Window: 2026-11-01 00:00 UTC to 2026-11-05 15:44 UTC. The first call in the window is at 2026-11-03 12:12 UTC.
Database: `aws-0-ca-central-1.pooler.supabase.com:5432/postgres` (hosted Supabase project `heqenombgkihfeggrxqc`, Postgres 17.6),
reached with the `DATABASE_URL` in `backend/.env.hosted`. No code, prompts, settings or data were changed, and no model calls were made.
This report contains only aggregates, ids (thread ids cut to 8 characters), token counts and timings.

## 1. Summary

1. **Thinking before the first token.** OpenAI takes p50 6.0 s (p90 12.6 s) to send the first token, about 75% of each chat call. That adds up to 1,057 of 1,612 s of generation time. Reasoning is 65% of output tokens (avg 599 per call at effort `medium`).
2. **The length of the structured reply.** Latency follows output tokens almost exactly (r = 0.94; latency_ms ≈ −279 + 12.4 × output_tokens). The visible JSON averages 317 tokens and takes 555 s in total after the first token. Calls with 1,500+ output tokens take p50 21–29 s.
3. **Deadline failures, plus time outside the model.** 3 of 154 chat calls hit the 30 s deadline and ended as an error the person saw. Platform overhead per chat call is small: our latency minus OpenRouter's generation_time is p50 0.33 s. A cold start on Vercel took 6.2 s on `/health`. The request time outside the model call could not be measured, because no hosting logs were available.
4. Chat p50 9.8 s, p90 19.6 s, max 29.2 s. 75 of 154 chat calls took over 10 s, 32 over 15 s, 18 over 20 s, and 1 hit 30 s.
5. **Prompt cache.** It resets on every change of reply schema: on the first call after a schema change, 12 of 15 calls had 0 tokens cached, against 4 of 79 when the schema stayed the same. In this data, uncached input does not lengthen the wait (r = −0.29 with latency).
6. **Background work.** The background understanding and memory-fold calls spend p50 6.3 s and p90 22–33 s outside OpenRouter's generation time. 15 of 49 understanding calls timed out. Two background retries never wrote their second row. This is consistent with Vercel suspending or ending the function once the response is sent.

## 2. Baseline report

`scripts/latency_report.py --since 2026-11-01` against prod, output verbatim:

```
chat calls since 2026-11-01 00:00 UTC
154 chat call(s): 151 ok, 3 failed and retried or given up

  all ok calls: 151 call(s)
    time      median 9.8 s, p90 19.9 s, slowest 29.2 s
    input     median 15315 tokens, 67% cached
    output    median 877 tokens: 516 thinking, 233 written
    speed     median 11.9 ms per output token
  directive: 121 call(s)
    time      median 9.9 s, p90 21.2 s, slowest 29.2 s
    input     median 15458 tokens, 67% cached
    output    median 901 tokens: 575 thinking, 239 written
    speed     median 11.7 ms per output token
  supportive: 30 call(s)
    time      median 8.8 s, p90 13.5 s, slowest 16.1 s
    input     median 14915 tokens, 63% cached
    output    median 702 tokens: 482 thinking, 214 written
    speed     median 12.2 ms per output token

  time by how much the reply wrote (thinking included):
         0-500 tokens:  25 call(s), median 4.9 s
      500-1000 tokens:  71 call(s), median 8.3 s
     1000-2000 tokens:  52 call(s), median 15.4 s
     2000-4000 tokens:   3 call(s), median 28.7 s

  retries (each adds its own time to the turn):
    timeout: 3 call(s), 90.0 s in all, median 30.0 s each

  the 10 slowest ok calls:
     29.2 s  directive  in  16024 ( 15055 cached)  out  1810 ( 1011 thinking)  2026-11-03 12:18 thread 219da449
     29.1 s  directive  in  17314 ( 15718 cached)  out  2054 ( 1230 thinking)  2026-11-03 12:28 thread 219da449
     28.7 s  directive  in  17784 ( 16273 cached)  out  2058 ( 1296 thinking)  2026-11-03 12:32 thread 219da449
     28.6 s  directive  in  15495 ( 14868 cached)  out  1876 ( 1270 thinking)  2026-11-03 12:40 thread a64eac70
     26.9 s  directive  in  16701 ( 15483 cached)  out  1932 (  873 thinking)  2026-11-03 12:22 thread 219da449
     25.3 s  directive  in  16426 ( 15592 cached)  out  1959 ( 1034 thinking)  2026-11-03 13:00 thread d4efc3a3
     24.6 s  directive  in  15794 ( 14997 cached)  out  1835 (  744 thinking)  2026-11-03 13:14 thread 45c568d8
     23.4 s  directive  in  15432 ( 14813 cached)  out  1681 (  900 thinking)  2026-11-03 12:14 thread 219da449
     21.9 s  directive  in  15754 ( 14928 cached)  out  1359 (  790 thinking)  2026-11-03 12:41 thread a64eac70
     21.4 s  directive  in  15458 ( 14581 cached)  out  2185 ( 1997 thinking)  2026-11-04 19:39 thread 12baf58c
```

Notes on reading it:

- The script's p90 (19.9 s) is `statistics.quantiles(n=10)`. The p90 values in section 4 (19.6 s) use linear interpolation.
- "failed and retried or given up" covers the 3 timeouts. All 3 were given up, not retried; see section 5.

## 3. Prod config vs repo

Active rows in prod `admin.prompts` (content not read; only `length(content)` compared):

| name | model_id | model_parameters | routing | updated_at (UTC) |
|---|---|---|---|---|
| voice | openai/gpt-6-luna | `{"reasoning_effort": "medium"}` | `{}` | 2026-11-04 22:09 |
| conversation | openai/gpt-6-luna | `{"reasoning_effort": "medium"}` | `{}` | 2026-11-04 22:09 |
| framework | (null) | `{}` | `{}` | 2026-11-04 22:09 |
| moments | (null) | `{}` | `{}` | 2026-11-04 22:09 |
| summarization | openai/gpt-6-luna | `{"maxTokens": 500, "reasoning_effort": "high"}` | `{}` | 2026-11-04 22:09 |
| memory_fold | openai/gpt-6-luna | `{"maxTokens": 800, "reasoning_effort": "high"}` | `{}` | 2026-11-04 22:09 |
| title_generation | (null) | `{}` | `{}` | 2026-11-04 22:09 |

Inactive rows still present: `mani_base`, `response_format`, `style_directive`, `style_reflective`, `style_supportive` (last updated 2026-10-30).

**Which row drives a chat call.** `composer.model_settings(config)` reads only the `voice` row. Every chat call and every `understanding` call therefore runs `openai/gpt-6-luna` at effort `medium` with `maxTokens` unset, so 2048 + 8192 = `max_completion_tokens` 10240. The `model_id` and `model_parameters` on `conversation`, `framework` and `moments` are not read for the call.

**Repo comparison.** The front matter of `content/prompts/voice.md`, `conversation.md`, `summarization.md` and `memory_fold.md` matches prod exactly (model and parameters). `framework.md`, `moments.md` and `title_generation.md` carry no model front matter, which matches the nulls. All 7 active prompt bodies have the same length in prod as in the repo: 22557, 34715, 11671, 4709, 1421, 2181 and 173 characters. No difference found.

**When prod was last seeded.** All active prompt rows and `admin.frameworks` were last written at **2026-11-04 22:09 UTC**. `admin.exercises` was last written on 2026-10-26 22:01. `admin.prompt_versions` is empty, so no earlier seed time is recorded; `updated_at` is overwritten on every seed. In git, `reasoning_effort: medium` was last changed on 2026-10-29 (`ff2e323`), so the effort was the same for the whole window, assuming prod had been seeded since then. Prompt *text* was changed in `114285b` (2026-11-03 23:21 UTC) and `5dfa952` (2026-11-04 17:07 UTC), and which text prod ran before the 11-04 22:09 seed cannot be determined. 149 of the 151 ok chat calls predate that seed.

Prod migrations run up to `030_body_check_in_without_feeling_step`, the same as the repo.

## 4. Call-level numbers

All calls in the window used `openai/gpt-6-luna`. Purposes present: `chat` 154, `understanding` 49, `memory_fold` 12. The enum also allows `summarize` and `exercise_select`, which have no rows in the window.

| | chat | understanding | memory_fold |
|---|---|---|---|
| count | 154 | 49 | 12 |
| ok / timeout / schema_invalid / provider_error | 151 / 3 / 0 / 0 | 34 / 15 / 0 / 0 | 9 / 3 / 0 / 0 |
| latency_ms, all rows: p50 / p90 / p99 / max | 9876 / 20363 / 30000 / 30001 | 25308 / 116571 / 316778 / 335002 | 22836 / 317129 / 408472 / 416532 |
| latency_ms, ok only: p50 / p90 / p99 / max | 9761 / 19591 / 28891 / 29193 | 16486 / 46232 / 54573 / 55130 | 22188 / 34310 / 47530 / 48999 |
| input tokens avg / p90 | 15114 / 16679 | 17816 / 18384 | 1998 / 2659 |
| cached input avg / p90 | 10053 / 15185 | 13887 / 17733 | 0 / 0 |
| uncached input (input − cached) avg / p90 | 5060 / 14470 | 3929 / 17235 | 1998 / 2659 |
| output tokens avg / p90 | 916 / 1514 | 900 / 1235 | 1382 / 2066 |
| reasoning tokens avg / p90 | 599 / 1034 | 514 / 717 | 763 / 1366 |
| visible output (output − reasoning) avg / p50 / p90 | 317 / 233 / 628 | 386 / 383 / 561 | 619 / 688 / 734 |
| cache ratio (Σcached / Σinput) | 66.5% (33 calls with 0 cached) | 77.9% (7 with 0) | 0% |
| reasoning share of output (Σ) | 65.4% | 57.1% | 55.2% |
| ms per output token, p50 | 11.9 | 17.9 | 13.9 |

Token figures are over ok calls. Timeouts record 0 tokens.

### Chat only

Latency by reasoning tokens (ok calls):

| reasoning_tokens | n | p50 | p90 |
|---|---|---|---|
| 0–200 | 19 | 4.2 s | 7.9 s |
| 200–500 | 51 | 7.3 s | 13.2 s |
| 500–1000 | 61 | 11.0 s | 20.5 s |
| 1000+ | 20 | 15.5 s | 28.8 s |

Latency by output tokens (ok calls; reasoning included):

| output_tokens | n | p50 | p90 |
|---|---|---|---|
| 0–500 | 25 | 4.9 s | 5.8 s |
| 500–1000 | 71 | 8.3 s | 11.5 s |
| 1000–1500 | 38 | 13.9 s | 18.8 s |
| 1500–2000 | 14 | 21.4 s | 28.0 s |
| 2000+ | 3 | 28.7 s | 29.0 s |

Latency by visible output (output − reasoning):

| visible tokens | n | p50 | p90 |
|---|---|---|---|
| 0–200 | 44 | 5.9 s | 12.3 s |
| 200–400 | 70 | 9.7 s | 14.1 s |
| 400–800 | 30 | 17.8 s | 23.9 s |
| 800+ | 7 | 24.6 s | 27.7 s |

Correlation of latency with (151 ok chat calls):

| variable | Pearson | Spearman | least-squares fit |
|---|---|---|---|
| output_tokens | +0.94 | +0.95 | latency_ms = −279 + 12.43 × output |
| reasoning_tokens | +0.74 | +0.82 | latency_ms = 3288 + 13.06 × reasoning |
| visible output | +0.80 | +0.75 | latency_ms = 3912 + 22.67 × visible |
| input_tokens | +0.37 | +0.50 | — |
| uncached input | −0.29 | −0.20 | — |

Chat calls over a threshold (all 154 rows; ok-only in brackets): over 10 s **75** (72), over 15 s **32** (29), over 20 s **18** (15), over 30 s **1** (0). The single one over 30 s is a deadline timeout at 30,001 ms.

Chat by moment, from `admin.turn_traces`, which only exists from 2026-11-04 17:57 UTC; see Gaps:

| moment / schema | n | p50 | p90 | output p50 | reasoning p50 | cache |
|---|---|---|---|---|---|---|
| (no trace, before 11-04 17:57) | 47 | 15.9 s | 25.9 s | 1131 | 647 | 76% |
| in_stages | 44 | 10.3 s | 14.8 s | 995 | 742 | 65% |
| chatting | 30 | 7.4 s | 11.8 s | 666 | 417 | 65% |
| body | 18 | 5.1 s | 9.3 s | 358 | 188 | 61% |
| chatting, may_move | 10 | 9.1 s | 11.7 s | 775 | 554 | 54% |
| offer_open | 2 | 8.0 s | 9.5 s | 678 | 438 | 0% |

Chat by UTC day:

| day | n | p50 | p90 | reasoning p50 | output p50 | cache |
|---|---|---|---|---|---|---|
| 11-03 | 38 | 18.4 s | 27.4 s | 730 | 1345 | 76% |
| 11-04 | 111 | 8.2 s | 13.5 s | 497 | 711 | 64% |
| 11-05 | 2 | 7.0 s | 8.6 s | 252 | 426 | 0% |

On 11-03 the replies were longer, with the same model and effort. The prompt text in prod that day is unknown; see section 3.

## 5. Retries and failures

**How retries were identified.**

- `client.complete` writes one `admin.llm_calls` row per attempt.
- An attempt that is retried has an `error_message` starting `attempt N/2, retrying:` (first-token cut or transient provider error) or `attempt 1/2:` (schema failure).
- Error text was classified inside SQL and never selected.
- Each non-ok row was then paired with the next row of the same purpose in the same thread.

**Chat: no turn needed a second attempt in the window.**

- First-token cuts at 15 s: **0**.
- `schema_invalid`: **0**.
- `provider_error`: **0**.
- Extra wait added by automatic retries: **0 s**.

**Chat turns that ended in a failure the person saw: 3.** All three are `timeout` rows of exactly 30.0 s with no "retrying" marker. That is the whole-call `chat_deadline_seconds` (`asyncio.wait_for`), which `client.complete` does not retry. The person got "Mani took too long to answer". `complete()` runs before the turn writes anything, so the person's message is not stored.

| when (UTC) | thread | latency | what followed in the thread |
|---|---|---|---|
| 11-03 13:02:23 | d4efc3a3 | 30.0 s | no further chat call |
| 11-03 13:18:01 | 45c568d8 | 30.0 s | no further chat call |
| 11-04 17:42:38 | e4ba739b | 30.0 s | next chat call ok 224 s later, presumably a resend |

These count failures that wrote an `llm_calls` row. Failures with no model row, such as a database error or the function being cut off, cannot be seen without hosting logs. Two related observations:

- 4 ok chat calls have no `message_id`: e4ba739b ×3 at 17:46, b7bd9a7b ×1 at 17:57, all before traces existed. The link is set by a `fire_and_forget` task, and `message_id` is nulled when a message is deleted (edit/rewind deletes messages). From the data alone this could be a turn that rolled back after the model call, an edited turn, or a link task that never ran.
- In the window, people sent 159 stored messages against 151 ok chat calls. The 8-message difference is unexplained. Some turns never call the model, for example a safety-screen reply.

**Background calls (not on the person's wait).**

| purpose | timeouts | kind | latency of those rows |
|---|---|---|---|
| understanding | 15 of 49 | 14 final (read timeout, not retried by design), 1 cut after the first-token wait and retried, ok 8 s later | 61–335 s |
| memory_fold | 3 of 12 | 1 final read timeout (82 s); 2 marked "retrying" (343 s, 417 s) | 82–417 s |

- **Both `memory_fold` "retrying" rows have no second attempt recorded.** For 12baf58c at 11-05 14:40:33 nothing followed. For b987e1c3 at 11-04 19:01:39, the next memory_fold row is 19.5 h later. The retry started and never wrote its row, which is consistent with the process being suspended or ended (section 9).
- The configured first-token wait for these calls is `LLM_TIMEOUT_SECONDS` (60 s by default), yet the rows record 61–417 s.

## 6. Prompt cache

**What records a turn's moment and shape.**

- `admin.turn_traces.trace->>'moment'` (`chatting`, `in_stages`, `body`, `offer_open`, `check_open`) and `trace->>'may_move'` (chat turns only). The trace joins to the chat call through `turn_traces.llm_call_id`. Only these closed keys were read.
- `understanding` calls are recognised by `purpose = 'understanding'`.
- "Schema key" below means `moment`, plus `may_move` on chatting turns. It does not capture `slots` or `declined_row`, which also change the shape; a `may_move` turn whose `slots.going_through` is empty still sends plain `ConversationReply`.
- Traces start at 2026-11-04 17:57 UTC, so the 11-03 threads show `?`.
- "Turn" is the count of ok chat calls in the thread. Rows in between belong to the turn before them.
- Of 14 threads with calls, 8 have at least 6 chat calls.

### Five representative threads

**12baf58c** (all moments; 48 turns, abridged where nothing changes):

| turn | purpose | moment/shape | outcome | input | cached | ratio | latency s |
|---|---|---|---|---|---|---|---|
| 1 | chat | chatting | ok | 14412 | 0 | 0% | 5.1 |
| 1 | understanding | understanding | timeout | 0 | 0 | – | 84.2 |
| 1 | understanding | understanding | ok | 17246 | 17145 | 99% | 8.0 |
| 2 | chat | chatting | ok | 14555 | 0 | 0% | 6.0 |
| 2 | understanding | understanding | ok | 17346 | 0 | 0% | 8.0 |
| 3 | chat | chatting | ok | 14819 | 14270 | 96% | 4.3 |
| 3 | understanding | understanding | ok | 17486 | 17144 | 98% | 19.0 |
| 4–8 | chat | chatting | ok | 14904–15292 | 14320–14523 | 95–96% | 4.9–9.0 |
| 9 | chat | chatting | ok | 15458 | 14581 | 94% | 21.4 |
| 10 | chat | chatting, may_move | ok | 16339 | **0** | 0% | 5.6 |
| 10 | understanding | understanding | ok | 18080 | 17528 | 97% | 10.4 |
| 11 | chat | chatting, may_move | ok | 16426 | 14919 | 91% | 7.4 |
| 12 | chat | chatting, may_move | ok | 16573 | 14978 | 90% | 10.0 |
| 13 | chat | offer_open | ok | 12638 | **0** | 0% | 9.9 |
| 14 | chat | in_stages | ok | 14281 | **0** | 0% | 6.5 |
| 15 | chat | in_stages | ok | 14789 | 11407 | 77% | 7.5 |
| 16–29 | chat | in_stages | ok | 14882–16659 | 11407 (every call) | 68–74% | 6.1–16.4 |
| 30 | chat | chatting | ok | 17175 | 14177 | 83% | 7.3 |
| 31–32 | chat | chatting | ok | 17191–17234 | 16069–16104 | 93% | 8.4–9.8 |
| 33 | chat | chatting, may_move | ok | 18141 | 14395 | 79% | 6.9 |
| 34–44 | chat | in_stages | ok | 15658–17563 | 11407 (every call) | 65–73% | 6.8–17.5 |
| 45 | chat | body | ok | 13945 | **0** | 0% | 4.4 |
| 46–48 | chat | body | ok | 14130–14277 | 9692 (every call) | 68–69% | 4.9–9.0 |

**452e18e6:**

| turn | purpose | moment/shape | outcome | input | cached | ratio | latency s |
|---|---|---|---|---|---|---|---|
| 1 | chat | chatting | ok | 14444 | 0 | 0% | 5.2 |
| 1 | understanding | understanding | timeout | 0 | 0 | – | 113.9 |
| 2 | chat | chatting | ok | 14593 | 0 | 0% | 6.4 |
| 2 | understanding | understanding | timeout | 0 | 0 | – | 76.2 |
| 3 | chat | chatting | ok | 14775 | 14361 | 97% | 9.7 |
| 3 | understanding | understanding | timeout | 0 | 0 | – | 113.6 |
| 4 | chat | chatting | ok | 14900 | 14448 | 97% | 10.7 |
| 5 | chat | ? (no trace) | ok | 14984 | 14536 | 97% | 9.5 |
| 5 | understanding | understanding | timeout | 0 | 0 | – | 98.4 |
| 6 | chat | chatting | ok | 15095 | 14600 | 97% | 10.9 |
| 6 | understanding | understanding | ok | 17704 | 17474 | 99% | 41.9 |
| 7 | chat | chatting | ok | 15195 | 14690 | 97% | 11.7 |
| 7 | understanding | understanding | ok | 17769 | 17564 | 99% | 53.4 |
| 8 | chat | chatting | ok | 15473 | 14763 | 95% | 5.0 |
| 8 | understanding | understanding | ok | 18045 | 17637 | 98% | 20.4 |
| 9 | chat | chatting | ok | 15677 | 14830 | 95% | 13.2 |
| 9 | understanding | understanding | timeout | 0 | 0 | – | 294.5 |
| 10 | chat | chatting, may_move | ok | 16641 | **0** | 0% | 11.0 |
| 10 | understanding | understanding | ok | 18279 | 17752 | 97% | 34.7 |
| 11 | chat | chatting, may_move | ok | 16739 | 15291 | 91% | 13.5 |
| 11 | understanding | understanding | ok | 18417 | 17833 | 97% | 15.2 |
| 12 | chat | offer_open | ok | 12819 | **0** | 0% | 6.1 |
| 13 | chat | in_stages | ok | 14412 | **0** | 0% | 14.5 |
| 14 | chat | in_stages | ok | 14930 | 11438 | 77% | 7.2 |
| 15 | chat | in_stages | ok | 15019 | 0 | 0% | 7.7 (203 s after the previous call) |
| 16–21 | chat | in_stages | ok | 15514–16679 | 11407 (every call) | 68–74% | 7.8–16.1 |
| 22 | chat | body | ok | 12780 | **0** | 0% | 3.3 |
| 23–30 | chat | body | ok | 12944–13139 | 9692 (every call) | 74–75% | 3.3–12.6 |

**e661b2b1:**

| turn | purpose | moment/shape | outcome | input | cached | ratio | latency s |
|---|---|---|---|---|---|---|---|
| 1 | chat | chatting | ok | 13852 | 0 | 0% | 7.8 |
| 2 | chat | chatting | ok | 14047 | 0 | 0% | 7.5 |
| 2 | understanding | understanding | ok | 16733 | 0 | 0% | 20.2 |
| 3 | chat | chatting | ok | 14245 | 13817 | 97% | 12.9 |
| 3 | understanding | understanding | ok | 16816 | 0 | 0% | 19.6 |
| 3 | understanding | understanding | timeout | 0 | 0 | – | 83.1 |
| 4 | chat | chatting | ok | 14879 | 13921 | 94% | 8.7 |
| 4 | understanding | understanding | ok | 17499 | 16795 | 96% | 28.2 |
| 5 | chat | chatting, may_move | ok | 15889 | **0** | 0% | 6.9 |
| 5 | understanding | understanding | ok | 17655 | 16921 | 96% | 6.7 |
| 6 | chat | in_stages | ok | 13460 | **0** | 0% | 8.3 |
| 7–13 | chat | in_stages | ok | 14112–15934 | 10815 (every call) | 68–77% | 5.9–14.2 |
| 14 | chat | body | ok | 12102 | **0** | 0% | 3.7 |
| 15–18 | chat | body | ok | 12287–12482 | 9100 (every call) | 73–74% | 3.3–6.2 |

**219da449** (11-03, no traces):

| turn | input | cached | ratio | latency s |
|---|---|---|---|---|
| 1 | 14845 | 0 | 0% | 14.8 |
| 2 | 15147 | 0 | 0% | 20.0 |
| 3 | 15432 | 14813 | 96% | 23.4 |
| 4 | 15652 | 14911 | 95% | 16.4 |
| 5 | 15744 | 14989 | 95% | 19.6 |
| 6 | 16024 | 15055 | 94% | 29.2 |
| 7 | 9289 | 0 | 0% | 12.7 |
| 8 | 16522 | 15218 | 92% | 20.0 |
| 9 | 16701 | 15483 | 93% | 26.9 |
| 10 | 16941 | 15620 | 92% | 18.7 |
| 11 | 9988 | 7600 | 76% | 18.9 |
| 12 | 17314 | 15718 | 91% | 29.1 |
| 13 | 17402 | 16064 | 92% | 17.9 |
| 14 | 17533 | 16156 | 92% | 20.5 |
| 15 | 10552 | 7600 | 72% | 13.3 |
| 16 | 17784 | 16273 | 92% | 28.7 |

All rows are chat ok calls. Turns 7, 11 and 15 use a different, shorter prompt and share their own cache (7600 tokens), separate from the long turns.

**d4efc3a3** (11-03, no traces): turns 1–2 had 0 cached (14904, 15315 input). Turns 3–10 had 95–96% cached: turn 3 cached exactly 14904, which is turn 1's whole input. Latencies were 8.1–25.3 s. After turn 10, a chat call hit the 30.0 s deadline, and a memory_fold call then timed out at 82 s.

### Aggregates (ok chat calls in the 8 threads with ≥ 6 chat calls)

Average cache ratio by turn index:

| turn | n | mean | median |
|---|---|---|---|
| 1 | 8 | 24.7% | 0% |
| 2 | 8 | 11.9% | 0% |
| 3 | 8 | 84.3% | 96.2% |
| 4 | 8 | 95.7% | 95.7% |
| 5 | 8 | 83.6% | 95.1% |
| 6 | 8 | 71.3% | 94.6% |
| 7 | 6 | 60.6% | 85.8% |
| 8 | 6 | 90.8% | 93.5% |
| 9 | 6 | 90.4% | 93.5% |
| 10 | 5 | 51.8% | 71.8% |
| 11 | 4 | 81.5% | 83.5% |
| 12 | 4 | 63.6% | 81.7% |
| 13 | 4 | 41.2% | 36.2% |
| 14 | 4 | 42.2% | 38.3% |
| 15 | 4 | 55.8% | 73.0% |

First call after a moment/shape change, compared with the call before it (consecutive ok chat calls, both traced):

| pairs | n | ratio before | ratio after (mean / median) | after = 0 cached | cached ÷ previous call's input |
|---|---|---|---|---|---|
| schema key **changed** | 15 | 67.8% | **15.6% / 0%** | **12 of 15** | 15.7% |
| schema key **stayed** | 79 | 61.5% | 74.1% / 73.5% | 4 of 79 | 74.8% |

By transition:

| transition | n | before | after |
|---|---|---|---|
| chatting → chatting, may_move | 5 | 94% | 16% |
| in_stages → body | 3 | 71% | 0% |
| chatting, may_move → offer_open | 2 | 91% | 0% |
| offer_open → in_stages | 2 | 0% | 0% |
| chatting, may_move → in_stages | 2 | 40% | 36% |
| in_stages → chatting | 1 | 72% | 83% |

`understanding` vs the chat call it follows (28 pairs): the chat call's mean ratio is 73.3%, the understanding call's 86.7% (median 97.1%). 3 understanding calls had 0 cached. The median gap after the chat call is 16 s. Understanding input is a median 2,572 tokens larger than the chat call's, mostly because its schema is larger (21.5k characters of JSON schema against 7.7k for `ConversationReply`).

Cache ratio by gap since the previous ok chat call: under 1 min, mean 68% (n 90); 1–5 min, 72% (n 42); 5–10 min, 32% (n 3). No longer gaps occur.

### Conclusion: the data supports "a schema change resets the cache"

- **On the first call after a change of reply schema, the cache was 0 in 12 of 15 cases. When the schema stayed the same, it was 0 in 4 of 79.** On the next call under the new schema, the cache is back (for example 0% → 91% at chatting → may_move, 0% → 77% at the start of stages).
- The cleanest case is **chatting → chatting, may_move**. `_converse` builds the same system prompt (`compose_conversation`, unaffected by `allowed`) and the same history for both. Only the `response_format` schema differs, plus the trailing system note, which comes *after* the person's message and so after any shared prefix. The first may_move call still dropped to 0 cached in the threads shown (12baf58c turn 10, 452e18e6 turn 10, e661b2b1 turn 5).
- For the other transitions (into `offer_open`, `in_stages`, `body`), the system prompt also changes (`compose_framework` / `moments`), so those cases cannot separate the schema from the prompt.
- **The understanding calls point the same way.** They cache from the previous *understanding* call, never from the chat call just before them: 12baf58c turn 3 understanding cached 17,144, about the previous understanding's input, more than the chat call's whole input of 14,819. Likewise the next chat call caches from the previous chat call (14,320), not from the understanding call. Chat and understanding keep two separate caches, which fits the schema sitting at the start of the cached prefix.
- **This does not appear to cost wait time:** across ok chat calls, latency correlates −0.29 with uncached input.

Three related observations, not explained by this data:

- **Turn 2 is almost never cached (1 of 8), even though turn 1 had the same schema and system prompt 8–121 s earlier.** Turn 3's cached count always matches turn 1's input (14270 ≤ 14412; 14361 ≤ 14444; 13817 ≤ 13852; 14904 = 14904; 14813 ≤ 14845). So turn 1's prompt is in the cache by turn 3 but not by turn 2. The title instruction is added at the end of the system prompt, and the title field is in every reply schema, so neither explains a miss on the whole prefix. The cause was not determined.
- **During `in_stages` and `body`, the cached count is fixed for the whole run** (11407 or 10815 in stages, 9692 or 9100 in body) while input grows, so 3–6k tokens per call are re-read uncached every turn. During `chatting` the cached count grows with the conversation. Something placed after the first ~11.4k tokens changes on every stage or body turn. Its location was not determined.
- Of the 12 zero-cache calls after a change, the first in_stages call after `offer_open` has `offer_open` at 0% too: two schema changes in a row.

## 7. Endpoints

`scripts/llm_call_providers.py` (as written, which means the default 30 most recent chat calls, all inside the window): every call was served by `OpenAI`, with OpenRouter latency 2.9–14.2 s and generation time 4.1–15.7 s.

All 194 calls in the window that have a `generation_id` were then resolved through `GET /api/v1/generation`, which returns metadata only: 151 chat, 34 understanding, 9 memory_fold. Timeouts have no id. 194 of 194 resolved.

| purpose | provider / endpoint | share | our latency p50 / p90 | OR first token p50 / p90 | OR generation_time p50 / p90 | first token → end p50 | throughput p50 (native tokens/s) | ours − generation_time p50 / p90 |
|---|---|---|---|---|---|---|---|---|
| chat | OpenAI, `service_tier=default` | 100% (151) | 9.8 / 19.6 s | 6.0 / 12.6 s | 9.3 / 19.3 s | 1.6 s | 88 | **0.33 / 0.55 s** |
| understanding | OpenAI, `service_tier=default` | 100% (34) | 16.5 / 46.2 s | 6.1 / 10.0 s | 7.9 / 13.0 s | 2.2 s | 103 | **6.3 / 32.6 s** |
| memory_fold | OpenAI, `service_tier=default` | 100% (9) | 22.2 / 34.3 s | 9.5 / 16.6 s | 15.8 / 21.0 s | 4.3 s | 99 | **6.4 / 22.3 s** |

- Every call was `streamed: true` with `finish_reason: stop`, BYOK false, `api_type: completions`, and exactly one entry in `provider_responses`: one attempt with status 200, so no fallbacks were used.
- `session_id` and `data_region` are null on every generation.
- Throughput on `tokens_completion` (OpenRouter's normalised count) is lower: chat p50 39 tokens/s.
- For chat, the time before the first token is p50 75% of generation time. Summed over all 151 calls: 1,057 s before the first token, 555 s after it, and 64 s on our side (ours − generation_time). First-token latency correlates 0.70 with native reasoning tokens.
- Cost in the window, from OpenRouter: chat $0.18, understanding $0.04, memory_fold $0.01.

## 8. OpenRouter account and model

Snapshot taken 2026-11-05 at about 15:40 UTC, using the OpenRouter key in `backend/.env`. That key resolved prod's generation ids, so it is on the same account. Whether it is the same *key* prod uses is unknown, because prod's value is redacted.

- **Credits:** `GET /api/v1/credits` reports total_credits $80.00 and total_usage $56.31, so the **balance is $23.69**.
- **Key (`GET /api/v1/key`):** `limit` null, `limit_remaining` null, `budgets` empty, `is_free_tier` false, `expires_at` null. Usage is $1.24 this week and month, and $0.07 today. The rate limit field (`requests: -1`) is marked deprecated. `allowed_data_regions` is `["global"]`.
- **Model reasoning object (`openai/gpt-6-luna`):** `mandatory: false`, `default_enabled: true`, `supported_efforts: [max, xhigh, high, medium, low, none]`, `default_effort: medium`. Top provider: context 1,050,000, max completion 128,000, `is_moderated: true`.
- **`GET /api/v1/models/openai/gpt-6-luna/endpoints`**, all with model version `gpt-6-luna-20260922`. Latency and throughput are OpenRouter-wide over the last 30 minutes, not our requests:

| tag | provider | service tier | prompt / completion $ per M | cache read $/M | latency_last_30m p50 / p90 (ms) | throughput_last_30m p50 (tok/s) | uptime 30m / 1d | status |
|---|---|---|---|---|---|---|---|---|
| `openai` | OpenAI | (default) | 0.10 / 0.50 | 0.01 | 2347 / 6889 | 65 | 100 / 100 | 0 |
| `openai/fast` | OpenAI | priority | 0.20 / 1.00 | 0.02 | 1325 / 4334 | 109 | 100 / 100 | 0 |
| `openai/flex` | OpenAI | flex | 0.05 / 0.25 | 0.005 | 11622 / 19163 | 13 | 0 / 59.2 | −5 |
| `azure` | Azure | – | 0.10 / 0.50 | 0.01 | 3236 / 9876 | 61 | 100 / 100 | 0 |
| `azure/us` | Azure | – | 0.11 / 0.55 | 0.011 | 1856 / 7267 | 66 | 100 / 100 | 0 |
| `azure/eu` | Azure | – | 0.11 / 0.55 | 0.011 | 1236 / 4856 | 66 | 100 / 100 | 0 |
| `amazon-bedrock/global` | Amazon Bedrock | – | 0.10 / 0.50 | 0.01 | 1307 / 2745 | 121 | 100 / 99.4 | 0 |
| `amazon-bedrock/us-east-1` | Amazon Bedrock | – | 0.11 / 0.55 | 0.011 | 615 / 2070 | 95 | 100 / 100 | 0 |

Every endpoint also lists a price override above 272k prompt tokens, and every endpoint reports `supports_implicit_caching: false`, although caching is clearly happening on ours (section 6). With our `provider.only = ["openai"]`, the configured comment says the base slug never matches a tier endpoint. That fits the observed `service_tier=default` on all 194 calls, i.e. the `openai` row.

## 9. Hosting and non-model time

**What hosts the production backend: Vercel, as serverless functions.**

- `backend/.env.production` was created by the Vercel CLI (`VERCEL_ENV="production"`), and its variable names are the backend's (`DATABASE_URL`, `OPENROUTER_API_KEY`, `SUPABASE_*`, `CORS_ORIGINS`). Every secret in it is the placeholder `[sensitive]`, so the values are unreadable.
- The Vercel OIDC token's claims (decoded locally; the token is not reproduced) name team `muhammad-2203`, project `mani-ai-obuv`, plan **hobby**.
- `GET https://mani-ai-obuv.vercel.app/health` and `/health/ready` return 200 with `server: Vercel`. `/health/ready` is this app's route. These were three unauthenticated read-only requests.
- The journal (`duplicate-migration-versions-after-merge-2026-10-06.md`) records "Vercel only ships code", and `mani/routers/cron.py` is written for Vercel Cron.
- No `vercel.json` is in the repo. `PORT-STATUS.md` says it was removed and that "Hosting is not decided". Vercel detects the FastAPI `app` in `main.py` and runs it as a Vercel Function with Fluid compute. The `Dockerfile` (uvicorn, long-running) is not what serves production.

**Region.** `x-vercel-id: pdx1::iad1::…` on all three responses: the function runs in **iad1 (Washington, D.C., US East)**. `pdx1` is the edge nearest to where the probe ran.

**Supabase.** Project `heqenombgkihfeggrxqc` is in **AWS ca-central-1 (Montréal)**, going by the pooler hostname. `.env.hosted` connects through the **Supavisor session pooler, port 5432**: `aws-0-ca-central-1.pooler.supabase.com:5432`. `mani/db/pool.py` explains that the session pooler is required because asyncpg uses prepared statements. Prod's own `DATABASE_URL` is redacted. It is assumed to be the same, since the hosted project holds prod's calls and was seeded through `.env.hosted`. Every database round trip crosses from iad1 to ca-central-1.

**Cold starts.** Probe timings: first `/health` 6.16 s, then `/health/ready` 1.00 s and `/health` 0.98 s. Each Fluid instance opens its own asyncpg pool (min 2, max 10) through the pooler on start. No lifespan or warm-up configuration was found.

**Effect on `fire_and_forget`.** Vercel's documentation says:

- Fluid compute instances suspend ("ensures that idle pool clients are properly released before functions suspend").
- The supported way to keep working after the response, `waitUntil`, "is available in Node.js and in the Edge Runtime". For Python, Vercel points background work to Queues.
- Hobby max duration is 300 s, and a function that exceeds it is terminated.

`mani/background.py` uses bare `asyncio.create_task`, which Vercel does not track. These tasks run after `POST /v1/threads/{id}/messages` returns: `link_call`, `record_trace`, `update_summary` and `read_understanding`, plus the summary and memory-fold work. The data matches tasks that are suspended or cut off:

- Background calls spend p50 6.3 s, p90 22–33 s, between OpenRouter finishing and our row being written. Chat calls, which run inside the request, spend 0.33 s there.
- 15 of 49 understanding calls timed out, recording 61–335 s against a 60 s chunk wait. Both memory-fold retries never wrote a second row.
- At 11-05 14:40:33, two background calls from different threads wrote their timeout rows in the same second. They had started at 14:34:58 and 14:34:49, and the last request before them had arrived at 14:34:48. 14:40:33 is about 5.7 minutes after that request, near Hobby's 300 s limit, but this cannot be confirmed without logs.
- Understanding calls that overlapped the person's next request ran at p50 10.7 ms per token (n = 2), against 19.9 ms per token (n = 32) for the rest.

**Request duration of `POST /v1/threads/{id}/messages`.** Not measured: no hosting logs were available (see Gaps). The only figure is from inside the app: our chat call latency minus OpenRouter's generation time is p50 0.33 s, p90 0.55 s. The rest of the turn is not measured: auth/JWKS, the composed read, the safety screen, the transaction and the writes, each a round trip from iad1 to ca-central-1.

## 10. Request we send

The exact chat payload, built offline from `mani/llm/chain.py` and `client.py` with the installed `langchain-openai` 1.6.2 and `openai` 3.14.0. `messages` are omitted.

```json
{
  "model": "openai/gpt-6-luna",
  "stream": true,
  "max_completion_tokens": 10240,
  "extra_body": {
    "provider": {"only": ["openai"], "sort": "latency", "allow_fallbacks": true, "data_collection": "deny"},
    "reasoning": {"effort": "medium"},
    "usage": {"include": true}
  },
  "response_format": {"type": "json_schema", "json_schema": {"name": "ConversationReply", "strict": true, "schema": "<7,740 characters>"}}
}
```

- **Provider block:** `only: ["openai"]`, `sort: "latency"`, `allow_fallbacks: true`, `data_collection: "deny"` (from `Settings.routing()` defaults; the `voice` row's `routing` is `{}`). Prod's environment sets no `OPENROUTER_*` routing variables, judging by the variable names in the 2026-10-31 Vercel pull, so these defaults apply.
- **Reasoning:** `{"effort": "medium"}`, from the `voice` row. `Settings.reasoning_effort` (`high`) applies only when a row names no effort. No `temperature` is sent to this model.
- **Max tokens:** `max_completion_tokens = 2048 (DEFAULT_MAX_TOKENS, voice row sets none) + 8192 (REASONING_ALLOWANCE_TOKENS) = 10240`.
- **Streaming:** yes (`runnable.astream`). The chat call has a 15 s `stream_chunk_timeout` (`CHAT_FIRST_TOKEN_SECONDS`) for the first and every later chunk, a 60 s HTTP timeout (`LLM_TIMEOUT_SECONDS`), a 30 s whole-call `asyncio.wait_for` (`CHAT_DEADLINE_SECONDS`), and `max_retries=0` in the SDK. Our own retry covers a first-token cut, a transient provider error, or a schema failure (at most 2 attempts). No `stream_options` is sent; usage arrives through OpenRouter's `usage.include`.
- **Structured output:** `response_format` json_schema with `strict: true`. The `ConversationReply` schema is 7,740 characters, `ConversationUnderstanding` 21,497 characters. Moment shapes come from `schema.reply_for`, and the may-move variant from `schema.conversation_reply_for`.
- **`session_id`:** not sent; OpenRouter's generation records show `session_id: null`. **`prompt_cache_key`:** not sent. **`user`:** not sent.
- `understanding` calls send the same block with `ConversationUnderstanding`, and a 60 s chunk timeout instead of 15 s, with no whole-call deadline. `memory_fold` and `summarize` take their row's `reasoning_effort: high` and `maxTokens` (800 → 8992 and 500 → 8692 `max_completion_tokens`).

## 11. Gaps

- **Prod's environment values are unreadable.** Vercel redacts them, and only variable names are visible, from a pull dated 2026-10-31. That the prod `DATABASE_URL` points at `heqenombgkihfeggrxqc` rests on the journal, on the project receiving live calls up to 14:40 UTC today, and on there being no other hosted project. The value itself was not read. Whether the OpenRouter key in `backend/.env` is prod's key is unknown; it is on the same account.
- **No hosting logs.** The Vercel CLI is not installed and there is no login state (`~/.vercel` is absent). `fly`, `railway` and `render` CLIs are absent too. So there is no request duration for `POST /v1/threads/{id}/messages`, no count of failures that left no `llm_calls` row, no instance and cold-start count, and no confirmation of suspension. The function's region came from response headers. Its `maxDuration` is unknown; with no `vercel.json`, it is presumably the 300 s Hobby default.
- **Traces start at 2026-11-04 17:57 UTC.** 47 of 151 ok chat calls, all of 11-03 and early 11-04, have no moment. The schema key used in section 6 leaves out `slots` and `declined_row`, so a may_move turn with plain `ConversationReply` cannot be told apart.
- **What prod ran before the last seed.** Effort is not recorded per call, and `admin.prompt_versions` is empty. Which prompt text prod ran before the 2026-11-04 22:09 seed is unknown, so the slower 11-03 day cannot be attributed.
- **Background latencies include time while suspended.** `understanding` and `memory_fold` latencies and timeouts are inflated by time the process was not running. They are not a measure of the model.
- **Unexplained gaps in the data:**
  - 159 stored messages from people against 151 ok chat calls (8 unexplained).
  - 4 ok chat calls with no `message_id` (cause ambiguous; section 5).
  - The turn-2 cache miss and the fixed cached count during stages and body (section 6).
- OpenRouter's endpoint latency and throughput are OpenRouter-wide 30-minute figures from one moment, not ours.
- Sample sizes are small: 14 threads, 8 of them with at least 6 chat calls, and 15 schema-change pairs.
- Separately from latency: the git `origin` remote URL embeds a GitHub personal access token in plain text, printed by `git remote -v`. It is not reproduced here.
