// ABOUTME: One row in the Home Screen section — edit link, inline display-order editor, remove.
// ABOUTME: Order and removal run through the updateExerciseFields server action.

"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import { Badge } from "@/components/shared";
import { updateExerciseFields } from "@/lib/actions/exercises";
import type { AdminExercise } from "@/types";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.exercises.homeScreen;

const SECONDARY_BUTTON =
  "rounded-mani-md border border-mani-border px-3 py-1.5 text-sm font-medium text-mani-text transition-colors duration-200 hover:border-mani-text-light hover:bg-mani-bg disabled:cursor-not-allowed disabled:opacity-50";
const DANGER_BUTTON =
  "rounded-mani-md border border-mani-border px-3 py-1.5 text-sm font-medium text-mani-error transition-colors duration-200 hover:border-mani-text-light hover:bg-mani-bg disabled:cursor-not-allowed disabled:opacity-50";

interface HomeScreenExerciseRowProps {
  exercise: AdminExercise;
  position: number;
}

export function HomeScreenExerciseRow({ exercise, position }: HomeScreenExerciseRowProps) {
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [orderValue, setOrderValue] = useState(exercise.displayOrder.toString());

  const handleRemove = () => {
    setError(null);
    startTransition(async () => {
      const result = await updateExerciseFields(exercise.id, { showOnHomeScreen: false });
      setError(result.error);
    });
  };

  const handleUpdateOrder = () => {
    const newOrder = parseInt(orderValue, 10);
    if (isNaN(newOrder) || newOrder === exercise.displayOrder) {
      setIsEditing(false);
      return;
    }

    setError(null);
    startTransition(async () => {
      const result = await updateExerciseFields(exercise.id, { displayOrder: newOrder });
      setError(result.error);
      if (!result.error) setIsEditing(false);
    });
  };

  return (
    <div className="flex items-center gap-4 rounded-mani-md bg-mani-bg-card p-3">
      <div className="w-8 flex-shrink-0 text-center">
        <Badge variant="neutral">{position}</Badge>
      </div>

      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-medium">{exercise.title}</div>
        <div className="truncate text-xs text-mani-text-muted">{exercise.description}</div>
      </div>

      <div className="flex flex-shrink-0 items-center justify-end gap-2">
        <Link href={`/admin/exercises/${exercise.id}`} className={SECONDARY_BUTTON}>
          {STRINGS.editButton}
        </Link>

        {isEditing ? (
          <>
            <input
              type="number"
              value={orderValue}
              onChange={(e) => setOrderValue(e.target.value)}
              className="w-16 rounded-mani-md border border-mani-border bg-mani-bg-card px-2 py-1 text-sm text-mani-text"
              min="0"
              disabled={isPending}
            />
            <button onClick={handleUpdateOrder} disabled={isPending} className={SECONDARY_BUTTON}>
              {STRINGS.saveButton}
            </button>
            <button
              onClick={() => {
                setIsEditing(false);
                setOrderValue(exercise.displayOrder.toString());
              }}
              disabled={isPending}
              className={SECONDARY_BUTTON}
            >
              {STRINGS.cancelButton}
            </button>
          </>
        ) : (
          <>
            <button
              onClick={() => setIsEditing(true)}
              disabled={isPending}
              title="Edit display order"
              className={SECONDARY_BUTTON}
            >
              {STRINGS.orderPrefix}
              {exercise.displayOrder}
            </button>
            <button onClick={handleRemove} disabled={isPending} className={DANGER_BUTTON}>
              {STRINGS.deleteButton}
            </button>
          </>
        )}
      </div>

      {error && <span className="text-sm text-mani-error">{error}</span>}
      {isPending && <span className="text-sm text-mani-text-muted">{dictionary.admin.pages.saving}</span>}
    </div>
  );
}
