// ABOUTME: Maps the chat API's wire shapes to the UI's Message and ThreadListItem, and reads a failed call's
// ABOUTME: user-facing sentence. Pure, so the chat state and its tests share one translation.

import type { Message, SmartPrompt, ThreadListItem } from '@/types/chat';
import { ApiError } from '@/lib/api/api-error';
import type { MessageOut, PromptOut, ThreadOut, TurnOut } from '@/types/chat-api';

function toPrompt(prompt: PromptOut): SmartPrompt {
  return {
    label: prompt.label,
    library: prompt.library ?? undefined,
    technique: prompt.technique ?? undefined,
    decline: prompt.decline ?? undefined,
  };
}

export function messageFromWire(message: MessageOut): Message {
  return {
    id: message.id,
    threadId: message.thread_id,
    role: message.role,
    content: message.content,
    createdAt: message.created_at,
    promptOptions: message.prompts?.map(toPrompt) ?? [],
  };
}

/** A thread's messages oldest first; the messages route sends them newest first. */
export function messagesFromWire(newestFirst: MessageOut[]): Message[] {
  return [...newestFirst].reverse().map(messageFromWire);
}

export function messageFromTurn(turn: TurnOut, threadId: string, fallbackId: string): Message {
  return {
    id: turn.id ?? fallbackId,
    threadId,
    role: 'mani',
    content: turn.content,
    createdAt: turn.created_at ?? new Date().toISOString(),
    promptOptions: turn.prompts?.map(toPrompt) ?? [],
  };
}

export function threadFromWire(thread: ThreadOut): ThreadListItem {
  return { id: thread.id, title: thread.title ?? null, lastMessageAt: thread.last_message_at };
}

/** The backend's sentence for a failed call, or null when the failure carried none (a network error). */
export function errorText(error: unknown): string | null {
  return error instanceof ApiError ? error.userMessage : null;
}
