// ABOUTME: Tests the conversation state's send, reply, failure and retry rules with real messages and wire shapes,
// ABOUTME: including that a reply for a send the screen no longer waits on never lands in another conversation.

import type { Message } from '@/types/chat';
import type { MessageOut } from '@/types/chat-api';
import { chatReducer, hasStarted, initialChatState, type ChatState } from './chat-reducer';
import { messagesFromWire } from './to-ui';

function userMessage(id: string, content: string): Message {
  return { id, threadId: '', role: 'user', content, createdAt: '2026-11-25T10:00:00Z' };
}

function maniMessage(id: string, content: string): Message {
  return { id, threadId: 'thread-1', role: 'mani', content, createdAt: '2026-11-25T10:00:05Z' };
}

function sending(state: ChatState, id: string, content: string): ChatState {
  return chatReducer(state, {
    type: 'sendStarted',
    pending: { content, clientMessageId: id },
    message: userMessage(id, content),
  });
}

describe('chatReducer', () => {
  it('starts the conversation once a style is chosen and adopts the thread the first reply created', () => {
    const picked = chatReducer(initialChatState(null), {
      type: 'styleChosen',
      style: 'supportive',
      opener: maniMessage('opener', 'How can I support you today?'),
    });
    expect(hasStarted(picked)).toBe(true);

    const replied = chatReducer(sending(picked, 'c1', 'Work is a lot'), {
      type: 'replied',
      clientMessageId: 'c1',
      threadId: 'thread-1',
      reply: maniMessage('m1', 'Tell me more.'),
    });
    expect(replied.threadId).toBe('thread-1');
    expect(replied.sending).toBeNull();
    expect(replied.messages.map((m) => m.content)).toEqual(['How can I support you today?', 'Work is a lot', 'Tell me more.']);
  });

  it('drops a reply that arrives after the person started a new chat', () => {
    const inFlight = sending(initialChatState('thread-1'), 'c1', 'Hello');
    const fresh = chatReducer(inFlight, { type: 'reset', threadId: null });
    const late = chatReducer(fresh, {
      type: 'replied',
      clientMessageId: 'c1',
      threadId: 'thread-1',
      reply: maniMessage('m1', 'Hi'),
    });
    expect(late).toEqual(initialChatState(null));
  });

  it('keeps a failed message with its client id, and a retry sends that same id again', () => {
    const failed = chatReducer(sending(initialChatState('thread-1'), 'c1', 'Hello'), {
      type: 'sendFailed',
      clientMessageId: 'c1',
      error: 'Something went wrong. Please try again.',
    });
    expect(failed.failed).toEqual({ content: 'Hello', clientMessageId: 'c1', error: 'Something went wrong. Please try again.' });
    expect(failed.messages).toHaveLength(1);

    const retrying = chatReducer(failed, { type: 'retryStarted' });
    expect(retrying.sending).toEqual({ content: 'Hello', clientMessageId: 'c1' });
    expect(retrying.failed).toBeNull();
    expect(retrying.messages).toHaveLength(1);
  });

  it('sets a failed message aside when the person writes something else instead', () => {
    const failed = chatReducer(sending(initialChatState('thread-1'), 'c1', 'Hello'), {
      type: 'sendFailed',
      clientMessageId: 'c1',
      error: null,
    });
    const next = sending(failed, 'c2', 'Never mind, something else');
    expect(next.failed).toBeNull();
    expect(next.messages.map((m) => m.id)).toEqual(['c2']);
  });
});

describe('messagesFromWire', () => {
  it('puts the newest-first page in reading order and keeps the buttons', () => {
    const page: MessageOut[] = [
      {
        id: 'm2',
        thread_id: 't',
        role: 'mani',
        content: 'Want to try something?',
        prompts: [{ label: 'Visit library', library: 'home', technique: null, decline: null }],
        created_at: '2026-11-25T10:00:05Z',
      },
      { id: 'm1', thread_id: 't', role: 'user', content: 'Hi', created_at: '2026-11-25T10:00:00Z' },
    ];
    const messages = messagesFromWire(page);
    expect(messages.map((m) => m.id)).toEqual(['m1', 'm2']);
    expect(messages[1].promptOptions).toEqual([{ label: 'Visit library', library: 'home', technique: undefined, decline: undefined }]);
  });
});
