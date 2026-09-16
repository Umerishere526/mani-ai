// ABOUTME: Placeholder chat thread and message data standing in for the FastAPI chats
// ABOUTME: endpoints, which don't exist yet — replace with a real fetch once the backend lands.

import type { AdminThread, AdminMessage } from "@/types";

export const ADMIN_THREADS: AdminThread[] = [
  {
    id: "thread-1",
    userId: "user-aaaa-1111",
    userEmail: "jordan.lee@example.com",
    userNickname: "Jordan",
    title: "Feeling overwhelmed at work",
    createdAt: "2026-09-10T14:00:00.000Z",
    lastMessageAt: "2026-09-10T14:22:00.000Z",
    messageCount: 8,
    crisisDetected: false,
  },
  {
    id: "thread-2",
    userId: "user-bbbb-2222",
    userEmail: "sam.rivera@example.com",
    userNickname: null,
    title: "Setting a boundary with a parent",
    createdAt: "2026-09-08T09:15:00.000Z",
    lastMessageAt: "2026-09-08T09:48:00.000Z",
    messageCount: 14,
    crisisDetected: false,
  },
  {
    id: "thread-3",
    userId: "user-cccc-3333",
    userEmail: "morgan.chen@example.com",
    userNickname: "Morgan",
    title: null,
    createdAt: "2026-09-12T22:05:00.000Z",
    lastMessageAt: "2026-09-12T22:31:00.000Z",
    messageCount: 6,
    crisisDetected: true,
  },
];

export const ADMIN_MESSAGES: Record<string, AdminMessage[]> = {
  "thread-1": [
    {
      id: "msg-1-1",
      role: "user",
      content: "I've had back to back meetings all week and I'm exhausted.",
      createdAt: "2026-09-10T14:00:00.000Z",
    },
    {
      id: "msg-1-2",
      role: "mani",
      content: "That sounds draining. What's been the hardest part of the week for you?",
      createdAt: "2026-09-10T14:01:00.000Z",
    },
    {
      id: "msg-1-3",
      role: "user",
      content: "Feeling like I can't say no to anything.",
      createdAt: "2026-09-10T14:03:00.000Z",
    },
  ],
  "thread-2": [
    {
      id: "msg-2-1",
      role: "user",
      content: "My mom keeps calling multiple times a day and I don't know how to ask her to stop.",
      createdAt: "2026-09-08T09:15:00.000Z",
    },
    {
      id: "msg-2-2",
      role: "mani",
      content: "It sounds like you want more space without damaging the relationship. What would a boundary look like for you here?",
      createdAt: "2026-09-08T09:17:00.000Z",
    },
  ],
  "thread-3": [
    {
      id: "msg-3-1",
      role: "user",
      content: "I don't see the point in any of this anymore.",
      createdAt: "2026-09-12T22:05:00.000Z",
    },
    {
      id: "msg-3-2",
      role: "mani",
      content: "I'm really glad you told me. You don't have to go through this alone — can we talk about what's happening right now?",
      createdAt: "2026-09-12T22:06:00.000Z",
    },
  ],
};

export function getThreadById(id: string): AdminThread | undefined {
  return ADMIN_THREADS.find((thread) => thread.id === id);
}

export function getThreadMessages(threadId: string): AdminMessage[] {
  return ADMIN_MESSAGES[threadId] ?? [];
}

export function searchThreads(search?: string): AdminThread[] {
  if (!search) return ADMIN_THREADS;
  const searchLower = search.toLowerCase();
  return ADMIN_THREADS.filter(
    (thread) =>
      thread.userEmail?.toLowerCase().includes(searchLower) ||
      thread.userId.toLowerCase().includes(searchLower),
  );
}
