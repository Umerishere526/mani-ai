// ABOUTME: The state of one conversation on screen: its thread, messages, chosen style, and the message in flight
// ABOUTME: or failed. A pure reducer, so the send, reply and retry rules are tested without rendering.

import type { ConversationStyle, Message } from '@/types/chat';

export interface PendingSend {
  content: string;
  /** Also the user message's id: the backend returns the original reply when a send with it is retried. */
  clientMessageId: string;
}

export interface ChatState {
  threadId: string | null;
  style: ConversationStyle | null;
  messages: Message[];
  sending: PendingSend | null;
  failed: (PendingSend & { error: string | null }) | null;
}

export type ChatAction =
  | { type: 'reset'; threadId: string | null }
  | { type: 'loaded'; threadId: string; messages: Message[] }
  | { type: 'styleChosen'; style: ConversationStyle; opener: Message | null }
  | { type: 'sendStarted'; pending: PendingSend; message: Message }
  | { type: 'retryStarted' }
  | { type: 'replied'; clientMessageId: string; threadId: string; reply: Message }
  | { type: 'sendFailed'; clientMessageId: string; error: string | null };

export function initialChatState(threadId: string | null): ChatState {
  return { threadId, style: null, messages: [], sending: null, failed: null };
}

/** Whether the conversation is under way, or still waiting for the person to pick a style. */
export function hasStarted(state: ChatState): boolean {
  return state.threadId !== null || state.style !== null;
}

export function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case 'reset':
      return initialChatState(action.threadId);
    case 'loaded':
      return action.threadId === state.threadId ? { ...state, messages: action.messages } : state;
    case 'styleChosen':
      return { ...state, style: action.style, messages: action.opener ? [...state.messages, action.opener] : state.messages };
    case 'sendStarted': {
      if (state.sending) return state;
      // Writing something else instead of retrying sets the failed message aside.
      const kept = state.messages.filter((m) => m.id !== state.failed?.clientMessageId);
      return { ...state, sending: action.pending, failed: null, messages: [...kept, action.message] };
    }
    case 'retryStarted':
      if (!state.failed) return state;
      return { ...state, sending: { content: state.failed.content, clientMessageId: state.failed.clientMessageId }, failed: null };
    case 'replied':
      // A reply for a send this screen no longer waits on (the person started a new chat meanwhile) is dropped.
      if (state.sending?.clientMessageId !== action.clientMessageId) return state;
      return { ...state, threadId: action.threadId, sending: null, messages: [...state.messages, action.reply] };
    case 'sendFailed':
      if (!state.sending || state.sending.clientMessageId !== action.clientMessageId) return state;
      return { ...state, sending: null, failed: { ...state.sending, error: action.error } };
  }
}
