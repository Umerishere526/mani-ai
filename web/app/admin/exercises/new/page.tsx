// ABOUTME: Admin page for creating a new exercise.
// ABOUTME: Ported from mani-app's app/admin/exercises/new/page.tsx.

import { BackLink } from "@/components/shared";
import { ExerciseForm } from "@/components/admin";
import type { AdminExercise } from "@/types";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.exercises;

async function createExercise(formData: FormData): Promise<AdminExercise> {
  "use server";
  // No backend yet — placeholder data doesn't persist this create.
  console.log("create exercise", Object.fromEntries(formData.entries()));
  return {
    id: `exercise-${Date.now()}`,
    title: String(formData.get("title") ?? ""),
    description: String(formData.get("description") ?? ""),
    subtitle: null,
    type: "Breathing",
    category: (formData.get("category") as AdminExercise["category"]) ?? null,
    durationMinutes: Number(formData.get("durationMinutes") ?? 0),
    audioUrl: (formData.get("audioUrl") as string) || null,
    displayOrder: Number(formData.get("displayOrder") ?? 0),
    showOnHomeScreen: formData.get("showOnHomeScreen") === "true",
    isActive: formData.get("isActive") === "true",
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
}

export default function NewExercisePage() {
  return (
    <div>
      <div className="mb-8">
        <BackLink href="/admin/exercises">{STRINGS.backToExercises}</BackLink>
        <h1 className="text-[1.75rem] font-semibold tracking-tight text-mani-text">{STRINGS.newTitle}</h1>
      </div>

      <ExerciseForm onSubmit={createExercise} submitLabel={STRINGS.newSubmitLabel} />
    </div>
  );
}
