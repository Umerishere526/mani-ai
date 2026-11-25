// ABOUTME: Sends the person's messages: starts the thread with the first one, retries a failed one with the same
// ABOUTME: client id (the backend answers a repeat with the original reply), and asks for a reply's follow-up work.

import type { Dispatch } from 'react';
import { randomUUID } from 'expo-crypto';
import { followUp, sendMessage, startThread } from '@/lib/api/threads';
import { errorText, messageFromTurn, type ChatAction, type ChatState, type PendingSend } from '@/lib/chat';
import type { TurnOut } from '@/types/chat-api';

export function useChatSend(state: ChatState, dispatch: Dispatch<ChatAction>, onTurn?: (turn: TurnOut) => void) {
  const deliver = async ({ content, clientMessageId }: PendingSend) => {
    const body = { content, client_message_id: clientMessageId };
    try {
      let threadId = state.threadId;
      let turn: TurnOut;
      if (threadId) {
        turn = await sendMessage(threadId, body);
      } else {
        const started = await startThread({ ...body, style: state.style });
        threadId = started.thread.id;
        turn = started.turn;
      }
      dispatch({ type: 'replied', clientMessageId, threadId, reply: messageFromTurn(turn, threadId, randomUUID()) });
      onTurn?.(turn);
      if (turn.follow_up_pending && turn.id) {
        // Fire and forget: work that fails stays pending on the backend and runs on the next request.
        followUp(threadId, turn.id).catch(() => undefined);
      }
    } catch (error) {
      dispatch({ type: 'sendFailed', clientMessageId, error: errorText(error) });
    }
  };

  const send = (content: string) => {
    const trimmed = content.trim();
    if (!trimmed || state.sending) return;
    const pending = { content: trimmed, clientMessageId: randomUUID() };
    const message = {
      id: pending.clientMessageId,
      threadId: state.threadId ?? '',
      role: 'user' as const,
      content: trimmed,
      createdAt: new Date().toISOString(),
    };
    dispatch({ type: 'sendStarted', pending, message });
    void deliver(pending);
  };

  const retry = () => {
    if (!state.failed) return;
    const { content, clientMessageId } = state.failed;
    dispatch({ type: 'retryStarted' });
    void deliver({ content, clientMessageId });
  };

  return { send, retry };
}
