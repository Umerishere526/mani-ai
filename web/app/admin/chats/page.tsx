// ABOUTME: Admin Chats list — searchable list of conversations, most recently active first, a page at a time.
// ABOUTME: Reads from the backend; ?search filters by email or id and ?cursor moves to older conversations.

import Link from "next/link";
import { EmptyState, PageHeader, SearchForm, TableCard, TableHeadCell } from "@/components/shared";
import { ThreadRow } from "@/components/admin/thread-row";
import { listThreads } from "@/lib/api/threads";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.chats;

export default async function ChatsPage({ searchParams }: PageProps<"/admin/chats">) {
  const { search, cursor } = await searchParams;
  const term = typeof search === "string" ? search : undefined;
  const page = await listThreads(term, typeof cursor === "string" ? cursor : undefined);
  const olderQuery = new URLSearchParams({ ...(term ? { search: term } : {}), cursor: page.nextCursor ?? "" });

  return (
    <div>
      <PageHeader title={STRINGS.title} />
      <p className="mb-6 text-sm text-mani-text-muted">{STRINGS.description}</p>

      <div className="mb-6">
        <SearchForm basePath="/admin/chats" placeholder={STRINGS.searchPlaceholder} initialSearch={term} />
      </div>

      {page.threads.length === 0 ? (
        <EmptyState message={term ? STRINGS.emptySearch.replace("{search}", term) : STRINGS.empty} />
      ) : (
        <TableCard>
          <thead>
            <tr>
              <TableHeadCell>{STRINGS.colUser}</TableHeadCell>
              <TableHeadCell>{STRINGS.colTitle}</TableHeadCell>
              <TableHeadCell>{STRINGS.colMessages}</TableHeadCell>
              <TableHeadCell>{STRINGS.colLastActivity}</TableHeadCell>
              <TableHeadCell>{STRINGS.colStatus}</TableHeadCell>
              <TableHeadCell align="right">{STRINGS.colActions}</TableHeadCell>
            </tr>
          </thead>
          <tbody>
            {page.threads.map((thread) => (
              <ThreadRow key={thread.id} thread={thread} />
            ))}
          </tbody>
        </TableCard>
      )}

      {page.nextCursor && (
        <div className="mt-6 text-right">
          <Link href={`/admin/chats?${olderQuery.toString()}`} className="text-sm font-medium">
            {STRINGS.olderLink}
          </Link>
        </div>
      )}
    </div>
  );
}
