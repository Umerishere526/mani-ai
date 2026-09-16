// ABOUTME: Pill-shaped text input whose border switches to the accent color on focus.
// ABOUTME: Used across onboarding forms (nickname, email, password, OTP).

import { colors } from '@/lib/tokens';
import { cn } from '@/lib/utils';
import { TextInput, type TextInputProps } from './text-input';

export type CapsuleInputProps = TextInputProps;

export function CapsuleInput({ className, ...props }: CapsuleInputProps) {
  return (
    <TextInput
      className={cn(
        'rounded-full border border-border-default bg-bg-card px-4 py-3 text-base text-text-default focus:border-accent-default',
        className,
      )}
      placeholderTextColor={colors.text.light}
      {...props}
    />
  );
}
