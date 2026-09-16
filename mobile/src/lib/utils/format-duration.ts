// ABOUTME: Formats a decimal-minutes duration (e.g. 2.64) as mm:ss (e.g. "2:38").

export function formatDuration(minutes: number): string {
  const mins = Math.floor(minutes);
  const secs = Math.round((minutes - mins) * 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}
