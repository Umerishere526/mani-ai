// ABOUTME: The app's backend client and session, wired to EXPO_PUBLIC_* config and on-device
// ABOUTME: storage. Feature modules (profile, account, …) send their requests through `api`.

import AsyncStorage from '@react-native-async-storage/async-storage';
import { createGoTrueAuth } from '@/lib/auth/gotrue';
import { createSessionManager } from '@/lib/auth/session-manager';
import { createApiClient } from './api-client';

export { ApiError, type ApiErrorCategory } from './api-error';

export const sessionManager = createSessionManager({
  auth: createGoTrueAuth({
    url: process.env.EXPO_PUBLIC_SUPABASE_URL,
    publishableKey: process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY,
  }),
  storage: AsyncStorage,
});

export const api = createApiClient({
  baseUrl: process.env.EXPO_PUBLIC_API_URL,
  getAccessToken: () => sessionManager.getAccessToken(),
  refreshAccessToken: () => sessionManager.refreshAccessToken(),
});
