// ABOUTME: Supabase Auth (GoTrue) over its REST endpoints with the publishable key: email and
// ABOUTME: password sign-up and sign-in, token refresh and sign-out, errors mapped to AuthError.

import { FetchTimeoutError, fetchWithTimeout } from '@/lib/utils/fetch-with-timeout';
import { AuthError, type AuthErrorCode, type AuthService, type Session } from './session';

const AUTH_TIMEOUT_MS = 15_000;

interface GoTrueSession {
  access_token?: string;
  refresh_token?: string;
  expires_in?: number;
  expires_at?: number;
  user?: { id?: string; email?: string | null };
}

interface GoTrueError {
  error_code?: string;
  error?: string;
  msg?: string;
  error_description?: string;
}

const KNOWN_CODES: AuthErrorCode[] = [
  'invalid_credentials',
  'email_not_confirmed',
  'user_already_exists',
  'weak_password',
];

function codeFor(status: number, body: GoTrueError | null): AuthErrorCode {
  const code = body?.error_code ?? body?.error;
  if (KNOWN_CODES.includes(code as AuthErrorCode)) return code as AuthErrorCode;
  if (code === 'refresh_token_not_found' || code === 'refresh_token_already_used') return 'session_expired';
  if (code === 'invalid_grant') return 'invalid_credentials';
  if (status === 429) return 'rate_limited';
  return 'unknown';
}

function toSession(body: GoTrueSession, nowMs: number): Session | null {
  if (!body.access_token || !body.refresh_token || !body.user?.id) return null;
  return {
    accessToken: body.access_token,
    refreshToken: body.refresh_token,
    expiresAt: body.expires_at ?? Math.floor(nowMs / 1000) + (body.expires_in ?? 0),
    user: { id: body.user.id, email: body.user.email ?? null },
  };
}

export function createGoTrueAuth({
  url,
  publishableKey,
  fetchImpl = fetch,
}: {
  url: string | undefined;
  publishableKey: string | undefined;
  fetchImpl?: typeof fetch;
}): AuthService {
  async function call(path: string, body: unknown, accessToken?: string): Promise<GoTrueSession> {
    if (!url || !publishableKey) throw new AuthError('config');
    const headers: Record<string, string> = { apikey: publishableKey, 'Content-Type': 'application/json' };
    if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
    let response: Response;
    try {
      response = await fetchWithTimeout(
        fetchImpl,
        `${url.replace(/\/+$/, '')}/auth/v1${path}`,
        { method: 'POST', headers, body: JSON.stringify(body) },
        AUTH_TIMEOUT_MS,
      );
    } catch (error) {
      throw new AuthError('network', error instanceof FetchTimeoutError ? error.message : undefined);
    }
    const json = await response.json().catch(() => null);
    if (!response.ok) {
      const error = json as GoTrueError | null;
      throw new AuthError(codeFor(response.status, error), error?.msg ?? error?.error_description);
    }
    return (json ?? {}) as GoTrueSession;
  }

  async function sessionFrom(path: string, body: unknown): Promise<Session> {
    const session = toSession(await call(path, body), Date.now());
    if (!session) throw new AuthError('unknown', 'GoTrue returned no session');
    return session;
  }

  return {
    async signUp(email, password) {
      return toSession(await call('/signup', { email, password }), Date.now());
    },
    signIn(email, password) {
      return sessionFrom('/token?grant_type=password', { email, password });
    },
    refresh(refreshToken) {
      return sessionFrom('/token?grant_type=refresh_token', { refresh_token: refreshToken });
    },
    async signOut(accessToken) {
      await call('/logout', {}, accessToken);
    },
  };
}
