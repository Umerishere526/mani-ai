// ABOUTME: One conversation against the backend: an existing thread's messages, or the opening (greeting and styles)
// ABOUTME: for a new one, then sending. Reports each reply so the screen can react to a crisis or a pause.

import { useEffect, useReducer } from 'react';
import { randomUUID } from 'expo-crypto';
import { getProfile } from '@/lib/api/profile';
import { getMessages, getOpening } from '@/lib/api/threads';
import { chatReducer, hasStarted, initialChatState, messagesFromWire } from '@/lib/chat';
import type { TurnOut } from '@/types/chat-api';
import type { ConversationStyle } from '@/types/chat';
import { useChatSend } from './useChatSend';
import { useLoad } from './useLoad';

export function useChat(initialThreadId: string | undefined, onTurn?: (turn: TurnOut) => void) {
  const [state, dispatch] = useReducer(chatReducer, initialThreadId ?? null, initialChatState);
  const started = hasStarted(state);

  useEffect(() => {
    dispatch({ type: 'reset', threadId: initialThreadId ?? null });
  }, [initialThreadId]);

  const thread = useLoad(
    initialThreadId ?? null,
    () => getMessages(initialThreadId ?? ''),
    (page) => initialThreadId && dispatch({ type: 'loaded', threadId: initialThreadId, messages: messagesFromWire(page.messages) }),
  );
  const opening = useLoad(started ? null : 'opening', getOpening);
  const profile = useLoad(started ? null : 'opening', getProfile);
  const { send, retry } = useChatSend(state, dispatch, onTurn);

  const chooseStyle = (style: ConversationStyle) => {
    const opener = opening.data?.openers?.[style];
    const message = opener
      ? { id: randomUUID(), threadId: '', role: 'mani' as const, content: opener, createdAt: new Date().toISOString() }
      : null;
    dispatch({ type: 'styleChosen', style, opener: message });
  };

  const startNewThread = () => dispatch({ type: 'reset', threadId: null });

  return {
    state,
    started,
    opening: opening.data,
    defaultStyle: profile.data?.support_style ?? null,
    loadFailed: thread.failed || opening.failed,
    reload: thread.failed ? thread.retry : opening.retry,
    chooseStyle,
    send,
    retry,
    startNewThread,
  };
}
