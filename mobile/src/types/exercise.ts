// ABOUTME: Exercise library UI shapes, mirroring @mani/api's exercise/topic schemas by
// ABOUTME: structure only (no zod, no backend import) — this app has no API layer yet.

export type TopicId =
  | 'EmotionalIntelligence'
  | 'BuildingHabits'
  | 'Boundaries'
  | 'Anxiety'
  | 'Burnout';

export type ExerciseType = 'Breathing' | 'Meditation' | 'Visualization';

export interface Exercise {
  id: string;
  title: string;
  description: string;
  subtitle: string | null;
  type: ExerciseType;
  category: TopicId | null;
  durationMinutes: number;
  audioUrl: string | null;
}
