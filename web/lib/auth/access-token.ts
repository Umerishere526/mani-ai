// ABOUTME: Reads the expiry from an access token's payload without verifying it, to decide when to refresh.
// ABOUTME: Never an authorization check: the auth server and the backend verify every token they act on.

// Refresh a little early so a token does not expire between the proxy and the backend call.
const REFRESH_MARGIN_SECONDS = 60;

function expiresAt(token: string): number | null {
  const payload = token.split(".")?.[1];
  if (!payload) return null;
  try {
    const json = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    const exp = (JSON.parse(json) as { exp?: unknown })?.exp;
    return typeof exp === "number" ? exp : null;
  } catch {
    return null;
  }
}

/** True when the token is unreadable, expired, or about to expire. */
export function needsRefresh(token: string, nowSeconds: number = Date.now() / 1000): boolean {
  const exp = expiresAt(token);
  return exp === null || exp - REFRESH_MARGIN_SECONDS <= nowSeconds;
}
