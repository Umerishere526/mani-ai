// ABOUTME: Admin page for editing an existing exercise.
// ABOUTME: Ported from mani-app's app/admin/exercises/[id]/page.tsx.

import { notFound } from "next/navigation";
import { BackLink } from "@/components/shared";
import { ExerciseForm } from "@/components/admin";
import { getExerciseById } from "@/lib/placeholder-exercises";
import type { AdminExercise } from "@/types";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.exercises;

interface ExerciseEditPageProps {
  params: Promise<{ id: string }>;
}

export default async function ExerciseEditPage({ params }: ExerciseEditPageProps) {
  const { id } = await params;
  const exercise = getExerciseById(id);

  if (!exercise) {
    notFound();
  }
  const currentExercise: AdminExercise = exercise;

  async function handleUpdate(formData: FormData): Promise<AdminExercise> {
    "use server";
    // No backend yet — placeholder data doesn't persist this update.
    console.log("update exercise", id, Object.fromEntries(formData.entries()));
    return {
      ...currentExercise,
      title: String(formData.get("title") ?? currentExercise.title),
      description: String(formData.get("description") ?? currentExercise.description),
      updatedAt: new Date().toISOString(),
    };
  }

  return (
    <div>
      <div className="mb-8">
        <BackLink href="/admin/exercises">{STRINGS.backToExercises}</BackLink>
        <h1 className="text-[1.75rem] font-semibold tracking-tight text-mani-text">{STRINGS.editTitle}</h1>
        <p className="mt-1 text-sm text-mani-text-muted">{exercise.title}</p>
      </div>

      <ExerciseForm exercise={exercise} onSubmit={handleUpdate} submitLabel={STRINGS.editSubmitLabel} />
    </div>
  );
}
