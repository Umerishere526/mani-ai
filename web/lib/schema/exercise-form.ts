// ABOUTME: Validation schema for the admin Exercise form, checked again inside the save action.
// ABOUTME: The backend requires a title, a category and an audio path on every exercise.

import { z } from "zod";

export const exerciseFormSchema = z.object({
  title: z.string().trim().min(1),
  description: z.string().trim(),
  category: z.string().trim().min(1),
  audioPath: z.string().trim().min(1),
  durationMinutes: z.number().positive().nullable(),
  displayOrder: z.number().int().min(0),
  showOnHomeScreen: z.boolean(),
  isActive: z.boolean(),
});

export type ExerciseFormValues = z.infer<typeof exerciseFormSchema>;
