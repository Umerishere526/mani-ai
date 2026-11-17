2026-11-16

# One failed model call lost a whole scenario run

The first live pass for spec 0008 (`scenario_check.py --scenario moves --style directive --save …`) ran about twelve
minutes and about 228 model calls, then saved nothing.

What happened, from the output: two `stream_chunk_timeout fired` lines, then `ConnectionResetError: [Errno 54]` on
several streaming calls at once, so the network or the provider dropped the connections; which of the two is not
known. One conversation raised `ServiceError: provider call failed`. `main` awaited the conversations with a plain
`asyncio.gather`, so that first error left `main`, the `finally` closed the pool while three other conversations were
mid-turn (they then failed with "database pool is not open"), and the code that prints and saves was never reached.
The two conversations in flight also left their users and `admin.llm_calls` rows behind, because their clean-up needs
the pool.

The fix is in the runner, not around it: `gather(..., return_exceptions=True)` and `scenario_check.settled`, which
keeps every conversation that ran to its end and names each stopped one. A stopped conversation is left out whole,
because half of one would be counted as if its later lines had been reached. It is run again alone with `--scenario`
and `--style`, and `conversation_counts.py` takes that file beside the others.

- A long paid run must survive one failed call. Check that before starting one, with the model pointed at a dead
  address: it costs nothing.
- The token use of the calls that were left behind gave the only cost figure: per call about 15,200 input tokens
  (8,800 cached) and 950 output.
- Related: [[exclusive-moments-and-forced-questions-2026-11-16]], `docs/specs/0008-one-conversation-many-moments/`.
