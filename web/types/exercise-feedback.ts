// ABOUTME: Types for the admin Feedback section — one person's rating of one library exercise.
// ABOUTME: The shape the backend's /v1/admin/exercise-feedback endpoint returns, in camelCase.

export type FeedbackRating = "up" | "down";

export interface ExerciseFeedback {
  userId: string;
  userEmail: string | null;
  exerciseId: string;
  exerciseTitle: string;
  exerciseType: string | null;
  category: string;
  rating: FeedbackRating;
  reason: string | null;
  updatedAt: string;
}
