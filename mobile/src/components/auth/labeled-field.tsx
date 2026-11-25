// ABOUTME: A form field's label above the bordered box that holds its input (and any
// ABOUTME: trailing control, like a show-password toggle), shared by the account forms.

import type { ReactNode } from 'react';
import { View } from 'react-native';
import { Text } from '@/components/shared';

export interface LabeledFieldProps {
  label: string;
  children: ReactNode;
}

export function LabeledField({ label, children }: LabeledFieldProps) {
  return (
    <View className="mb-6">
      <Text className="mb-2 font-sans-medium text-sm text-secondary-500/90">{label}</Text>
      <View className="flex-row items-center rounded-xl border border-secondary-500/15 bg-secondary-500/8">
        {children}
      </View>
    </View>
  );
}
