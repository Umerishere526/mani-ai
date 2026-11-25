// ABOUTME: Formats exercise times as m:ss — a listed duration rounded to the nearest 30 seconds
// ABOUTME: (R143, never below 0:30), and an exact count of seconds for a running clock.

const ROUNDING_SECONDS = 30;

export function formatClock(totalSeconds: number): string {
  const seconds = Math.max(0, Math.round(totalSeconds));
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function roundDurationSeconds(minutes: number): number {
  const steps = Math.round((minutes * 60) / ROUNDING_SECONDS);
  return Math.max(ROUNDING_SECONDS, steps * ROUNDING_SECONDS);
}

export function formatDuration(minutes: number): string {
  return formatClock(roundDurationSeconds(minutes));
}
