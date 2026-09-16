// ABOUTME: A vertical stack of SmartPromptChip suggestions shown under the latest Mani
// ABOUTME: message. Renders nothing if there are no prompts to show.

import { View } from 'react-native';
import type { SmartPrompt } from '@/types/chat';
import { SmartPromptChip } from './smart-prompt-chip';

export interface SmartPromptRowProps {
  prompts: SmartPrompt[];
  onPromptPress: (prompt: SmartPrompt) => void;
}

export function SmartPromptRow({ prompts, onPromptPress }: SmartPromptRowProps) {
  if (!prompts || !Array.isArray(prompts) || prompts.length === 0) {
    return null;
  }

  return (
    <View className="gap-3 px-4 py-2">
      {prompts.map((prompt) => (
        <SmartPromptChip key={prompt.label} prompt={prompt} onPress={onPromptPress} />
      ))}
    </View>
  );
}
