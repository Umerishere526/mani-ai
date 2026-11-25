// ABOUTME: The account-wide chat pause as the backend reports it (a turn, the profile, or a 423 refusal), how long
// ABOUTME: it runs, what leads the crisis screen, and when a reply opens that screen by itself.

import { ApiError } from '@/lib/api/api-error';
import type { TurnOut } from '@/types/chat-api';

export interface ChatPause {
  from: string;
  until: string;
  /** What the pause is for, when the backend says: an overdose or whose danger it is. */
  reason: string | null;
}

interface PauseStamps {
  paused_from?: string | null;
  paused_until?: string | null;
  paused_for?: string | null;
  chat_paused_from?: string | null;
  chat_paused_until?: string | null;
  chat_paused_for?: string | null;
}

/** The pause a turn or a refusal's details (`paused_*`), or a profile or opening (`chat_paused_*`) carries. */
export function pauseIn(source: PauseStamps | null | undefined): ChatPause | null {
  const from = source?.paused_from ?? source?.chat_paused_from;
  const until = source?.paused_until ?? source?.chat_paused_until;
  const reason = source?.paused_for ?? source?.chat_paused_for ?? null;
  return from && until ? { from, until, reason } : null;
}

/** The pause behind a refused send: the backend answers 423 `chat_paused` with its times in `details`. */
export function pauseFromError(error: unknown): ChatPause | null {
  if (!(error instanceof ApiError) || error.category !== 'chat_paused') return null;
  return pauseIn(error.details as PauseStamps | null);
}

/** Which help line leads the crisis screen: "Call 911 now." after an overdose, where 988 is no substitute (R90);
 * emergency services for danger to someone else, from someone or in the body, whose help is 911; otherwise 988.
 * PROVISIONAL: clinician sign-off required before deploy. */
export type HelpLead = 'callNow' | 'emergency' | 'support';

const EMERGENCY_KINDS = ['someone_else', 'from_someone', 'body'];

export function helpLead(pause: ChatPause | null): HelpLead {
  if (pause?.reason === 'overdose') return 'callNow';
  return EMERGENCY_KINDS.includes(pause?.reason ?? '') ? 'emergency' : 'support';
}

export function isPauseActive(pause: ChatPause | null, now: Date): pause is ChatPause {
  return pause !== null && Date.parse(pause.until) > now.getTime();
}

export type PauseUnit = 'hour' | 'minute' | 'second';

/** How long the pause runs, in the largest whole unit that holds it: 15 minutes, 24 hours. */
export function pauseLength(pause: ChatPause): { count: number; unit: PauseUnit } {
  const seconds = Math.max(1, Math.round((Date.parse(pause.until) - Date.parse(pause.from)) / 1000));
  if (seconds % 3600 === 0) return { count: seconds / 3600, unit: 'hour' };
  if (seconds % 60 === 0) return { count: seconds / 60, unit: 'minute' };
  return { count: seconds, unit: 'second' };
}

/** A reply opens the crisis screen when it starts a pause, or when it is the first to find a crisis; later replies
 * in the same crisis leave it closed, so it does not cover every message. */
export function opensCrisisScreen(turn: TurnOut, crisisBefore: boolean): boolean {
  return pauseIn(turn) !== null || (Boolean(turn.crisis_detected) && !crisisBefore);
}
