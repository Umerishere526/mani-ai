# 504s follow what the reply writes before its text

2026-11-03. Lolly's four Directive chats ([[../../docs/client/messages/2026-11-03-four-directive-chats]]): two ended in
"504 llm_timeout", on her 11th and 7th messages, never early. Not measured: the hosted and local databases were not
reachable from this session, so `scripts/latency_report.py` has not been run on her threads.

The reasoning, from the code:

- A chat turn's reply is `ConversationReply`. Since approach A (muhammad, 2026-10-29), `text` is its 14th field. Before
  it the model writes `reading` (14 fields, "re-read from the whole conversation", so it grows every turn), `picture`
  (16 fields), and eleven more (`heart`, `need`, `needs_info`, `info_needed`, `shape`, `window`, `insight`,
  `insight_from`, `link`, `move`, `plan`). Output tokens set a streamed call's time far more than input does.
- The system prompt before the transcript is about 20k tokens (`voice.md` about 5.7k, `conversation.md` about 8.8k,
  the schema with its descriptions about 5.9k; characters / 4). Mostly cached, so it is not the first suspect.
- `client.complete` wraps each chat attempt in `asyncio.wait_for(..., chat_deadline_seconds=30)`. A stream that is
  still writing at 30 s raises `TimeoutError`, which is not retried, so the turn fails as `LLM_TIMEOUT`. The 15 s
  silence cut retries; the deadline does not.

So the more the reading holds, the longer every later turn takes, until one passes 30 s. That matches 504s that only
come late. To confirm: `latency_report.py --since 2026-11-03` and look at output tokens against latency, by turn number.

The failed message is also the one missing from both transcripts: the chat tester dropped a message whose send failed
(fixed the same day, it goes back into the composer). That is probably email 2's "it deleted my answer" too.

Email 2's early framework is a separate cause: `frustrated` sets `converse.TOWARD`, and the note then says "move toward
the framework" while `MOVE_NOT` forbids the offer, so the text named the framework with nothing behind it.

Decided the same day (muhammad): split the turn. The reply asks only for what the turn calls for and the text; the
reading and the picture are a second call after the reply is sent, merged under the thread's turn lock. Two things
found while building it: `threads.get` does not select `understanding` (hence `threads.understanding_of`), and the
scripted model in `tests/integration/test_turn.py` has to answer a reading with the reply that went out, not the
latest one served, or a late reading looks lost. See [[a-session-not-a-set-of-rules-2026-10-29]] for approach A, which
this keeps: the picture still comes before the text, one message behind at worst.
