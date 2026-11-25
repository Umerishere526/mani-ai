// ABOUTME: The admin data-access check: the session cookie's token, verified by the auth server, carrying the admin claim.
// ABOUTME: Redirects to sign-in without a valid session and to the access-denied page without the claim.

import { cache } from "react";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { getUser, type AuthUser } from "./gotrue";
import { ACCESS_COOKIE } from "./session-cookies";

// The backend grants admin access on the same claim (backend/mani/auth/jwt.py, Claims.is_admin).
const ADMIN_ROLE = "admin";

export interface AdminSession {
  accessToken: string;
  email: string;
}

export function hasAdminClaim(user: AuthUser): boolean {
  return user?.appMetadata?.admin_role === ADMIN_ROLE;
}

export const requireAdmin = cache(async (): Promise<AdminSession> => {
  const accessToken = (await cookies()).get(ACCESS_COOKIE)?.value;
  if (!accessToken) redirect("/auth/login");

  const user = await getUser(accessToken);
  if (!user) redirect("/auth/login");
  if (!hasAdminClaim(user)) redirect("/auth/unauthorized");

  return { accessToken, email: user.email ?? "" };
});
