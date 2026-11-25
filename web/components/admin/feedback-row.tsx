// ABOUTME: One rating in the admin Feedback table — who, which exercise, the rating and its reason.
// ABOUTME: The category shows its dictionary label when it has one.

import { Badge, TableCell } from "@/components/shared";
import type { ExerciseFeedback } from "@/types";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.feedback;
const CATEGORY_LABELS: Record<string, string> = dictionary.admin.forms.categories;

interface FeedbackRowProps {
  entry: ExerciseFeedback;
}

export function FeedbackRow({ entry }: FeedbackRowProps) {
  return (
    <tr className="transition-colors duration-150 hover:bg-mani-bg">
      <TableCell className="max-w-xs truncate text-sm text-mani-text">
        {entry.userEmail ?? `${entry.userId.slice(0, 8)}...`}
      </TableCell>
      <TableCell>
        <div className="text-sm font-medium text-mani-text">{entry.exerciseTitle}</div>
        <p className="mt-0.5 text-sm text-mani-text-muted">{CATEGORY_LABELS[entry.category] ?? entry.category}</p>
      </TableCell>
      <TableCell>
        <Badge variant={entry.rating === "up" ? "success" : "neutral"}>
          {entry.rating === "up" ? STRINGS.ratingUp : STRINGS.ratingDown}
        </Badge>
      </TableCell>
      <TableCell className="text-sm text-mani-text-muted">{entry.reason ?? STRINGS.noReason}</TableCell>
      <TableCell className="text-sm whitespace-nowrap text-mani-text-muted">
        {new Date(entry.updatedAt).toLocaleDateString()}
      </TableCell>
    </tr>
  );
}
