// ABOUTME: The crisis resources route: the helplines the safety screens show. Open to a paused person too.

import type { CrisisResource } from '@/types/chat-api';
import { api } from './index';

export function getCrisisResources(): Promise<CrisisResource[]> {
  return api.request<CrisisResource[]>('GET', '/v1/crisis/resources');
}
