// ABOUTME: Admin Exercises list — home screen section plus library exercises grouped by category.
// ABOUTME: Reads the whole catalog, inactive exercises included, from the backend on each request.

import { EmptyState, PageHeader } from "@/components/shared";
import { HomeScreenSection } from "@/components/admin/home-screen-section";
import { ExerciseCategoryTable } from "@/components/admin/exercise-category-table";
import { listExercises } from "@/lib/api/exercises";
import type { AdminExercise } from "@/types";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.exercises;

export default async function ExercisesPage() {
  const exercises = await listExercises();
  const libraryExercises = exercises.filter((e) => !e.showOnHomeScreen);

  const exercisesByCategory = libraryExercises.reduce<Record<string, AdminExercise[]>>((acc, exercise) => {
    acc[exercise.category] ??= [];
    acc[exercise.category].push(exercise);
    return acc;
  }, {});
  const categories = Object.keys(exercisesByCategory).sort();

  return (
    <div>
      <PageHeader title={STRINGS.title} action={{ label: STRINGS.newButton, href: "/admin/exercises/new" }} />

      <HomeScreenSection exercises={exercises} />

      <div className="mb-4">
        <h2 className="text-lg font-medium text-mani-text">{STRINGS.libraryTitle}</h2>
        <p className="text-sm text-mani-text-muted">{STRINGS.libraryDescription}</p>
      </div>

      {libraryExercises.length === 0 ? (
        <EmptyState message={STRINGS.empty} action={{ label: STRINGS.emptyAction, href: "/admin/exercises/new" }} />
      ) : (
        <div className="space-y-8">
          {categories.map((category) => (
            <ExerciseCategoryTable key={category} category={category} exercises={exercisesByCategory[category]} />
          ))}
        </div>
      )}
    </div>
  );
}
