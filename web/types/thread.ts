// ABOUTME: Types for the admin Chats section — user conversation threads and messages.
// ABOUTME: The shapes the backend's /v1/admin/threads endpoints return, in camelCase.

export interface AdminThread {
  id: string;
  userId: string;
  userEmail: string | null;
  userNickname: string | null;
  title: string | null;
  createdAt: string;
  lastMessageAt: string;
  messageCount: number;
  crisisDetected: boolean;
}

export interface AdminMessage {
  id: string;
  role: "user" | "mani";
  content: string;
  createdAt: string;
}

export interface AdminThreadPage {
  threads: AdminThread[];
  nextCursor: string | null;
}
