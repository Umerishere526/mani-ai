// ABOUTME: Calls the backend's /v1/admin endpoints from the server with the signed-in admin's bearer token.
// ABOUTME: Every call checks the admin session first, so no admin data is read without it.

import { requireAdmin } from "@/lib/auth/require-admin";

const NOT_FOUND = 404;

export class AdminApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

interface ErrorBody {
  error?: { message?: string };
}

interface AdminRequest {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
}

function apiUrl(path: string): string {
  const base = process.env.MANI_API_URL;
  if (!base) throw new Error("MANI_API_URL is not set");
  return `${base.replace(/\/$/, "")}/v1/admin${path}`;
}

/** The parsed JSON body, undefined for 204, or an AdminApiError carrying the backend's safe message. */
export async function adminFetch<T>(path: string, { method = "GET", body }: AdminRequest = {}): Promise<T> {
  const { accessToken } = await requireAdmin();
  const response = await fetch(apiUrl(path), {
    method,
    headers: { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });

  if (!response.ok) {
    const error = (await response.json().catch(() => null)) as ErrorBody | null;
    throw new AdminApiError(response.status, error?.error?.message ?? `backend answered ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

/** A single record, or null when the backend says it does not exist. */
export async function adminFetchOrNull<T>(path: string): Promise<T | null> {
  try {
    return await adminFetch<T>(path);
  } catch (error) {
    if (error instanceof AdminApiError && error.status === NOT_FOUND) return null;
    throw error;
  }
}
