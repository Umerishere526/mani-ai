// ABOUTME: Buckets chat threads into Today/Yesterday/Older groups by lastMessageAt,
// ABOUTME: interleaved with header markers so a FlatList can render one flat list.

import type { ThreadListItem } from '@/types/chat';

export type DateGroup = 'today' | 'yesterday' | 'older';

export type GroupedThreadRow =
  | { type: 'header'; group: DateGroup }
  | { type: 'thread'; thread: ThreadListItem };

export function getDateGroup(dateString: string, now: Date = new Date()): DateGroup {
  const date = new Date(dateString);
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);

  if (date >= today) return 'today';
  if (date >= yesterday) return 'yesterday';
  return 'older';
}

export function groupThreadsByDate(threads: ThreadListItem[], now: Date = new Date()): GroupedThreadRow[] {
  const groups: Record<DateGroup, ThreadListItem[]> = { today: [], yesterday: [], older: [] };

  for (const thread of threads) {
    groups[getDateGroup(thread.lastMessageAt, now)].push(thread);
  }

  const rows: GroupedThreadRow[] = [];
  for (const group of ['today', 'yesterday', 'older'] as const) {
    if (groups[group].length === 0) continue;
    rows.push({ type: 'header', group });
    for (const thread of groups[group]) {
      rows.push({ type: 'thread', thread });
    }
  }

  return rows;
}
