// ABOUTME: Admin page for creating a new exercise.
// ABOUTME: The form saves through the saveExercise server action.

import { BackLink } from "@/components/shared";
import { ExerciseForm } from "@/components/admin";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.exercises;

export default function NewExercisePage() {
  return (
    <div>
      <div className="mb-8">
        <BackLink href="/admin/exercises">{STRINGS.backToExercises}</BackLink>
        <h1 className="text-[1.75rem] font-semibold tracking-tight text-mani-text">{STRINGS.newTitle}</h1>
      </div>

      <ExerciseForm submitLabel={STRINGS.newSubmitLabel} />
    </div>
  );
}
