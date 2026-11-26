// ABOUTME: Reads the full exercise catalog, inactive exercises included, for the admin Exercises pages.
// ABOUTME: The backend has no single-exercise read, so one exercise is found in the catalog.

import type { AdminExercise } from "@/types";
import { adminFetch } from "./admin-fetch";

export interface ExerciseRecord {
  id: string;
  title: string;
  subtitle?: string | null;
  description?: string | null;
  type?: string | null;
  category: string;
  audio_path: string;
  duration_minutes?: number | null;
  display_order?: number | null;
  show_on_home_screen?: boolean | null;
  framework_id?: string | null;
  is_active?: boolean | null;
  created_at: string;
  updated_at: string;
}

export function toExercise(record: ExerciseRecord): AdminExercise {
  return {
    id: record.id,
    title: record.title,
    subtitle: record.subtitle ?? null,
    description: record.description ?? "",
    type: record.type ?? null,
    category: record.category,
    audioPath: record.audio_path,
    durationMinutes: record.duration_minutes ?? null,
    displayOrder: record.display_order ?? 0,
    showOnHomeScreen: record.show_on_home_screen ?? false,
    frameworkId: record.framework_id ?? null,
    isActive: record.is_active ?? true,
    createdAt: record.created_at,
    updatedAt: record.updated_at,
  };
}

export async function listExercises(): Promise<AdminExercise[]> {
  const records = await adminFetch<ExerciseRecord[]>("/exercises");
  return records.map(toExercise);
}

export async function getExercise(id: string): Promise<AdminExercise | null> {
  const exercises = await listExercises();
  return exercises.find((exercise) => exercise.id === id) ?? null;
}
