// ABOUTME: Row actions for an exercise in the Exercises library — edit, activate/deactivate, delete.
// ABOUTME: Activation and deletion run through the exercise server actions.

"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import { deleteExercise, updateExerciseFields } from "@/lib/actions/exercises";
import type { AdminExercise } from "@/types";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.exercises.actions;

interface ExerciseActionsProps {
  exercise: AdminExercise;
}

const SECONDARY_BUTTON =
  "rounded-mani-md border border-mani-border px-3 py-1.5 text-sm font-medium text-mani-text transition-colors duration-200 hover:border-mani-text-light hover:bg-mani-bg disabled:cursor-not-allowed disabled:opacity-50";
const DANGER_BUTTON =
  "rounded-mani-md border border-mani-border px-3 py-1.5 text-sm font-medium text-mani-error transition-colors duration-200 hover:border-mani-text-light hover:bg-mani-bg disabled:cursor-not-allowed disabled:opacity-50";

export function ExerciseActions({ exercise }: ExerciseActionsProps) {
  const [isPending, startTransition] = useTransition();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleToggleActive = () => {
    setError(null);
    startTransition(async () => {
      const result = await updateExerciseFields(exercise.id, { isActive: !exercise.isActive });
      setError(result.error);
    });
  };

  const handleDelete = () => {
    setError(null);
    startTransition(async () => {
      const result = await deleteExercise(exercise.id);
      setError(result.error);
      setShowDeleteConfirm(false);
    });
  };

  return (
    <div className="flex items-center justify-end gap-2">
      {error && <span className="text-sm text-mani-error">{error}</span>}
      <Link href={`/admin/exercises/${exercise.id}`} className={SECONDARY_BUTTON}>
        {STRINGS.edit}
      </Link>

      <button type="button" onClick={handleToggleActive} disabled={isPending} className={SECONDARY_BUTTON}>
        {exercise.isActive ? STRINGS.deactivate : STRINGS.activate}
      </button>

      {showDeleteConfirm ? (
        <div className="flex items-center gap-1">
          <button type="button" onClick={handleDelete} disabled={isPending} className={DANGER_BUTTON}>
            {STRINGS.confirmDelete}
          </button>
          <button
            type="button"
            onClick={() => setShowDeleteConfirm(false)}
            disabled={isPending}
            className={SECONDARY_BUTTON}
          >
            {STRINGS.cancel}
          </button>
        </div>
      ) : (
        <button type="button" onClick={() => setShowDeleteConfirm(true)} className={DANGER_BUTTON}>
          {STRINGS.delete}
        </button>
      )}
    </div>
  );
}
