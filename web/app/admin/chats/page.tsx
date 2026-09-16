// ABOUTME: Admin Chats list — searchable, paginated list of user conversation threads.
// ABOUTME: Ported from mani-app's app/admin/chats/page.tsx.

import Link from "next/link";
import { Badge, EmptyState } from "@/components/shared";
import { ChatSearchForm } from "@/components/admin/chat-search-form";
import { searchThreads } from "@/lib/placeholder-threads";
import { formatRelativeTime } from "@/lib/utils";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.chats;

interface ChatsPageProps {
  searchParams: Promise<{ search?: string; cursor?: string }>;
}

export default async function ChatsPage({ searchParams }: ChatsPageProps) {
  const { search } = await searchParams;
  const threads = searchThreads(search);

  return (
    <div>
      <div className="mb-8 flex items-center justify-between">
        <h1 className="text-[1.75rem] font-semibold tracking-tight text-mani-text">{STRINGS.title}</h1>
      </div>

      <p className="mb-6 text-sm text-mani-text-muted">{STRINGS.description}</p>

      <div className="mb-6">
        <ChatSearchForm initialSearch={search} />
      </div>

      {threads.length === 0 ? (
        <EmptyState message={search ? STRINGS.emptySearch.replace("{search}", search) : STRINGS.empty} />
      ) : (
        <div className="overflow-hidden rounded-mani-lg bg-mani-bg-card shadow-mani-card">
          <table className="w-full border-collapse">
            <thead className="bg-mani-bg">
              <tr>
                <th className="border-b border-mani-border px-6 py-3.5 text-left text-[0.6875rem] font-semibold uppercase tracking-wide text-mani-text-muted">
                  {STRINGS.colUser}
                </th>
                <th className="border-b border-mani-border px-6 py-3.5 text-left text-[0.6875rem] font-semibold uppercase tracking-wide text-mani-text-muted">
                  {STRINGS.colTitle}
                </th>
                <th className="border-b border-mani-border px-6 py-3.5 text-left text-[0.6875rem] font-semibold uppercase tracking-wide text-mani-text-muted">
                  {STRINGS.colMessages}
                </th>
                <th className="border-b border-mani-border px-6 py-3.5 text-left text-[0.6875rem] font-semibold uppercase tracking-wide text-mani-text-muted">
                  {STRINGS.colLastActivity}
                </th>
                <th className="border-b border-mani-border px-6 py-3.5 text-left text-[0.6875rem] font-semibold uppercase tracking-wide text-mani-text-muted">
                  {STRINGS.colStatus}
                </th>
                <th className="border-b border-mani-border px-6 py-3.5 text-right text-[0.6875rem] font-semibold uppercase tracking-wide text-mani-text-muted">
                  {STRINGS.colActions}
                </th>
              </tr>
            </thead>
            <tbody>
              {threads.map((thread) => (
                <tr key={thread.id} className="transition-colors duration-150 hover:bg-mani-bg">
                  <td className="border-b border-mani-border px-6 py-4 last:border-b-0">
                    <div className="font-medium">{thread.userNickname ?? STRINGS.anonymous}</div>
                    <p className="mt-0.5 max-w-xs truncate text-sm text-mani-text-muted">
                      {thread.userEmail ?? `${thread.userId.slice(0, 8)}...`}
                    </p>
                  </td>
                  <td className="border-b border-mani-border px-6 py-4 text-sm text-mani-text last:border-b-0">
                    {thread.title ?? STRINGS.untitledShort}
                  </td>
                  <td className="border-b border-mani-border px-6 py-4 text-sm text-mani-text-muted last:border-b-0">
                    {thread.messageCount}
                  </td>
                  <td className="border-b border-mani-border px-6 py-4 text-sm text-mani-text-muted last:border-b-0">
                    {formatRelativeTime(thread.lastMessageAt, {
                      justNow: STRINGS.justNow,
                      minutesAgoSuffix: STRINGS.minutesAgoSuffix,
                      hoursAgoSuffix: STRINGS.hoursAgoSuffix,
                      daysAgoSuffix: STRINGS.daysAgoSuffix,
                    })}
                  </td>
                  <td className="border-b border-mani-border px-6 py-4 last:border-b-0">
                    {thread.crisisDetected ? (
                      <Badge variant="accent">{STRINGS.statusCrisis}</Badge>
                    ) : (
                      <Badge variant="success">{STRINGS.statusNormal}</Badge>
                    )}
                  </td>
                  <td className="border-b border-mani-border px-6 py-4 text-right last:border-b-0">
                    <Link
                      href={`/admin/chats/${thread.id}`}
                      className="text-sm font-medium text-mani-accent transition-colors duration-150 hover:text-mani-accent-hover"
                    >
                      {STRINGS.viewLink}
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
