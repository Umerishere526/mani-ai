// ABOUTME: Types for the admin Exercises section — guided audio exercises.
// ABOUTME: The shape the backend's /v1/admin/exercises endpoints return, in camelCase.

export interface AdminExercise {
  id: string;
  title: string;
  subtitle: string | null;
  description: string;
  type: string | null;
  category: string;
  audioPath: string;
  durationMinutes: number | null;
  displayOrder: number;
  showOnHomeScreen: boolean;
  frameworkId: string | null;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}
