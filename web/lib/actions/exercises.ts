// ABOUTME: Server actions for the exercise catalog: save the form, change single fields, delete.
// ABOUTME: Each validates its input here and goes through adminFetch, which re-checks the admin session.

"use server";

import { revalidatePath } from "next/cache";
import { adminFetch } from "@/lib/api/admin-fetch";
import type { ExerciseRecord } from "@/lib/api/exercises";
import { exerciseFormSchema } from "@/lib/schema";
import dictionary from "@/dictionaries/en.json";
import { runAdminAction, type ActionResult } from "./action-result";

const STRINGS = dictionary.admin.forms.exercise;

export interface SaveExerciseResult extends ActionResult {
  exerciseId: string | null;
}

interface ExerciseFieldChanges {
  isActive?: boolean;
  showOnHomeScreen?: boolean;
  displayOrder?: number;
}

function revalidateExercises(): void {
  revalidatePath("/admin/exercises", "layout");
}

function exercisePath(exerciseId: string): string {
  return `/exercises/${encodeURIComponent(exerciseId)}`;
}

function readForm(formData: FormData) {
  const duration = String(formData.get("durationMinutes") ?? "").trim();
  return exerciseFormSchema.safeParse({
    title: String(formData.get("title") ?? ""),
    description: String(formData.get("description") ?? ""),
    category: String(formData.get("category") ?? ""),
    audioPath: String(formData.get("audioPath") ?? ""),
    durationMinutes: duration ? Number(duration) : null,
    displayOrder: Number(formData.get("displayOrder") ?? 0),
    showOnHomeScreen: formData.get("showOnHomeScreen") === "true",
    isActive: formData.get("isActive") === "true",
  });
}

/** Creates the exercise when exerciseId is null, otherwise updates it. */
export async function saveExercise(exerciseId: string | null, formData: FormData): Promise<SaveExerciseResult> {
  const parsed = readForm(formData);
  if (!parsed.success) return { error: STRINGS.invalidInput, exerciseId };

  const { data } = parsed;
  const body = {
    title: data.title,
    description: data.description,
    category: data.category,
    audio_path: data.audioPath,
    duration_minutes: data.durationMinutes ?? undefined,
    display_order: data.displayOrder,
    show_on_home_screen: data.showOnHomeScreen,
    is_active: data.isActive,
  };

  let savedId = exerciseId;
  const result = await runAdminAction(async () => {
    const saved = exerciseId
      ? await adminFetch<ExerciseRecord>(exercisePath(exerciseId), { method: "PATCH", body })
      : await adminFetch<ExerciseRecord>("/exercises", { method: "POST", body });
    savedId = saved?.id ?? null;
  });
  revalidateExercises();
  return { ...result, exerciseId: savedId };
}

export async function updateExerciseFields(exerciseId: string, changes: ExerciseFieldChanges): Promise<ActionResult> {
  if (changes.displayOrder !== undefined && (!Number.isInteger(changes.displayOrder) || changes.displayOrder < 0)) {
    return { error: STRINGS.invalidInput };
  }
  const body = {
    is_active: changes.isActive,
    show_on_home_screen: changes.showOnHomeScreen,
    display_order: changes.displayOrder,
  };
  const result = await runAdminAction(() => adminFetch(exercisePath(exerciseId), { method: "PATCH", body }));
  revalidateExercises();
  return result;
}

export async function deleteExercise(exerciseId: string): Promise<ActionResult> {
  const result = await runAdminAction(() => adminFetch(exercisePath(exerciseId), { method: "DELETE" }));
  revalidateExercises();
  return result;
}
