// ABOUTME: Server actions for prompts: create, edit, activate or deactivate, and roll back to a past version.
// ABOUTME: Each validates its input here and goes through adminFetch, which re-checks the admin session.

"use server";

import { revalidatePath } from "next/cache";
import { adminFetch } from "@/lib/api/admin-fetch";
import { listPromptVersions } from "@/lib/api/prompts";
import { promptFormSchema, type PromptFormValues } from "@/lib/schema";
import dictionary from "@/dictionaries/en.json";
import { runAdminAction, type ActionResult } from "./action-result";

const STRINGS = dictionary.admin.pages.prompts;

function revalidatePrompts(): void {
  revalidatePath("/admin/prompts", "layout");
}

/** The fields the backend stores, from validated form values; blank model fields are left unset. */
function toPromptBody(values: PromptFormValues) {
  const parameters = values.modelParameters?.trim();
  return {
    description: values.description ?? "",
    content: values.content,
    model_id: values.modelId?.trim() ? values.modelId.trim() : undefined,
    model_parameters: parameters ? (JSON.parse(parameters) as Record<string, unknown>) : undefined,
  };
}

export async function createPrompt(values: PromptFormValues): Promise<ActionResult> {
  const parsed = promptFormSchema.safeParse(values);
  if (!parsed.success) return { error: STRINGS.invalidInput };
  const result = await runAdminAction(() =>
    adminFetch("/prompts", { method: "POST", body: { name: parsed.data.name, ...toPromptBody(parsed.data) } }),
  );
  revalidatePrompts();
  return result;
}

export async function updatePrompt(promptId: string, values: PromptFormValues): Promise<ActionResult> {
  const parsed = promptFormSchema.safeParse(values);
  if (!parsed.success) return { error: STRINGS.invalidInput };
  const changeSummary = parsed.data.changeSummary?.trim();
  const body = { ...toPromptBody(parsed.data), change_summary: changeSummary ? changeSummary : undefined };
  const result = await runAdminAction(() =>
    adminFetch(`/prompts/${encodeURIComponent(promptId)}`, { method: "PATCH", body }),
  );
  revalidatePrompts();
  return result;
}

export async function setPromptActive(promptId: string, isActive: boolean): Promise<ActionResult> {
  const result = await runAdminAction(() =>
    adminFetch(`/prompts/${encodeURIComponent(promptId)}`, { method: "PATCH", body: { is_active: isActive } }),
  );
  revalidatePrompts();
  return result;
}

/** Publishes a past version's content and model settings as the next version. */
export async function rollbackPrompt(promptId: string, version: number): Promise<ActionResult> {
  const versions = await listPromptVersions(promptId);
  const target = versions.find((candidate) => candidate.version === version);
  if (!target) return { error: STRINGS.versions.rollbackError };

  const body = {
    content: target.content,
    model_id: target.modelId ?? undefined,
    model_parameters: target.modelParameters,
    routing: target.routing,
    change_summary: STRINGS.versions.rollbackSummary.replace("{version}", String(version)),
  };
  const result = await runAdminAction(() =>
    adminFetch(`/prompts/${encodeURIComponent(promptId)}`, { method: "PATCH", body }),
  );
  revalidatePrompts();
  return result;
}
