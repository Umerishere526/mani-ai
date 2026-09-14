// ABOUTME: The pinned profile row at the bottom of ChatDrawer, with a gradient fade so the
// ABOUTME: scrolling thread list above it doesn't cut off abruptly.

import { Pressable, View } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { colors } from '@/lib/tokens';
import en from '@/dictionaries/en.json';
import { Text } from '@/components/shared';

export interface ChatDrawerProfileFooterProps {
  nickname?: string | null;
  onPress: () => void;
  gradientBottomOffset: number;
  paddingBottom: number;
}

export function ChatDrawerProfileFooter({
  nickname,
  onPress,
  gradientBottomOffset,
  paddingBottom,
}: ChatDrawerProfileFooterProps) {
  const displayName = nickname ?? 'User';

  return (
    <>
      <LinearGradient
        colors={[`${colors.primary[900]}00`, colors.primary[900], colors.primary[900]]}
        className="absolute left-0 right-0 h-10"
        style={{ bottom: gradientBottomOffset }}
        pointerEvents="none"
      />
      <Pressable
        onPress={onPress}
        accessibilityLabel={en.chat.openSettingsLabel}
        accessibilityRole="button"
        className="absolute bottom-0 left-0 right-0 flex-row items-center border-t border-secondary-500/10 bg-primary-900 px-4 pt-4 active:bg-primary-800"
        style={{ paddingBottom }}
      >
        <View className="mr-3 h-10 w-10 items-center justify-center rounded-full bg-secondary-500">
          <Text className="font-sans-semibold text-lg text-primary-600">{displayName[0]?.toUpperCase()}</Text>
        </View>
        <Text className="flex-1 font-sans-medium text-base" numberOfLines={1}>
          {displayName}
        </Text>
      </Pressable>
    </>
  );
}
