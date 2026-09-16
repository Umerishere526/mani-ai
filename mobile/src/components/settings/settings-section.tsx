// ABOUTME: Groups a set of SettingsRow items under an uppercase section label.

import type { ReactNode } from 'react';
import { View } from 'react-native';
import { Text } from '@/components/shared';

export interface SettingsSectionProps {
  title: string;
  children: ReactNode;
}

export function SettingsSection({ title, children }: SettingsSectionProps) {
  return (
    <View className="mb-6">
      <Text className="mb-2 px-4 font-sans-semibold text-xs uppercase tracking-[1px] text-secondary-400">
        {title}
      </Text>
      <View className="gap-1">{children}</View>
    </View>
  );
}
