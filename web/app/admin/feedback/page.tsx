// ABOUTME: Admin Feedback — people's helpful / not helpful ratings of library exercises, newest first.
// ABOUTME: Reads from the backend on each request; ?search filters by part of an email.

import { EmptyState, PageHeader, SearchForm, TableCard, TableHeadCell } from "@/components/shared";
import { FeedbackRow } from "@/components/admin/feedback-row";
import { listExerciseFeedback } from "@/lib/api/exercise-feedback";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.feedback;

export default async function FeedbackPage({ searchParams }: PageProps<"/admin/feedback">) {
  const { search } = await searchParams;
  const term = typeof search === "string" ? search : undefined;
  const feedback = await listExerciseFeedback(term);

  return (
    <div>
      <PageHeader title={STRINGS.title} />
      <p className="mb-6 text-sm text-mani-text-muted">{STRINGS.description}</p>

      <div className="mb-6">
        <SearchForm basePath="/admin/feedback" placeholder={STRINGS.searchPlaceholder} initialSearch={term} />
      </div>

      {feedback.length === 0 ? (
        <EmptyState message={term ? STRINGS.emptySearch.replace("{search}", term) : STRINGS.empty} />
      ) : (
        <TableCard>
          <thead>
            <tr>
              <TableHeadCell>{STRINGS.colUser}</TableHeadCell>
              <TableHeadCell>{STRINGS.colExercise}</TableHeadCell>
              <TableHeadCell>{STRINGS.colRating}</TableHeadCell>
              <TableHeadCell>{STRINGS.colReason}</TableHeadCell>
              <TableHeadCell>{STRINGS.colUpdated}</TableHeadCell>
            </tr>
          </thead>
          <tbody>
            {feedback.map((entry) => (
              <FeedbackRow key={`${entry.userId}-${entry.exerciseId}`} entry={entry} />
            ))}
          </tbody>
        </TableCard>
      )}
    </div>
  );
}
