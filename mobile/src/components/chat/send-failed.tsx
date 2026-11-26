// ABOUTME: Under a message that did not send: the backend's reason (or a plain one when the network failed) and a
// ABOUTME: Try again button that resends it, unless the chat is paused.

import { Pressable, View } from 'react-native';
import en from '@/dictionaries/en.json';
import { Text } from '@/components/shared';

export interface SendFailedProps {
  error: string | null;
  onRetry?: () => void;
}

export function SendFailed({ error, onRetry }: SendFailedProps) {
  return (
    <View className="items-end gap-2 px-4 py-2" accessibilityLiveRegion="polite">
      <Text className="text-right text-sm text-secondary-600">{error ?? en.chat.sendFailed}</Text>
      {onRetry ? (
        <Pressable
          onPress={onRetry}
          className="min-h-11 justify-center rounded-full bg-primary-500 px-5 active:opacity-80"
          accessibilityRole="button"
          accessibilityLabel={en.chat.retrySendLabel}
        >
          <Text className="font-sans-semibold text-sm">{en.common.retry}</Text>
        </Pressable>
      ) : null}
    </View>
  );
}
