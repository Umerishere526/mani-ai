// ABOUTME: One category's library exercises on the admin Exercises page: heading, count and table.
// ABOUTME: Row actions edit, activate or deactivate, and delete through server actions.

import Link from "next/link";
import { Badge, TableCard, TableCell, TableHeadCell } from "@/components/shared";
import { ExerciseActions } from "./exercise-actions";
import type { AdminExercise } from "@/types";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.exercises;
const COMMON = dictionary.admin.pages;
const CATEGORY_LABELS: Record<string, string> = dictionary.admin.forms.categories;

interface ExerciseCategoryTableProps {
  category: string;
  exercises: AdminExercise[];
}

export function ExerciseCategoryTable({ category, exercises }: ExerciseCategoryTableProps) {
  return (
    <section>
      <h3 className="mb-3 font-medium text-mani-text">{CATEGORY_LABELS[category] ?? category}</h3>
      <p className="mb-4 text-sm text-mani-text-muted">
        {exercises.length} {exercises.length !== 1 ? STRINGS.exerciseCountPlural : STRINGS.exerciseCountSingular}
      </p>
      <TableCard>
        <thead>
          <tr>
            <TableHeadCell>{STRINGS.colTitle}</TableHeadCell>
            <TableHeadCell>{STRINGS.colDuration}</TableHeadCell>
            <TableHeadCell>{STRINGS.colOrder}</TableHeadCell>
            <TableHeadCell>{STRINGS.colStatus}</TableHeadCell>
            <TableHeadCell align="right">{STRINGS.colActions}</TableHeadCell>
          </tr>
        </thead>
        <tbody>
          {exercises.map((exercise) => (
            <tr key={exercise.id} className="transition-colors duration-150 hover:bg-mani-bg">
              <TableCell>
                <Link href={`/admin/exercises/${exercise.id}`} className="font-medium">
                  {exercise.title}
                </Link>
                {exercise.description && (
                  <p className="mt-0.5 max-w-xs truncate text-sm text-mani-text-muted">{exercise.description}</p>
                )}
              </TableCell>
              <TableCell className="text-sm text-mani-text">
                {exercise.durationMinutes === null ? COMMON.unknown : `${exercise.durationMinutes}${STRINGS.minutesSuffix}`}
              </TableCell>
              <TableCell className="text-sm text-mani-text-muted">{exercise.displayOrder}</TableCell>
              <TableCell>
                <Badge variant={exercise.isActive ? "success" : "neutral"}>
                  {exercise.isActive ? COMMON.active : COMMON.inactive}
                </Badge>
              </TableCell>
              <TableCell className="text-right">
                <ExerciseActions exercise={exercise} />
              </TableCell>
            </tr>
          ))}
        </tbody>
      </TableCard>
    </section>
  );
}
