// ABOUTME: A new conversation before its first message: the backend's opening as a style picker once it has
// ABOUTME: loaded, a spinner while it loads, and a retry when it could not be read.

import { ActivityIndicator, View } from 'react-native';
import en from '@/dictionaries/en.json';
import { colors } from '@/lib/tokens';
import type { OpeningOut } from '@/types/chat-api';
import type { ConversationStyle } from '@/types/chat';
import { ConversationStylePicker } from './conversation-style-picker';
import { LoadFailed } from './load-failed';

export interface ChatOpeningProps {
  opening: OpeningOut | null;
  defaultStyle?: ConversationStyle | null;
  failed: boolean;
  onRetry: () => void;
  onSelect: (style: ConversationStyle) => void;
}

export function ChatOpening({ opening, defaultStyle, failed, onRetry, onSelect }: ChatOpeningProps) {
  if (failed) return <LoadFailed onRetry={onRetry} />;
  if (!opening) {
    return (
      <View className="flex-1 items-center justify-center">
        <ActivityIndicator color={colors.secondary[500]} accessibilityLabel={en.common.loading} />
      </View>
    );
  }
  return (
    <ConversationStylePicker
      greeting={opening.greeting}
      options={opening.style_options ?? []}
      defaultStyle={defaultStyle}
      onSelect={onSelect}
    />
  );
}
