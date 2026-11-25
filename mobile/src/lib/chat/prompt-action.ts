// ABOUTME: What tapping a button under Mani's reply does: a library button opens that library section, anything
// ABOUTME: else (a technique offer, a decline, a plain reply) is sent as the label, which the backend matches.

import { CATEGORY_DISPLAY_ORDER } from '@/lib/exercise-categories';
import type { SmartPrompt } from '@/types/chat';
import type { TopicId } from '@/types/exercise';

export type PromptAction =
  /** `section` null is the library's front page: "home", or a section the app does not list. */
  | { kind: 'library'; section: TopicId | null }
  | { kind: 'send'; text: string };

function isListedSection(library: string): library is TopicId {
  return (CATEGORY_DISPLAY_ORDER as string[]).includes(library);
}

export function promptAction(prompt: SmartPrompt): PromptAction {
  if (prompt.library) {
    return { kind: 'library', section: isListedSection(prompt.library) ? prompt.library : null };
  }
  // A technique offer is sent too: the backend knows the tap from its label and starts that technique.
  return { kind: 'send', text: prompt.label };
}
