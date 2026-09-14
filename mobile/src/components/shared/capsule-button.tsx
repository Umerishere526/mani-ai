// ABOUTME: Full-width pill button with primary (filled) and secondary (outlined) variants,
// ABOUTME: plus a loading state that swaps the label for a spinner.

import { ActivityIndicator, Pressable, type PressableProps } from 'react-native';
import { colors } from '@/lib/tokens';
import { cn } from '@/lib/utils';
import { Text } from './text';

export interface CapsuleButtonProps extends PressableProps {
  title: string;
  disabled?: boolean;
  loading?: boolean;
  variant?: 'primary' | 'secondary';
  className?: string;
}

export function CapsuleButton({
  title,
  disabled = false,
  loading = false,
  variant = 'primary',
  className,
  ...props
}: CapsuleButtonProps) {
  const isDisabled = disabled || loading;
  const isPrimary = variant === 'primary';

  return (
    <Pressable
      disabled={isDisabled}
      accessibilityRole="button"
      accessibilityLabel={title}
      accessibilityState={{ disabled: isDisabled }}
      className={cn(
        'items-center justify-center self-stretch rounded-full px-4 py-3 active:opacity-70',
        isPrimary ? 'bg-accent-default' : 'border border-accent-default bg-transparent',
        isDisabled && 'opacity-50',
        className,
      )}
      {...props}
    >
      {loading ? (
        <ActivityIndicator color={isPrimary ? colors.text.inverse : colors.accent.default} size="small" />
      ) : (
        <Text className={cn('font-sans-semibold text-base', isPrimary ? 'text-white' : 'text-accent-default')}>
          {title}
        </Text>
      )}
    </Pressable>
  );
}
