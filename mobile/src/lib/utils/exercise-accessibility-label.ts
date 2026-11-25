// ABOUTME: An exercise's meta line (its length and type, or Coming soon before it is recorded) and the screen-reader
// ABOUTME: label for its row or card: title then the meta line, in the order they are shown.

import en from '@/dictionaries/en.json';
import type { Exercise } from '@/types/exercise';
import { formatDuration } from './format-duration';

export function exerciseMeta(exercise: Exercise): string[] {
  if (!exercise.recorded) return [en.exercises.comingSoonItem];
  const length = exercise.durationMinutes === null ? null : formatDuration(exercise.durationMinutes);
  return [length, exercise.type].filter((part): part is string => Boolean(part));
}

export function exerciseAccessibilityLabel(exercise: Exercise): string {
  return [exercise.title, ...exerciseMeta(exercise)].join(', ');
}
