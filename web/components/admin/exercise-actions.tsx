// ABOUTME: Row actions for an exercise in the Exercises library — edit, activate/deactivate, delete.
// ABOUTME: Ported from mani-app's app/admin/exercises/ExerciseActions.tsx, restyled to Tailwind.

"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { AdminExercise } from "@/types";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.exercises.actions;

interface ExerciseActionsProps {
  exercise: AdminExercise;
  canEdit: boolean;
  canAdmin: boolean;
}

const SECONDARY_BUTTON =
  "rounded-mani-md border border-mani-border px-3 py-1.5 text-sm font-medium text-mani-text transition-colors duration-200 hover:border-mani-text-light hover:bg-mani-bg disabled:cursor-not-allowed disabled:opacity-50";
const DANGER_BUTTON =
  "rounded-mani-md border border-mani-border px-3 py-1.5 text-sm font-medium text-mani-error transition-colors duration-200 hover:border-mani-text-light hover:bg-mani-bg disabled:cursor-not-allowed disabled:opacity-50";

export function ExerciseActions({ exercise, canEdit, canAdmin }: ExerciseActionsProps) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const handleToggleActive = () => {
    startTransition(async () => {
      // No backend yet — placeholder data doesn't persist this toggle.
      console.log("toggle exercise active", exercise.id, !exercise.isActive);
      router.refresh();
    });
  };

  const handleDelete = () => {
    startTransition(async () => {
      // No backend yet — placeholder data doesn't persist this delete.
      console.log("delete exercise", exercise.id);
      setShowDeleteConfirm(false);
      router.refresh();
    });
  };

  return (
    <div className="flex items-center justify-end gap-2">
      {canEdit && (
        <Link href={`/admin/exercises/${exercise.id}`} className={SECONDARY_BUTTON}>
          {STRINGS.edit}
        </Link>
      )}

      {canAdmin && (
        <>
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
        </>
      )}
    </div>
  );
}
