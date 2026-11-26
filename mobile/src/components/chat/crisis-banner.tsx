// ABOUTME: Replaces ChatInputBar while the person's chat is paused: tapping it reopens the crisis
// ABOUTME: screen with the helplines instead of letting them keep typing.

import { Pressable } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import en from '@/dictionaries/en.json';
import { Text } from '@/components/shared';

export interface CrisisBannerProps {
  onPress: () => void;
}

export function CrisisBanner({ onPress }: CrisisBannerProps) {
  const insets = useSafeAreaInsets();

  return (
    <Pressable
      onPress={onPress}
      className="items-center justify-center bg-primary-900 px-5 pt-8 active:bg-primary-800"
      style={{ paddingBottom: insets.bottom + 24 }}
      accessibilityRole="button"
      accessibilityLabel={en.chat.crisisBannerLabel}
      accessibilityHint={en.chat.crisisBannerHint}
    >
      <Text className="text-center font-sans-semibold text-[17px] leading-6">{en.chat.crisisBannerText}</Text>
    </Pressable>
  );
}
