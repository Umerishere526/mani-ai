// ABOUTME: Admin Exercises list — home screen section plus library exercises grouped by category.
// ABOUTME: Ported from mani-app's app/admin/exercises/page.tsx.

import Link from "next/link";
import { Badge, EmptyState } from "@/components/shared";
import { HomeScreenSection } from "@/components/admin/home-screen-section";
import { ExerciseActions } from "@/components/admin/exercise-actions";
import { ADMIN_EXERCISES } from "@/lib/placeholder-exercises";
import { ADMIN_PERMISSIONS } from "../lib/permissions";
import type { AdminExercise } from "@/types";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.exercises;
const CATEGORY_LABELS = dictionary.admin.forms.categories;
const COMMON = dictionary.admin.pages;

export default function ExercisesPage() {
  const { canEdit, canAdmin } = ADMIN_PERMISSIONS;

  const libraryExercises = ADMIN_EXERCISES.filter((e) => !e.showOnHomeScreen && e.category !== null);

  const exercisesByCategory = libraryExercises.reduce<Record<string, AdminExercise[]>>((acc, exercise) => {
    const category = exercise.category as string;
    acc[category] ??= [];
    acc[category].push(exercise);
    return acc;
  }, {});

  const categories = Object.keys(exercisesByCategory).sort();

  return (
    <div>
      <div className="mb-8 flex items-center justify-between">
        <h1 className="text-[1.75rem] font-semibold tracking-tight text-mani-text">{STRINGS.title}</h1>
        {canEdit && (
          <Link
            href="/admin/exercises/new"
            className="inline-flex items-center justify-center gap-2 rounded-mani-md bg-mani-accent px-5 py-2.5 text-[0.9375rem] font-medium text-white shadow-mani-sm transition-colors duration-200 hover:bg-mani-accent-hover"
          >
            {STRINGS.newButton}
          </Link>
        )}
      </div>

      <HomeScreenSection exercises={ADMIN_EXERCISES} canEdit={canEdit} />

      <div className="mb-4">
        <h2 className="text-lg font-medium text-mani-text">{STRINGS.libraryTitle}</h2>
        <p className="text-sm text-mani-text-muted">{STRINGS.libraryDescription}</p>
      </div>

      {libraryExercises.length === 0 ? (
        <EmptyState
          message={STRINGS.empty}
          action={canEdit ? { label: STRINGS.emptyAction, href: "/admin/exercises/new" } : undefined}
        />
      ) : (
        <div className="space-y-8">
          {categories.map((category) => (
            <div key={category}>
              <h3 className="mb-3 font-medium text-mani-text">{CATEGORY_LABELS[category as keyof typeof CATEGORY_LABELS] ?? category}</h3>
              <p className="mb-4 text-sm text-mani-text-muted">
                {exercisesByCategory[category].length}{" "}
                {exercisesByCategory[category].length !== 1 ? STRINGS.exerciseCountPlural : STRINGS.exerciseCountSingular}
              </p>
              <div className="overflow-hidden rounded-mani-lg bg-mani-bg-card shadow-mani-card">
                <table className="w-full border-collapse">
                  <thead className="bg-mani-bg">
                    <tr>
                      <th className="border-b border-mani-border px-6 py-3.5 text-left text-[0.6875rem] font-semibold uppercase tracking-wide text-mani-text-muted">
                        {STRINGS.colTitle}
                      </th>
                      <th className="border-b border-mani-border px-6 py-3.5 text-left text-[0.6875rem] font-semibold uppercase tracking-wide text-mani-text-muted">
                        {STRINGS.colDuration}
                      </th>
                      <th className="border-b border-mani-border px-6 py-3.5 text-left text-[0.6875rem] font-semibold uppercase tracking-wide text-mani-text-muted">
                        {STRINGS.colOrder}
                      </th>
                      <th className="border-b border-mani-border px-6 py-3.5 text-left text-[0.6875rem] font-semibold uppercase tracking-wide text-mani-text-muted">
                        {STRINGS.colStatus}
                      </th>
                      <th className="border-b border-mani-border px-6 py-3.5 text-right text-[0.6875rem] font-semibold uppercase tracking-wide text-mani-text-muted">
                        {STRINGS.colActions}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {exercisesByCategory[category].map((exercise) => (
                      <tr key={exercise.id} className="transition-colors duration-150 hover:bg-mani-bg">
                        <td className="border-b border-mani-border px-6 py-4 last:border-b-0">
                          <Link href={`/admin/exercises/${exercise.id}`} className="font-medium">
                            {exercise.title}
                          </Link>
                          {exercise.description && (
                            <p className="mt-0.5 max-w-xs truncate text-sm text-mani-text-muted">
                              {exercise.description}
                            </p>
                          )}
                        </td>
                        <td className="border-b border-mani-border px-6 py-4 text-sm text-mani-text last:border-b-0">
                          {exercise.durationMinutes}
                          {STRINGS.minutesSuffix}
                        </td>
                        <td className="border-b border-mani-border px-6 py-4 text-sm text-mani-text-muted last:border-b-0">
                          {exercise.displayOrder}
                        </td>
                        <td className="border-b border-mani-border px-6 py-4 last:border-b-0">
                          <Badge variant={exercise.isActive ? "success" : "neutral"}>
                            {exercise.isActive ? COMMON.active : COMMON.inactive}
                          </Badge>
                        </td>
                        <td className="border-b border-mani-border px-6 py-4 text-right last:border-b-0">
                          <ExerciseActions exercise={exercise} canEdit={canEdit} canAdmin={canAdmin} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
