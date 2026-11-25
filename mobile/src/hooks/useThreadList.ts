// ABOUTME: The person's conversations for the drawer's history, read from the backend each time the drawer opens.

import { listThreads } from '@/lib/api/threads';
import { threadFromWire } from '@/lib/chat';
import type { ThreadListItem } from '@/types/chat';
import { useLoad } from './useLoad';

export function useThreadList(visible: boolean): ThreadListItem[] {
  const { data } = useLoad(visible ? 'threads' : null, listThreads);
  return data?.threads?.map(threadFromWire) ?? [];
}
