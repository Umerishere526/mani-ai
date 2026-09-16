// ABOUTME: Filled pill button, the app's primary call-to-action style. Disabled state
// ABOUTME: swaps to a transparent/outlined look rather than just dimming.

import * as Haptics from 'expo-haptics';
import { Pressable, type PressableProps } from 'react-native';
import { cn } from '@/lib/utils';
import { Text } from './text';

export interface PrimaryButtonProps extends PressableProps {
  label: string;
  className?: string;
}

export function PrimaryButton({
  label,
  className,
  onPress,
  disabled,
  ...props
}: PrimaryButtonProps) {
  const handlePress: PressableProps['onPress'] = (event) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    onPress?.(event);
  };

  return (
    <Pressable
      onPress={handlePress}
      disabled={disabled}
      className={cn(
        'items-center justify-center self-center rounded-full px-8 py-4',
        disabled
          ? 'border border-white/30 bg-transparent'
          : 'bg-primary-400 active:opacity-90',
        className,
      )}
      {...props}
    >
      <Text className={cn('font-sans-semibold text-white', disabled && 'text-white/40')}>
        {label}
      </Text>
    </Pressable>
  );
}
