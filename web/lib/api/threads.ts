// ABOUTME: Reads conversations and transcripts from the backend for the admin Chats pages.
// ABOUTME: Each transcript read is logged by the backend (admin.thread_reads).

import type { AdminMessage, AdminThread, AdminThreadPage } from "@/types";
import { adminFetch, adminFetchOrNull } from "./admin-fetch";

interface ThreadRecord {
  id: string;
  user_id: string;
  user_email?: string | null;
  user_nickname?: string | null;
  title?: string | null;
  message_count?: number | null;
  crisis_detected?: boolean | null;
  created_at: string;
  last_message_at: string;
}

interface MessageRecord {
  id: string;
  role: "user" | "mani";
  content: string;
  created_at: string;
}

interface ThreadPageRecord {
  threads: ThreadRecord[];
  next_cursor?: string | null;
}

interface TranscriptRecord {
  thread: ThreadRecord;
  messages: MessageRecord[];
}

export interface Transcript {
  thread: AdminThread;
  messages: AdminMessage[];
}

function toThread(record: ThreadRecord): AdminThread {
  return {
    id: record.id,
    userId: record.user_id,
    userEmail: record.user_email ?? null,
    userNickname: record.user_nickname ?? null,
    title: record.title ?? null,
    messageCount: record.message_count ?? 0,
    crisisDetected: record.crisis_detected ?? false,
    createdAt: record.created_at,
    lastMessageAt: record.last_message_at,
  };
}

function toMessage(record: MessageRecord): AdminMessage {
  return { id: record.id, role: record.role, content: record.content, createdAt: record.created_at };
}

export async function listThreads(search?: string, cursor?: string): Promise<AdminThreadPage> {
  const query = new URLSearchParams();
  if (search) query.set("search", search);
  if (cursor) query.set("cursor", cursor);
  const page = await adminFetch<ThreadPageRecord>(`/threads?${query.toString()}`);
  return { threads: page.threads.map(toThread), nextCursor: page.next_cursor ?? null };
}

export async function getTranscript(id: string): Promise<Transcript | null> {
  const record = await adminFetchOrNull<TranscriptRecord>(`/threads/${encodeURIComponent(id)}`);
  if (!record) return null;
  return { thread: toThread(record.thread), messages: record.messages.map(toMessage) };
}
