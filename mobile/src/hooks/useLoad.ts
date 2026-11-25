// ABOUTME: Loads one value from the backend whenever its key changes, with a failed flag and a retry; a null key
// ABOUTME: loads nothing. A result that arrives after the key changed is dropped.

import { useEffect, useEffectEvent, useState } from 'react';

export interface Loaded<T> {
  data: T | null;
  failed: boolean;
  retry: () => void;
}

export function useLoad<T>(key: string | null, load: () => Promise<T>, onLoaded?: (data: T) => void): Loaded<T> {
  const [data, setData] = useState<T | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const fetchValue = useEffectEvent(load);
  const settle = useEffectEvent((value: T) => {
    setData(value);
    onLoaded?.(value);
  });

  useEffect(() => {
    if (key === null) return;
    let current = true;
    fetchValue().then(
      (value) => current && settle(value),
      () => current && setFailed(true),
    );
    return () => {
      current = false;
    };
  }, [key, attempt]);

  const retry = () => {
    setFailed(false);
    setAttempt((n) => n + 1);
  };

  return { data, failed, retry };
}
