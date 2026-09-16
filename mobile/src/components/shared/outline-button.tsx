// ABOUTME: White-outlined pill button on dark/gradient backgrounds — used for secondary
// ABOUTME: actions like "skip" or "not now" in onboarding steps.

import * as Haptics from 'expo-haptics';
import { Pressable, type PressableProps } from 'react-native';
import { cn } from '@/lib/utils';
import { Text } from './text';

export interface OutlineButtonProps extends PressableProps {
  label: string;
  className?: string;
}

export function OutlineButton({ label, className, onPress, ...props }: OutlineButtonProps) {
  const handlePress: PressableProps['onPress'] = (event) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    onPress?.(event);
  };

  return (
    <Pressable
      onPress={handlePress}
      className={cn(
        'items-center justify-center rounded-full border border-white bg-transparent px-8 py-4 active:opacity-80',
        className,
      )}
      {...props}
    >
      <Text className="font-sans-semibold text-base text-white">{label}</Text>
    </Pressable>
  );
}
