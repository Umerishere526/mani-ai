// ABOUTME: Admin page showing one chat thread's header info and full transcript.
// ABOUTME: Ported from mani-app's app/admin/chats/[id]/page.tsx.

import { notFound } from "next/navigation";
import { BackLink, Badge } from "@/components/shared";
import { ChatTranscript } from "@/components/admin/chat-transcript";
import { getThreadById, getThreadMessages } from "@/lib/placeholder-threads";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.chats;

interface ChatDetailPageProps {
  params: Promise<{ id: string }>;
}

export default async function ChatDetailPage({ params }: ChatDetailPageProps) {
  const { id } = await params;
  const thread = getThreadById(id);
  const messages = getThreadMessages(id);

  if (!thread) {
    notFound();
  }

  return (
    <div>
      <BackLink href="/admin/chats">{STRINGS.backToChats}</BackLink>

      <div className="rounded-mani-lg bg-mani-bg-card p-8 shadow-mani-card">
        <div className="mb-8 flex items-start justify-between">
          <div>
            <h1 className="text-[1.75rem] font-semibold tracking-tight text-mani-text">
              {thread.title ?? STRINGS.untitled}
            </h1>
            <div className="mt-2 flex items-center gap-4">
              <p className="text-sm text-mani-text-muted">
                {STRINGS.userPrefix}
                {thread.userNickname ?? STRINGS.anonymous} ({thread.userEmail ?? thread.userId})
              </p>
              <span className="text-mani-border">|</span>
              <p className="text-sm text-mani-text-muted">
                {thread.messageCount}
                {STRINGS.messageCountSuffix}
              </p>
              <span className="text-mani-border">|</span>
              <p className="text-sm text-mani-text-muted">
                {STRINGS.startedPrefix}
                {new Date(thread.createdAt).toLocaleDateString()}
              </p>
            </div>
          </div>
          {thread.crisisDetected && <Badge variant="accent">{STRINGS.crisisDetected}</Badge>}
        </div>

        <div className="border-t border-mani-border">
          <ChatTranscript messages={messages} />
        </div>
      </div>
    </div>
  );
}
