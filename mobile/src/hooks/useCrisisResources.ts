// ABOUTME: The crisis lines to show, from GET /v1/crisis/resources, with the backend's US lines until or unless
// ABOUTME: the list can be read, so the safety screens never wait on the network to show a number.

import { getCrisisResources } from '@/lib/api/crisis';
import { helpLines, type HelpLines } from '@/lib/chat';
import { useLoad } from './useLoad';

export function useCrisisResources(): HelpLines {
  const { data } = useLoad('crisis-resources', getCrisisResources);
  return helpLines(data);
}
