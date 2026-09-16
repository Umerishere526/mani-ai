// ABOUTME: Types for the admin Chats section — user conversation threads and messages.
// ABOUTME: Ported from mani-app's AdminThreadWithUser/AdminMessage shapes (admin/actions.ts).

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
