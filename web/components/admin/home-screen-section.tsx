// ABOUTME: Section on the Exercises page listing exercises shown as home-screen quick-action cards.
// ABOUTME: Ported from mani-app's app/admin/exercises/HomeScreenSection.tsx, restyled to Tailwind.

import { HomeScreenExerciseRow } from "./home-screen-exercise-row";
import type { AdminExercise } from "@/types";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.exercises.homeScreen;

interface HomeScreenSectionProps {
  exercises: AdminExercise[];
  canEdit: boolean;
}

export function HomeScreenSection({ exercises, canEdit }: HomeScreenSectionProps) {
  const homeScreenExercises = exercises
    .filter((e) => e.showOnHomeScreen)
    .sort((a, b) => a.displayOrder - b.displayOrder);

  return (
    <div className="mb-10">
      <h2 className="mb-2 text-lg font-medium text-mani-text">{STRINGS.title}</h2>
      <p className="mb-4 text-sm text-mani-text-muted">{STRINGS.description}</p>

      {homeScreenExercises.length === 0 ? (
        <div className="rounded-mani-md bg-mani-bg-card p-4 text-center text-sm text-mani-text-muted">
          {STRINGS.empty}
          {canEdit && STRINGS.emptyHelper}
        </div>
      ) : (
        <div className="space-y-2">
          {homeScreenExercises.map((exercise, index) => (
            <HomeScreenExerciseRow key={exercise.id} exercise={exercise} canEdit={canEdit} position={index + 1} />
          ))}
        </div>
      )}
    </div>
  );
}
