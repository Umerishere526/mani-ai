// ABOUTME: Reads people's ratings of library exercises for the admin Feedback page.
// ABOUTME: Most recently changed first, optionally filtered by part of an email.

import type { ExerciseFeedback, FeedbackRating } from "@/types";
import { adminFetch } from "./admin-fetch";

interface ExerciseFeedbackRecord {
  user_id: string;
  user_email?: string | null;
  exercise_id: string;
  exercise_title: string;
  exercise_type?: string | null;
  category: string;
  rating: FeedbackRating;
  reason?: string | null;
  updated_at: string;
}

function toExerciseFeedback(record: ExerciseFeedbackRecord): ExerciseFeedback {
  return {
    userId: record.user_id,
    userEmail: record.user_email ?? null,
    exerciseId: record.exercise_id,
    exerciseTitle: record.exercise_title,
    exerciseType: record.exercise_type ?? null,
    category: record.category,
    rating: record.rating,
    reason: record.reason ?? null,
    updatedAt: record.updated_at,
  };
}

export async function listExerciseFeedback(search?: string): Promise<ExerciseFeedback[]> {
  const query = new URLSearchParams();
  if (search) query.set("search", search);
  const records = await adminFetch<ExerciseFeedbackRecord[]>(`/exercise-feedback?${query.toString()}`);
  return records.map(toExerciseFeedback);
}
