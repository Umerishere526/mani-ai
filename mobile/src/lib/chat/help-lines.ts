// ABOUTME: Picks the crisis lines the app shows from GET /v1/crisis/resources: a line to call or text, emergency
// ABOUTME: services, and the helpline directory, with the backend's own US lines when the list cannot be read.

import type { CrisisResource } from '@/types/chat-api';

export interface HelpLines {
  support: CrisisResource | null;
  emergency: CrisisResource | null;
  directory: CrisisResource | null;
}

// The backend's reference lines (RESOURCES in backend/mani/chat/crisis.py), so the screen never shows no number.
export const FALLBACK_RESOURCES: CrisisResource[] = [
  { country: 'US', kind: 'emergency', name: 'Emergency services', phone: '911' },
  { country: 'US', kind: 'support', name: '988 Suicide & Crisis Lifeline', phone: '988', sms: '988' },
  { country: 'US', kind: 'directory', name: 'Find a helpline in your country', url: 'https://findahelpline.com' },
];

function first(resources: CrisisResource[], kind: CrisisResource['kind'], field: 'phone' | 'url') {
  return resources.find((r) => r.kind === kind && r[field]) ?? null;
}

export function helpLines(resources: CrisisResource[] | null | undefined): HelpLines {
  const list = resources?.length ? resources : FALLBACK_RESOURCES;
  return {
    support: first(list, 'support', 'phone'),
    emergency: first(list, 'emergency', 'phone'),
    directory: first(list, 'directory', 'url'),
  };
}

/** The directory's address as people say it: findahelpline.com. */
export function siteName(url: string): string {
  return url.replace(/^https?:\/\//, '').replace(/\/$/, '');
}
