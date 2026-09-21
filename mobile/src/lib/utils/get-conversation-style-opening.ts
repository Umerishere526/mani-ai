// ABOUTME: Looks up the style-specific opening question Mani asks once the user picks a
// ABOUTME: conversation style (Directive/Supportive/Reflective) at the start of a chat.

import en from '@/dictionaries/en.json';
import type { ConversationStyle } from '@/types/chat';

export function getConversationStyleOpening(style: ConversationStyle): string {
  return en.chat.styles[style].opening;
}
