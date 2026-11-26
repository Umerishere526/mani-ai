// ABOUTME: How a library topic's listing is laid out: its own exercises first, then the ones it lists from other
// ABOUTME: topics under each subcategory, in the order the backend sends them.

import type { Exercise, ExerciseGroup } from '@/types/exercise';

export function groupBySubcategory(exercises: Exercise[]): ExerciseGroup[] {
  const groups = new Map<string | null, Exercise[]>();
  for (const exercise of exercises) {
    groups.set(exercise.subcategory, [...(groups.get(exercise.subcategory) ?? []), exercise]);
  }
  return [...groups].map(([subcategory, grouped]) => ({ subcategory, exercises: grouped }));
}
