// ABOUTME: Admin page for editing an existing exercise.
// ABOUTME: Reads the exercise from the backend catalog; the form saves through saveExercise.

import { notFound } from "next/navigation";
import { BackLink } from "@/components/shared";
import { ExerciseForm } from "@/components/admin";
import { getExercise } from "@/lib/api/exercises";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.exercises;

export default async function ExerciseEditPage({ params }: PageProps<"/admin/exercises/[id]">) {
  const { id } = await params;
  const exercise = await getExercise(id);

  if (!exercise) {
    notFound();
  }

  return (
    <div>
      <div className="mb-8">
        <BackLink href="/admin/exercises">{STRINGS.backToExercises}</BackLink>
        <h1 className="text-[1.75rem] font-semibold tracking-tight text-mani-text">{STRINGS.editTitle}</h1>
        <p className="mt-1 text-sm text-mani-text-muted">{exercise.title}</p>
      </div>

      <ExerciseForm exercise={exercise} submitLabel={STRINGS.editSubmitLabel} />
    </div>
  );
}
