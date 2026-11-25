// ABOUTME: The account-wide chat pause and the crisis screen. The pause is read from the profile on launch and from
// ABOUTME: every reply or refusal, so a new chat or another screen cannot get around it.

import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { useLoad } from '@/hooks/useLoad';
import { useSession } from '@/hooks/useSession';
import { getProfile } from '@/lib/api/profile';
import { emergencyLeads, isPauseActive, opensCrisisScreen, pauseFromError, pauseIn, type ChatPause } from '@/lib/chat';
import type { TurnOut } from '@/types/chat-api';

interface ChatSafetyValue {
  /** The pause running now, or null when chat is open. */
  pause: ChatPause | null;
  isScreenVisible: boolean;
  /** Emergency services lead the screen (an overdose) instead of the 988 line. */
  emergencyFirst: boolean;
  noteTurn: (turn: TurnOut, threadId: string) => void;
  noteSendError: (error: unknown) => void;
  openScreen: () => void;
  closeScreen: () => void;
}

const ChatSafetyContext = createContext<ChatSafetyValue | null>(null);

export function ChatSafetyProvider({ children }: { children: ReactNode }) {
  const { session } = useSession();
  const [pause, setPause] = useState<ChatPause | null>(null);
  const [isScreenVisible, setScreenVisible] = useState(false);
  // Threads whose last reply found a crisis: only the first such reply opens the screen.
  const crisisThreads = useRef(new Set<string>());

  const startPause = (next: ChatPause | null) => {
    if (!isPauseActive(next, new Date())) return;
    setPause(next);
    setScreenVisible(true);
  };

  // Read again for each person who signs in, so a pause begun on another device shows here on launch.
  // The profile is the whole truth for the person signing in, so it also clears a pause left from someone else.
  useLoad(session?.user?.id ?? null, getProfile, (profile) => {
    const next = pauseIn(profile);
    if (isPauseActive(next, new Date())) startPause(next);
    else setPause(null);
  });

  useEffect(() => {
    if (!pause) return;
    // One timer to the pause's end; the screen shows when chat opens again, never a ticking countdown.
    const timer = setTimeout(() => setPause(null), Math.max(0, Date.parse(pause.until) - Date.now()));
    return () => clearTimeout(timer);
  }, [pause]);

  const noteTurn = (turn: TurnOut, threadId: string) => {
    if (opensCrisisScreen(turn, crisisThreads.current.has(threadId))) setScreenVisible(true);
    if (turn.crisis_detected) crisisThreads.current.add(threadId);
    else crisisThreads.current.delete(threadId);
    startPause(pauseIn(turn));
  };

  const value: ChatSafetyValue = {
    pause,
    isScreenVisible,
    emergencyFirst: emergencyLeads(pause),
    noteTurn,
    noteSendError: (error) => startPause(pauseFromError(error)),
    openScreen: () => setScreenVisible(true),
    closeScreen: () => setScreenVisible(false),
  };

  return <ChatSafetyContext.Provider value={value}>{children}</ChatSafetyContext.Provider>;
}

export function useChatSafety(): ChatSafetyValue {
  const context = useContext(ChatSafetyContext);
  if (!context) {
    throw new Error('useChatSafety must be used within a ChatSafetyProvider');
  }
  return context;
}
