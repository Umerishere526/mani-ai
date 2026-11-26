// ABOUTME: Supabase Auth (GoTrue) over HTTP from the server: password sign-in, refresh, user lookup, sign-out.
// ABOUTME: Server-only; the anon key and the tokens never reach the browser.

export interface AuthSession {
  accessToken: string;
  refreshToken: string;
}

export interface AuthUser {
  id: string;
  email: string | null;
  appMetadata: Record<string, unknown>;
}

interface TokenResponse {
  access_token?: string;
  refresh_token?: string;
}

interface UserResponse {
  id?: string;
  email?: string | null;
  app_metadata?: Record<string, unknown> | null;
}

// GoTrue answers a wrong email or password, and a spent refresh token, with 400.
const REJECTED_STATUS = 400;

function authUrl(path: string): string {
  const base = process.env.SUPABASE_URL;
  if (!base) throw new Error("SUPABASE_URL is not set");
  return `${base.replace(/\/$/, "")}/auth/v1${path}`;
}

function authHeaders(accessToken?: string): HeadersInit {
  const anonKey = process.env.SUPABASE_ANON_KEY;
  if (!anonKey) throw new Error("SUPABASE_ANON_KEY is not set");
  return {
    apikey: anonKey,
    Authorization: `Bearer ${accessToken ?? anonKey}`,
    "Content-Type": "application/json",
  };
}

/** A session, null when GoTrue refuses the credentials, or a thrown error when it cannot answer. */
async function requestSession(grantType: string, body: object): Promise<AuthSession | null> {
  const response = await fetch(authUrl(`/token?grant_type=${grantType}`), {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (response.status === REJECTED_STATUS) return null;
  if (!response.ok) throw new Error(`auth server answered ${response.status}`);
  const data = (await response.json()) as TokenResponse;
  if (!data?.access_token || !data?.refresh_token) throw new Error("auth server returned no tokens");
  return { accessToken: data.access_token, refreshToken: data.refresh_token };
}

export function signInWithPassword(email: string, password: string): Promise<AuthSession | null> {
  return requestSession("password", { email, password });
}

export function refreshSession(refreshToken: string): Promise<AuthSession | null> {
  return requestSession("refresh_token", { refresh_token: refreshToken });
}

/** The user a token belongs to, verified by the auth server, or null when the token is not valid. */
export async function getUser(accessToken: string): Promise<AuthUser | null> {
  const response = await fetch(authUrl("/user"), { headers: authHeaders(accessToken), cache: "no-store" });
  if (response.status === 401 || response.status === 403) return null;
  if (!response.ok) throw new Error(`auth server answered ${response.status}`);
  const data = (await response.json()) as UserResponse;
  if (!data?.id) return null;
  return { id: data.id, email: data.email ?? null, appMetadata: data.app_metadata ?? {} };
}

/** Revokes the refresh tokens behind an access token. Signing out locally does not wait on it succeeding. */
export async function signOut(accessToken: string): Promise<void> {
  await fetch(authUrl("/logout"), { method: "POST", headers: authHeaders(accessToken), cache: "no-store" });
}
