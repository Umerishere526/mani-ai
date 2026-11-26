// ABOUTME: Guards /admin: sends a visitor without a session to sign-in, and refreshes an expiring access token.
// ABOUTME: An optimistic check only; lib/auth/require-admin.ts verifies the token and the admin claim on every read.

import { NextResponse, type NextRequest } from "next/server";
import { needsRefresh } from "@/lib/auth/access-token";
import { refreshSession } from "@/lib/auth/gotrue";
import { ACCESS_COOKIE, REFRESH_COOKIE, clearSession, writeSession } from "@/lib/auth/session-cookies";

function toSignIn(request: NextRequest): NextResponse {
  const response = NextResponse.redirect(new URL("/auth/login", request.url));
  clearSession(response.cookies);
  return response;
}

export async function proxy(request: NextRequest) {
  const accessToken = request.cookies.get(ACCESS_COOKIE)?.value;
  if (accessToken && !needsRefresh(accessToken)) return NextResponse.next();

  const refreshToken = request.cookies.get(REFRESH_COOKIE)?.value;
  if (!refreshToken) return toSignIn(request);

  const session = await refreshSession(refreshToken).catch(() => null);
  if (!session) return toSignIn(request);

  // The page rendering this request reads the fresh token; the browser keeps it for the next one.
  request.cookies.set(ACCESS_COOKIE, session.accessToken);
  request.cookies.set(REFRESH_COOKIE, session.refreshToken);
  const response = NextResponse.next({ request });
  writeSession(response.cookies, session);
  return response;
}

export const config = {
  matcher: "/admin/:path*",
};
