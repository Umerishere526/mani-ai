// ABOUTME: Holds the signed-in session: restores it from storage, renews the access token
// ABOUTME: before it expires (one refresh at a time), and notifies subscribers on every change.

import { AuthError, type AuthService, type Session } from './session';

export const STORAGE_KEY = '@mani/session';
// Renew this long before expiry, so a token never expires mid-request.
const REFRESH_MARGIN_SECONDS = 60;

export interface KeyValueStorage {
  getItem(key: string): Promise<string | null>;
  setItem(key: string, value: string): Promise<void>;
  removeItem(key: string): Promise<void>;
}

export type SessionState =
  | { status: 'loading'; session: null }
  | { status: 'signedOut'; session: null }
  | { status: 'signedIn'; session: Session };

export type SignUpResult = 'signedIn' | 'confirmEmail';

export function createSessionManager({
  auth,
  storage,
  now = () => Date.now(),
}: {
  auth: AuthService;
  storage: KeyValueStorage;
  now?: () => number;
}) {
  let state: SessionState = { status: 'loading', session: null };
  let loading: Promise<void> | null = null;
  let refreshing: Promise<string | null> | null = null;
  const listeners = new Set<() => void>();

  function setState(next: SessionState) {
    state = next;
    listeners.forEach((listener) => listener());
  }

  async function keep(session: Session) {
    await storage.setItem(STORAGE_KEY, JSON.stringify(session));
    setState({ status: 'signedIn', session });
  }

  async function forget() {
    await storage.removeItem(STORAGE_KEY);
    setState({ status: 'signedOut', session: null });
  }

  async function refresh(): Promise<string | null> {
    const current = state.session;
    if (!current) return null;
    try {
      const renewed = await auth.refresh(current.refreshToken);
      await keep(renewed);
      return renewed.accessToken;
    } catch (error) {
      // Offline is not a verdict on the session: keep it and let the next call try again.
      if (error instanceof AuthError && error.code === 'network') return null;
      await forget();
      return null;
    }
  }

  function refreshAccessToken(): Promise<string | null> {
    refreshing ??= refresh().finally(() => {
      refreshing = null;
    });
    return refreshing;
  }

  function parseStored(stored: string | null): Session | null {
    if (!stored) return null;
    try {
      return JSON.parse(stored) as Session;
    } catch {
      return null;
    }
  }

  return {
    getState: () => state,
    subscribe(listener: () => void) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    load(): Promise<void> {
      loading ??= (async () => {
        const stored = await storage.getItem(STORAGE_KEY).catch(() => null);
        const session = parseStored(stored);
        setState(session ? { status: 'signedIn', session } : { status: 'signedOut', session: null });
      })();
      return loading;
    },
    async signIn(email: string, password: string) {
      await keep(await auth.signIn(email, password));
    },
    async signUp(email: string, password: string): Promise<SignUpResult> {
      const session = await auth.signUp(email, password);
      if (!session) return 'confirmEmail';
      await keep(session);
      return 'signedIn';
    },
    async signOut() {
      const token = state.session?.accessToken;
      // Revoking the refresh token is best effort; this device forgets the session regardless.
      if (token) await auth.signOut(token).catch(() => undefined);
      await forget();
    },
    refreshAccessToken,
    async getAccessToken(): Promise<string | null> {
      const session = state.session;
      if (!session) return null;
      if (session.expiresAt - now() / 1000 > REFRESH_MARGIN_SECONDS) return session.accessToken;
      return (await refreshAccessToken()) ?? state.session?.accessToken ?? null;
    },
  };
}

export type SessionManager = ReturnType<typeof createSessionManager>;
