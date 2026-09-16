// ABOUTME: Chat UI shapes, mirroring @mani/api's message/prompt schemas by structure only
// ABOUTME: (no zod, no backend import) — this app has no API layer yet, just the UI for it.

export type MessageRole = 'user' | 'mani';

export interface SmartPrompt {
  label: string;
  library?: string;
  technique?: string;
  decline?: boolean;
}

export interface Message {
  id: string;
  threadId: string;
  role: MessageRole;
  content: string;
  createdAt: string;
  promptOptions?: SmartPrompt[] | null;
  selectedPrompt?: string | null;
}

// Mirrors only the fields the chat UI actually reads from @mani/api's ThreadListItem —
// not the full backend contract, which has several more fields UI components don't use.
export interface ThreadListItem {
  id: string;
  title: string | null;
  preview?: string;
  lastMessageAt: string;
}
