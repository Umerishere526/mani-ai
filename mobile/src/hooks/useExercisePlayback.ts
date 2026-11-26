// ABOUTME: Playback clock for an exercise — play/pause, progress, remaining time and completion.
// ABOUTME: Driven by a timer, since no audio module is installed to report real playback.

import { useEffect, useState } from 'react';

const TICK_MS = 250;

export function useExercisePlayback(durationMs: number) {
  const [isRunning, setIsRunning] = useState(false);
  const [hasStarted, setHasStarted] = useState(false);
  const [elapsedMs, setElapsedMs] = useState(0);
  const isComplete = hasStarted && elapsedMs >= durationMs;
  const isPlaying = isRunning && !isComplete;

  useEffect(() => {
    if (!isPlaying) return;
    const interval = setInterval(() => {
      setElapsedMs((prev) => Math.min(prev + TICK_MS, durationMs));
    }, TICK_MS);
    return () => clearInterval(interval);
  }, [isPlaying, durationMs]);

  const togglePlayback = () => {
    setHasStarted(true);
    setIsRunning((prev) => !prev);
  };

  return {
    isPlaying,
    hasStarted,
    isComplete,
    progress: durationMs > 0 ? elapsedMs / durationMs : 1,
    remainingSeconds: (durationMs - elapsedMs) / 1000,
    togglePlayback,
  };
}
