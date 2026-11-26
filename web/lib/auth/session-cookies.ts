// ABOUTME: The admin session's cookies: their names and options, and writing or clearing them on any cookie store.
// ABOUTME: Works on next/headers cookies() in actions and on NextResponse cookies in the proxy.

import type { AuthSession } from "./gotrue";

export const ACCESS_COOKIE = "mani_admin_access";
export const REFRESH_COOKIE = "mani_admin_refresh";

// The refresh token outlives the hour-long access token; the proxy trades it for a fresh pair.
const SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 7;

interface CookieOptions {
  httpOnly: boolean;
  secure: boolean;
  sameSite: "lax";
  path: string;
  maxAge: number;
}

interface CookieStore {
  set(name: string, value: string, options: CookieOptions): unknown;
  delete(name: string): unknown;
}

function sessionCookieOptions(): CookieOptions {
  return {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: SESSION_MAX_AGE_SECONDS,
  };
}

export function writeSession(store: CookieStore, session: AuthSession): void {
  store.set(ACCESS_COOKIE, session.accessToken, sessionCookieOptions());
  store.set(REFRESH_COOKIE, session.refreshToken, sessionCookieOptions());
}

export function clearSession(store: CookieStore): void {
  store.delete(ACCESS_COOKIE);
  store.delete(REFRESH_COOKIE);
}
