// ABOUTME: The chat routes: the opening, starting a thread with its first message, sending, the follow-up after a
// ABOUTME: reply, and reading threads and their messages.

import type {
  MessageListOut,
  OpeningOut,
  SendMessageIn,
  ThreadListOut,
  ThreadStartedOut,
  ThreadStartIn,
  TurnOut,
} from '@/types/chat-api';
import { api } from './index';

// A turn waits on the model, and provider slowdowns have run 20 to 27 s (REL-2); the client's 15 s default would
// abandon replies the backend still delivers. A retry reuses the client message id, so it never pays twice.
export const TURN_TIMEOUT_MS = 60_000;

export function getOpening(): Promise<OpeningOut> {
  return api.request<OpeningOut>('GET', '/v1/threads/opening');
}

export function startThread(body: ThreadStartIn): Promise<ThreadStartedOut> {
  return api.request<ThreadStartedOut>('POST', '/v1/threads', { body, timeoutMs: TURN_TIMEOUT_MS });
}

export function sendMessage(threadId: string, body: SendMessageIn): Promise<TurnOut> {
  return api.request<TurnOut>('POST', `/v1/threads/${threadId}/messages`, { body, timeoutMs: TURN_TIMEOUT_MS });
}

export function followUp(threadId: string, messageId: string): Promise<unknown> {
  return api.request('POST', `/v1/threads/${threadId}/messages/${messageId}/follow-up`, { timeoutMs: TURN_TIMEOUT_MS });
}

export function listThreads(): Promise<ThreadListOut> {
  return api.request<ThreadListOut>('GET', '/v1/threads');
}

/** Newest first. */
export function getMessages(threadId: string): Promise<MessageListOut> {
  return api.request<MessageListOut>('GET', `/v1/threads/${threadId}/messages`);
}
