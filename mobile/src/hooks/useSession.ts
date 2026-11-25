// ABOUTME: Subscribes a component to the signed-in session, re-rendering on sign-in,
// ABOUTME: sign-out and token renewal.

import { useSyncExternalStore } from 'react';
import { sessionManager } from '@/lib/api';

export function useSession() {
  return useSyncExternalStore(sessionManager.subscribe, sessionManager.getState);
}
