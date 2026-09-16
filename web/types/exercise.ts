// ABOUTME: Types for the admin Exercises section — guided audio exercises.
// ABOUTME: Ported from mani-app's lib/db/exercises.ts AdminExercise shape.

export type ExerciseType = "Breathing" | "Meditation" | "Visualization";

export type ExerciseCategory =
  | "EmotionalIntelligence"
  | "NarcissisticDynamics"
  | "BuildingHabits"
  | "Boundaries"
  | "Anxiety"
  | "Burnout";

export interface AdminExercise {
  id: string;
  title: string;
  description: string;
  subtitle: string | null;
  type: ExerciseType;
  category: ExerciseCategory | null;
  durationMinutes: number;
  audioUrl: string | null;
  displayOrder: number;
  showOnHomeScreen: boolean;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}
