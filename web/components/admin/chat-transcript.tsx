// ABOUTME: Renders a chat thread's messages as a bubble transcript, user right / Mani left.
// ABOUTME: Ported from mani-app's app/admin/chats/[id]/ChatTranscript.tsx, restyled to Tailwind.

import type { AdminMessage } from "@/types";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.chats;

interface ChatTranscriptProps {
  messages: AdminMessage[];
}

export function ChatTranscript({ messages }: ChatTranscriptProps) {
  if (messages.length === 0) {
    return <div className="py-12 text-center text-mani-text-muted">{STRINGS.emptyTranscript}</div>;
  }

  return (
    <div className="space-y-6 py-6" role="log" aria-label="Conversation transcript">
      {messages.map((message) => {
        const isUser = message.role === "user";
        return (
          <article
            key={message.id}
            className={`flex ${isUser ? "justify-end" : "justify-start"}`}
            aria-label={`Message from ${isUser ? "user" : "Mani"}`}
          >
            <div
              className={`max-w-[75%] rounded-2xl px-4 py-3 text-mani-text ${
                isUser ? "rounded-br-md bg-mani-accent-light" : "rounded-bl-md bg-mani-bg"
              }`}
            >
              <div className={`mb-1 text-xs font-medium ${isUser ? "text-mani-accent" : "text-mani-text-muted"}`}>
                {isUser ? STRINGS.roleUser : STRINGS.roleMani}
              </div>
              <div className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</div>
              <div className="mt-2 text-xs text-mani-text-light">{formatMessageTime(message.createdAt)}</div>
            </div>
          </article>
        );
      })}
    </div>
  );
}

function formatMessageTime(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}
