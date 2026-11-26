// ABOUTME: Tests the session lifecycle against a scripted fake AuthService and an in-memory
// ABOUTME: storage — restore, renewal before expiry, sign-out on a dead session, offline.

import { AuthError, type AuthService, type Session } from './session';
import { createSessionManager, STORAGE_KEY, type KeyValueStorage } from './session-manager';

const NOW_MS = 1_800_000_000_000;
const NOW_S = NOW_MS / 1000;

function session(token: string, expiresAt = NOW_S + 3600): Session {
  return { accessToken: token, refreshToken: `refresh-${token}`, expiresAt, user: { id: 'u1', email: 'a@b.co' } };
}

class MemoryStorage implements KeyValueStorage {
  items = new Map<string, string>();
  async getItem(key: string) {
    return this.items.get(key) ?? null;
  }
  async setItem(key: string, value: string) {
    this.items.set(key, value);
  }
  async removeItem(key: string) {
    this.items.delete(key);
  }
}

class FakeAuth implements AuthService {
  refreshCalls = 0;
  refreshResult: () => Promise<Session> = async () => session('renewed');
  signUpResult: Session | null = null;
  async signUp() {
    return this.signUpResult;
  }
  async signIn() {
    return session('signed-in');
  }
  async refresh() {
    this.refreshCalls += 1;
    return this.refreshResult();
  }
  async signOut() {
    throw new AuthError('network');
  }
}

function setup(stored?: Session | string) {
  const auth = new FakeAuth();
  const storage = new MemoryStorage();
  if (stored) storage.items.set(STORAGE_KEY, typeof stored === 'string' ? stored : JSON.stringify(stored));
  const manager = createSessionManager({ auth, storage, now: () => NOW_MS });
  return { auth, storage, manager };
}

it('restores a stored session, and treats an unreadable one as signed out', async () => {
  const restored = setup(session('kept'));
  await restored.manager.load();
  expect(restored.manager.getState()).toMatchObject({ status: 'signedIn', session: { accessToken: 'kept' } });

  const corrupt = setup('{not json');
  await corrupt.manager.load();
  expect(corrupt.manager.getState().status).toBe('signedOut');
});

it('renews a token about to expire once for concurrent callers, and stores the renewal', async () => {
  const { auth, storage, manager } = setup(session('old', NOW_S + 30));
  await manager.load();

  const tokens = await Promise.all([manager.getAccessToken(), manager.getAccessToken()]);

  expect(tokens).toEqual(['renewed', 'renewed']);
  expect(auth.refreshCalls).toBe(1);
  expect(JSON.parse(storage.items.get(STORAGE_KEY) ?? '{}').accessToken).toBe('renewed');
});

it('signs out when the auth service rejects the refresh token', async () => {
  const { auth, storage, manager } = setup(session('old', NOW_S - 10));
  auth.refreshResult = async () => {
    throw new AuthError('session_expired');
  };
  await manager.load();

  expect(await manager.refreshAccessToken()).toBeNull();
  expect(manager.getState().status).toBe('signedOut');
  expect(storage.items.has(STORAGE_KEY)).toBe(false);
});

it('keeps the session when a refresh fails because the device is offline', async () => {
  const { auth, manager } = setup(session('old', NOW_S + 30));
  auth.refreshResult = async () => {
    throw new AuthError('network');
  };
  await manager.load();

  expect(await manager.getAccessToken()).toBe('old');
  expect(manager.getState().status).toBe('signedIn');
});

it('stays signed out after a sign-up that must confirm its email first', async () => {
  const { manager } = setup();
  await manager.load();

  expect(await manager.signUp('a@b.co', 'password1')).toBe('confirmEmail');
  expect(manager.getState().status).toBe('signedOut');
});

it('forgets the session on sign-out even when revoking it fails', async () => {
  const { storage, manager } = setup(session('kept'));
  await manager.load();

  await manager.signOut();

  expect(manager.getState().status).toBe('signedOut');
  expect(storage.items.has(STORAGE_KEY)).toBe(false);
});
