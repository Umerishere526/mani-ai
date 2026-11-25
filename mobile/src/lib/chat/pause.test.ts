// ABOUTME: Tests reading the pause from each place the backend reports it, its length, and when a reply opens the
// ABOUTME: crisis screen, with real TurnOut, profile and 423 error shapes.

import { ApiError } from '@/lib/api/api-error';
import type { TurnOut } from '@/types/chat-api';
import { emergencyLeads, isPauseActive, opensCrisisScreen, pauseFromError, pauseIn, pauseLength } from './pause';

const FROM = '2026-11-25T20:02:35Z';
const UNTIL = '2026-11-25T20:17:35Z';

function turn(overrides: Partial<TurnOut>): TurnOut {
  return { content: 'reply', crisis_detected: false, ...overrides };
}

describe('the pause', () => {
  it('is read from a turn, a profile and a 423 refusal alike, with what it is for', () => {
    const pause = { from: FROM, until: UNTIL, reason: 'overdose' };
    expect(pauseIn(turn({ paused_from: FROM, paused_until: UNTIL, paused_for: 'overdose' }))).toEqual(pause);
    expect(pauseIn({ chat_paused_from: FROM, chat_paused_until: UNTIL, chat_paused_for: 'overdose' })).toEqual(pause);
    const refusal = new ApiError({
      category: 'chat_paused',
      status: 423,
      details: { paused_from: FROM, paused_until: UNTIL, paused_for: 'overdose' },
    });
    expect(pauseFromError(refusal)).toEqual(pause);
  });

  it('is absent from an open profile and from other failures', () => {
    expect(pauseIn({ chat_paused_from: null, chat_paused_until: null })).toBeNull();
    expect(pauseFromError(new ApiError({ category: 'llm_unavailable', status: 503, details: { paused_until: UNTIL } }))).toBeNull();
    expect(pauseFromError(new ApiError({ category: 'network', retryable: true }))).toBeNull();
  });

  it('puts emergency services first only for an overdose', () => {
    expect(emergencyLeads({ from: FROM, until: UNTIL, reason: 'overdose' })).toBe(true);
    expect(emergencyLeads({ from: FROM, until: UNTIL, reason: 'self' })).toBe(false);
    expect(emergencyLeads(pauseIn({ chat_paused_from: FROM, chat_paused_until: UNTIL }))).toBe(false);
    expect(emergencyLeads(null)).toBe(false);
  });

  it('is active only until its end', () => {
    const pause = { from: FROM, until: UNTIL, reason: null };
    expect(isPauseActive(pause, new Date('2026-11-25T20:10:00Z'))).toBe(true);
    expect(isPauseActive(pause, new Date(UNTIL))).toBe(false);
  });

  it('states its length in the largest whole unit', () => {
    const lasting = (until: string) => pauseLength({ from: FROM, until, reason: null });
    expect(lasting(UNTIL)).toEqual({ count: 15, unit: 'minute' });
    expect(lasting('2026-11-26T20:02:35Z')).toEqual({ count: 24, unit: 'hour' });
    expect(lasting('2026-11-25T20:03:05Z')).toEqual({ count: 30, unit: 'second' });
  });
});

describe('opensCrisisScreen', () => {
  it('opens on the reply that starts a pause, even mid-crisis', () => {
    expect(opensCrisisScreen(turn({ crisis_detected: true, paused_from: FROM, paused_until: UNTIL }), true)).toBe(true);
  });

  it('opens on the first reply that finds a crisis, and not on the ones after it', () => {
    expect(opensCrisisScreen(turn({ crisis_detected: true }), false)).toBe(true);
    expect(opensCrisisScreen(turn({ crisis_detected: true }), true)).toBe(false);
    expect(opensCrisisScreen(turn({ crisis_detected: false }), false)).toBe(false);
  });
});
