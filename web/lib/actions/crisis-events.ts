// ABOUTME: Server action that marks a crisis event resolved, with the admin's note on what was done.
// ABOUTME: Posts to the backend's resolve endpoint, which re-checks the admin claim.

"use server";

import { revalidatePath } from "next/cache";
import { adminFetch } from "@/lib/api/admin-fetch";
import dictionary from "@/dictionaries/en.json";
import { runAdminAction, type ActionResult } from "./action-result";

const STRINGS = dictionary.admin.pages.crisisEvents;

export async function resolveCrisisEvent(
  eventId: string,
  _previous: ActionResult,
  formData: FormData,
): Promise<ActionResult> {
  const resolution = String(formData.get("resolution") ?? "").trim();
  if (!resolution) return { error: STRINGS.resolutionRequired };

  const result = await runAdminAction(() =>
    adminFetch(`/crisis-events/${encodeURIComponent(eventId)}/resolve`, { method: "POST", body: { resolution } }),
  );
  revalidatePath("/admin/crisis-events");
  return result;
}
