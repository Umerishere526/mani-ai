// ABOUTME: Placeholder exercise data standing in for the exercises tRPC router, which
// ABOUTME: doesn't exist in this app yet — replace with a real fetch once the backend lands.

import type { Exercise } from '@/types/exercise';

export const HOME_EXERCISES: Exercise[] = [
  {
    id: 'breathing-reset',
    title: 'Breathing Reset',
    description: 'A short breathing exercise to help you settle.',
    subtitle: null,
    type: 'Breathing',
    category: null,
    durationMinutes: 3.5,
    audioUrl: null,
  },
  {
    id: 'grounding-meditation',
    title: 'Grounding Meditation',
    description: 'Reconnect with the present moment.',
    subtitle: null,
    type: 'Meditation',
    category: null,
    durationMinutes: 5,
    audioUrl: null,
  },
];

export const EXERCISES_BY_CATEGORY: Record<string, Exercise[]> = {
  Anxiety: [
    {
      id: 'anxiety-breathing',
      title: 'Calming Breath',
      description: 'A gentle breathing pattern to ease anxious moments.',
      subtitle: null,
      type: 'Breathing',
      category: 'Anxiety',
      durationMinutes: 4,
      audioUrl: null,
    },
  ],
  Boundaries: [],
  BuildingHabits: [],
  Burnout: [],
  EmotionalIntelligence: [],
  NarcissisticDynamics: [],
};

export function getExerciseById(id: string): Exercise | undefined {
  return [...HOME_EXERCISES, ...Object.values(EXERCISES_BY_CATEGORY).flat()].find((exercise) => exercise.id === id);
}
