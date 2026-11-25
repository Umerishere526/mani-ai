// ABOUTME: What a chat screen shows when it could not read from the backend: a short line and a Try again button,
// ABOUTME: so a failed load never looks like an endless spinner.

import { Pressable, View } from 'react-native';
import en from '@/dictionaries/en.json';
import { Text } from '@/components/shared';

export interface LoadFailedProps {
  onRetry: () => void;
}

export function LoadFailed({ onRetry }: LoadFailedProps) {
  return (
    <View className="flex-1 items-center justify-center gap-4 px-6">
      <Text className="text-center text-base">{en.common.error}</Text>
      <Pressable
        onPress={onRetry}
        className="min-h-11 justify-center rounded-full bg-primary-500 px-6 active:opacity-80"
        accessibilityRole="button"
        accessibilityLabel={en.common.retry}
      >
        <Text className="font-sans-semibold text-base">{en.common.retry}</Text>
      </Pressable>
    </View>
  );
}
