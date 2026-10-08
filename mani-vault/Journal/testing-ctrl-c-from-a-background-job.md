# Testing Ctrl C on a script started as a background job

2026-10-07, while checking that `eval_replies.py --baseline` cleans up when interrupted (spec 0002, AC-9).

- `python script.py & kill -INT $!` from a non-interactive shell proves nothing. With job control off, the shell
  starts background jobs with SIGINT ignored, Python keeps the inherited `SIG_IGN`, and the run simply finishes.
  The first check "passed" by writing the file it was supposed to refuse to write.
- Fix for the check: call `signal.signal(signal.SIGINT, signal.default_int_handler)` at the top of the throwaway
  driver, then send `kill -INT`. `asyncio.run` cancels the main task, `finally` blocks still run their awaits,
  and `KeyboardInterrupt` reaches `__main__`.
- Run the real entry point (`runpy.run_path(..., run_name="__main__")`), not `asyncio.run(main())` from the
  driver, or you skip the `__main__` handling you meant to check (exit code 1, no traceback).

Dry running the baseline on a fake model: replace `mani.llm.chain.build`, not `client.complete`. Faking
`complete` (as `tests/integration/test_turn.py` does) writes no `admin.llm_calls` rows, so the cost capture is
never exercised. Make `chain._model` raise, so any path that would reach a real provider fails loudly.

Related: [[measure-before-tuning-prompts]].
