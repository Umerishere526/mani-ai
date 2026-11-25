// ABOUTME: Chat UI shapes the screens render, mapped from the backend's wire shapes in lib/chat.
// ABOUTME: camelCase and only what the UI reads; the wire's own types live in lib/chat/api-types.ts.

export type MessageRole = 'user' | 'mani';

export type ConversationStyle = 'directive' | 'supportive' | 'reflective';

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
}

export interface ThreadListItem {
  id: string;
  title: string | null;
  lastMessageAt: string;
}
