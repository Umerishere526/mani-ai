// ABOUTME: Builds the screen-reader label for an exercise row or card: title, duration and
// ABOUTME: type, in the same order the visible meta line and title show them.

import type { Exercise } from '@/types/exercise';
import { formatDuration } from './format-duration';

export function exerciseAccessibilityLabel(exercise: Exercise): string {
  return `${exercise.title}, ${formatDuration(exercise.durationMinutes)}, ${exercise.type}`;
}
