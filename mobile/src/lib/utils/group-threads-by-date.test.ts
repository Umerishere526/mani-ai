// ABOUTME: Tests groupThreadsByDate's bucketing/ordering logic against fake ThreadListItem
// ABOUTME: objects — no mocking, just real inputs pinned to a fixed "now".

import { getDateGroup, groupThreadsByDate } from './group-threads-by-date';
import type { ThreadListItem } from '@/types/chat';

const NOW = new Date('2026-09-14T12:00:00.000Z');

function makeThread(overrides: Partial<ThreadListItem>): ThreadListItem {
  return {
    id: 'thread-1',
    title: null,
    lastMessageAt: NOW.toISOString(),
    ...overrides,
  };
}

describe('getDateGroup', () => {
  it('classifies a timestamp from today as "today"', () => {
    expect(getDateGroup('2026-09-14T08:00:00.000Z', NOW)).toBe('today');
  });

  it('classifies a timestamp from yesterday as "yesterday"', () => {
    expect(getDateGroup('2026-09-13T23:00:00.000Z', NOW)).toBe('yesterday');
  });

  it('classifies anything older than yesterday as "older"', () => {
    expect(getDateGroup('2026-09-01T00:00:00.000Z', NOW)).toBe('older');
  });
});

describe('groupThreadsByDate', () => {
  it('returns an empty list for no threads', () => {
    expect(groupThreadsByDate([], NOW)).toEqual([]);
  });

  it('interleaves a header before each non-empty group, in today/yesterday/older order', () => {
    const today = makeThread({ id: 'today-1', lastMessageAt: '2026-09-14T09:00:00.000Z' });
    const older = makeThread({ id: 'older-1', lastMessageAt: '2026-09-01T09:00:00.000Z' });

    const rows = groupThreadsByDate([older, today], NOW);

    expect(rows).toEqual([
      { type: 'header', group: 'today' },
      { type: 'thread', thread: today },
      { type: 'header', group: 'older' },
      { type: 'thread', thread: older },
    ]);
  });

  it('omits a group header entirely when that group has no threads', () => {
    const today = makeThread({ id: 'today-1', lastMessageAt: '2026-09-14T09:00:00.000Z' });

    const rows = groupThreadsByDate([today], NOW);

    expect(rows.some((row) => row.type === 'header' && row.group === 'yesterday')).toBe(false);
    expect(rows.some((row) => row.type === 'header' && row.group === 'older')).toBe(false);
  });
});
