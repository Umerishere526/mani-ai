// ABOUTME: The greeting screen shown before a chat has a conversation style — lets the user
// ABOUTME: pick Directive, Supportive, or Reflective, which sets Mani's tone for the thread.

import { View } from 'react-native';
import en from '@/dictionaries/en.json';
import type { ConversationStyle } from '@/types/chat';
import { Text } from '@/components/shared';
import { ConversationStyleOption } from './conversation-style-option';

export interface ConversationStylePickerProps {
  onSelect: (style: ConversationStyle) => void;
}

const STYLES: ConversationStyle[] = ['directive', 'supportive', 'reflective'];

export function ConversationStylePicker({ onSelect }: ConversationStylePickerProps) {
  return (
    <View className="flex-1 items-center justify-center gap-8 px-6">
      <View className="items-center gap-3">
        <Text className="font-sans-semibold text-xl">{en.chat.styleGreeting}</Text>
        <Text className="text-center text-base text-secondary-600">{en.chat.stylePrompt}</Text>
      </View>

      <View className="w-full gap-4" accessibilityLabel={en.chat.styleOptionsLabel}>
        {STYLES.map((style) => (
          <ConversationStyleOption key={style} style={style} onPress={onSelect} />
        ))}
      </View>
    </View>
  );
}
