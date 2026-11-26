// ABOUTME: Runs one async action at a time for a button or form, exposing whether it is
// ABOUTME: running and the error of its last attempt, so screens don't each re-implement it.

import { useState } from 'react';

export function useAsyncAction<Args extends unknown[]>(action: (...args: Args) => Promise<unknown>) {
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const run = async (...args: Args) => {
    if (isRunning) return;
    setIsRunning(true);
    setError(null);
    try {
      await action(...args);
    } catch (caught) {
      setError(caught);
    } finally {
      setIsRunning(false);
    }
  };

  return { run, isRunning, error };
}
