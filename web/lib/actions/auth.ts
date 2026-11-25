// ABOUTME: Server actions for the admin session: password sign-in and sign-out.
// ABOUTME: Tokens are written to httpOnly cookies; the browser never holds them in script.

"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { signInWithPassword, signOut } from "@/lib/auth/gotrue";
import { ACCESS_COOKIE, clearSession, writeSession } from "@/lib/auth/session-cookies";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.login;

export interface SignInState {
  error: string | null;
}

export async function signIn(_previous: SignInState, formData: FormData): Promise<SignInState> {
  const email = String(formData.get("email") ?? "").trim();
  const password = String(formData.get("password") ?? "");
  if (!email || !password) return { error: STRINGS.missingFields };

  let session;
  try {
    session = await signInWithPassword(email, password);
  } catch {
    return { error: STRINGS.unavailable };
  }
  if (!session) return { error: STRINGS.invalidCredentials };

  writeSession(await cookies(), session);
  redirect("/admin");
}

export async function signOutAdmin(): Promise<void> {
  const store = await cookies();
  const accessToken = store.get(ACCESS_COOKIE)?.value;
  if (accessToken) await signOut(accessToken).catch(() => undefined);
  clearSession(store);
  redirect("/auth/login");
}
