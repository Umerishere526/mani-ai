// ABOUTME: Formats an exercise's length in minutes as m:ss, the way the mobile app shows it,
// ABOUTME: so "3.95" reads as 3:57 rather than as a decimal.

export function formatDuration(minutes: number): string {
  const seconds = Math.max(0, Math.round(minutes * 60));
  return `${Math.floor(seconds / 60)}:${(seconds % 60).toString().padStart(2, "0")}`;
}
