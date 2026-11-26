// ABOUTME: Formats exercise times as m:ss: a listed duration as the API sends it (already rounded to the nearest
// ABOUTME: 30 seconds, R143), and an exact count of seconds for a running clock.

export function formatClock(totalSeconds: number): string {
  const seconds = Math.max(0, Math.round(totalSeconds));
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export function formatDuration(minutes: number): string {
  return formatClock(minutes * 60);
}
