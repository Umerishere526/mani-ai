// ABOUTME: Formats a timestamp as a short relative string ("5m ago", "2d ago") or a date
// ABOUTME: once it's more than a week old. Ported from mani-app's admin/chats/page.tsx.

interface RelativeTimeStrings {
  justNow: string;
  minutesAgoSuffix: string;
  hoursAgoSuffix: string;
  daysAgoSuffix: string;
}

export function formatRelativeTime(dateString: string, strings: RelativeTimeStrings): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return strings.justNow;
  if (diffMins < 60) return `${diffMins}${strings.minutesAgoSuffix}`;
  if (diffHours < 24) return `${diffHours}${strings.hoursAgoSuffix}`;
  if (diffDays < 7) return `${diffDays}${strings.daysAgoSuffix}`;
  return date.toLocaleDateString();
}
