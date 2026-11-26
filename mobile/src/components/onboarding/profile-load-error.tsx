// ABOUTME: Shown in place of the app when the signed-in person's profile could not be read,
// ABOUTME: so we can't tell whether they still need onboarding: retry, or sign out.

import { View } from 'react-native';
import { PrimaryButton, SecondaryButton, Text } from '@/components/shared';
import en from '@/dictionaries/en.json';

export interface ProfileLoadErrorProps {
  onRetry: () => void;
  onSignOut: () => void;
}

export function ProfileLoadError({ onRetry, onSignOut }: ProfileLoadErrorProps) {
  return (
    <View className="flex-1 items-center justify-center gap-6 bg-primary-900 px-6">
      <Text className="text-center text-base leading-6" accessibilityRole="alert">
        {en.onboarding.profileLoadFailed}
      </Text>
      <PrimaryButton label={en.common.retry} onPress={onRetry} className="self-stretch" />
      <SecondaryButton label={en.settings.logOut} onPress={onSignOut} className="self-stretch" />
    </View>
  );
}
