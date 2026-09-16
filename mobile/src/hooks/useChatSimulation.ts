// ABOUTME: Local stand-in for ChatScreen's tRPC-backed send/receive loop — no backend
// ABOUTME: exists yet, so this simulates latency, canned replies, and crisis detection.

import { useCallback, useRef, useState } from 'react';
import { randomUUID } from 'expo-crypto';
import type { Message, SmartPrompt } from '@/types/chat';

const REPLY_DELAY_MS = 900;
const CRISIS_TRIGGER_WORDS = ['crisis', 'unsafe', 'emergency'];

const SMART_PROMPTS: SmartPrompt[] = [
  { label: 'Tell me more\nShare what led up to this' },
  { label: 'I need a moment\nJust want to sit with this feeling' },
];

function createMessage(role: Message['role'], content: string, promptOptions?: SmartPrompt[]): Message {
  return {
    id: randomUUID(),
    threadId: 'local-thread',
    role,
    content,
    createdAt: new Date().toISOString(),
    promptOptions,
  };
}

function buildReply(userText: string): Message {
  const isCrisis = CRISIS_TRIGGER_WORDS.some((word) => userText.toLowerCase().includes(word));
  if (isCrisis) {
    return createMessage('mani', "I hear that you're going through something serious. Let's find you the right support.");
  }
  return createMessage('mani', `Thanks for sharing that. Here's a **placeholder** reply — there's no backend wired up yet.`, SMART_PROMPTS);
}

export function useChatSimulation(initialThreadId?: string) {
  const [threadId, setThreadId] = useState(initialThreadId);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isWaitingForReply, setIsWaitingForReply] = useState(false);
  const [crisisDetected, setCrisisDetected] = useState(false);
  const replyTimeoutRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const sendMessage = useCallback((content: string) => {
    const trimmed = content.trim();
    if (!trimmed) return;

    const userMessage = createMessage('user', trimmed);
    setMessages((prev) => [...prev, userMessage]);
    setIsWaitingForReply(true);

    replyTimeoutRef.current = setTimeout(() => {
      const reply = buildReply(trimmed);
      setMessages((prev) => [...prev, reply]);
      setIsWaitingForReply(false);
      if (CRISIS_TRIGGER_WORDS.some((word) => trimmed.toLowerCase().includes(word))) {
        setCrisisDetected(true);
      }
    }, REPLY_DELAY_MS);
  }, []);

  const startNewThread = useCallback(() => {
    clearTimeout(replyTimeoutRef.current);
    setThreadId(randomUUID());
    setMessages([]);
    setIsWaitingForReply(false);
    setCrisisDetected(false);
  }, []);

  return {
    threadId,
    messages,
    isWaitingForReply,
    crisisDetected,
    sendMessage,
    startNewThread,
  };
}
