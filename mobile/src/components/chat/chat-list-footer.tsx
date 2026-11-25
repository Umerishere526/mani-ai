// ABOUTME: What follows the newest message: the pending reply, a message that failed to send with its retry, or
// ABOUTME: the buttons under Mani's latest reply.

import type { SmartPrompt } from '@/types/chat';
import { ReplyPending } from './reply-pending';
import { SendFailed } from './send-failed';
import { SmartPromptRow } from './smart-prompt-row';

export interface ChatListFooterProps {
  isWaitingForReply: boolean;
  failed: { error: string | null } | null;
  prompts: SmartPrompt[];
  onPromptPress: (prompt: SmartPrompt) => void;
  onRetry?: () => void;
}

export function ChatListFooter({ isWaitingForReply, failed, prompts, onPromptPress, onRetry }: ChatListFooterProps) {
  if (isWaitingForReply) return <ReplyPending />;
  if (failed) return <SendFailed error={failed.error} onRetry={onRetry} />;
  return <SmartPromptRow prompts={prompts} onPromptPress={onPromptPress} />;
}
