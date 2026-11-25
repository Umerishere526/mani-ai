// ABOUTME: The result every admin mutation returns to its form: an error sentence for the admin, or none.
// ABOUTME: A backend refusal becomes its safe message; anything else is thrown to the error boundary.

import { AdminApiError } from "@/lib/api/admin-fetch";

export interface ActionResult {
  error: string | null;
}

export async function runAdminAction(work: () => Promise<unknown>): Promise<ActionResult> {
  try {
    await work();
    return { error: null };
  } catch (error) {
    if (error instanceof AdminApiError) return { error: error.message };
    throw error;
  }
}
