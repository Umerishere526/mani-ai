// ABOUTME: Admin Crisis events — every crisis no admin has resolved yet, newest first, each with a resolve form.
// ABOUTME: Reads from the backend on each request; the conversation link opens the logged transcript.

import { ActionLink, EmptyState, PageHeader, TableCard, TableCell, TableHeadCell } from "@/components/shared";
import { ResolveCrisisForm } from "@/components/admin/resolve-crisis-form";
import { listUnresolvedCrisisEvents } from "@/lib/api/crisis-events";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.crisisEvents;

export default async function CrisisEventsPage() {
  const events = await listUnresolvedCrisisEvents();

  return (
    <div>
      <PageHeader title={STRINGS.title} />
      <p className="mb-6 text-sm text-mani-text-muted">{STRINGS.description}</p>

      {events.length === 0 ? (
        <EmptyState message={STRINGS.empty} />
      ) : (
        <TableCard>
          <thead>
            <tr>
              <TableHeadCell>{STRINGS.colDetected}</TableHeadCell>
              <TableHeadCell>{STRINGS.colReason}</TableHeadCell>
              <TableHeadCell>{STRINGS.colConversation}</TableHeadCell>
              <TableHeadCell align="right">{STRINGS.colResolve}</TableHeadCell>
            </tr>
          </thead>
          <tbody>
            {events.map((event) => (
              <tr key={event.id}>
                <TableCell className="text-sm whitespace-nowrap text-mani-text">
                  {new Date(event.detectedAt).toLocaleString()}
                </TableCell>
                <TableCell className="text-sm text-mani-text">{event.reason}</TableCell>
                <TableCell>
                  <ActionLink href={`/admin/chats/${event.threadId}`}>{STRINGS.viewConversation}</ActionLink>
                </TableCell>
                <TableCell className="text-right">
                  <ResolveCrisisForm eventId={event.id} />
                </TableCell>
              </tr>
            ))}
          </tbody>
        </TableCard>
      )}
    </div>
  );
}
