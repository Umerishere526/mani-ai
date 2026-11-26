// ABOUTME: What tapping a button under Mani's reply does: a library button opens that library section, anything
// ABOUTME: else (a technique offer, a decline, a plain reply) is sent as the label, which the backend matches.

import type { SmartPrompt } from '@/types/chat';

/** The library's front page, as a button names it; every other value is a topic id the backend lists. */
const LIBRARY_HOME = 'home';

export type PromptAction =
  /** `section` null is the library's front page. */
  | { kind: 'library'; section: string | null }
  | { kind: 'send'; text: string };

export function promptAction(prompt: SmartPrompt): PromptAction {
  if (prompt.library) {
    return { kind: 'library', section: prompt.library === LIBRARY_HOME ? null : prompt.library };
  }
  // A technique offer is sent too: the backend knows the tap from its label and starts that technique.
  return { kind: 'send', text: prompt.label };
}
