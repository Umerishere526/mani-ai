// ABOUTME: Shown while Mani's reply is on its way: the typing dots, and after about 8 s a line saying it is still
// ABOUTME: thinking, so a slow reply never looks like a frozen screen.

import { useEffect, useState } from 'react';
import { View } from 'react-native';
import en from '@/dictionaries/en.json';
import { Text } from '@/components/shared';
import { TypingIndicator } from './typing-indicator';

export const STILL_THINKING_AFTER_MS = 8_000;

export function ReplyPending() {
  const [isSlow, setSlow] = useState(false);

  // Mounted only while a reply is pending, so each wait starts from not slow.
  useEffect(() => {
    const timer = setTimeout(() => setSlow(true), STILL_THINKING_AFTER_MS);
    return () => clearTimeout(timer);
  }, []);

  return (
    <View>
      <TypingIndicator />
      {isSlow ? (
        <Text className="px-4 text-sm text-secondary-600" accessibilityLiveRegion="polite">
          {en.chat.stillThinking}
        </Text>
      ) : null}
    </View>
  );
}
