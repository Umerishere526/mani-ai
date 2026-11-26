// ABOUTME: The greeting screen shown before a chat has a conversation style: the backend's greeting and the styles
// ABOUTME: it offers (Directive, Supportive, Reflective), which set Mani's tone for the thread.

import { ScrollView, View } from 'react-native';
import en from '@/dictionaries/en.json';
import type { StyleOption } from '@/types/chat-api';
import type { ConversationStyle } from '@/types/chat';
import { AiDisclosure, Text } from '@/components/shared';
import { ConversationStyleOption } from './conversation-style-option';

export interface ConversationStylePickerProps {
  greeting: string;
  options: StyleOption[];
  defaultStyle?: ConversationStyle | null;
  onSelect: (style: ConversationStyle) => void;
}

export function ConversationStylePicker({ greeting, options, defaultStyle, onSelect }: ConversationStylePickerProps) {
  return (
    <ScrollView className="flex-1" contentContainerClassName="grow items-center justify-center gap-8 px-6">
      <Text className="text-center font-sans-semibold text-xl">{greeting}</Text>

      <View className="w-full gap-4" accessibilityLabel={en.chat.styleOptionsLabel}>
        {options.map((option) => (
          <ConversationStyleOption
            key={option.style}
            style={option.style}
            selected={option.style === defaultStyle}
            onPress={onSelect}
          />
        ))}
      </View>

      <AiDisclosure />
    </ScrollView>
  );
}
