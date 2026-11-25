// ABOUTME: Base text input — follows the system text size up to a capped multiplier and applies
// ABOUTME: the app's default type family, matching the Text component's defaults.

import { forwardRef } from 'react';
import { TextInput as RNTextInput, type TextInputProps as RNTextInputProps } from 'react-native';
import { MAX_FONT_SIZE_MULTIPLIER } from '@/lib/font-scaling';
import { cn } from '@/lib/utils';

export interface TextInputProps extends RNTextInputProps {
  className?: string;
}

export const TextInput = forwardRef<RNTextInput, TextInputProps>(function TextInput(
  { className, style, ...props },
  ref,
) {
  return (
    <RNTextInput
      ref={ref}
      maxFontSizeMultiplier={MAX_FONT_SIZE_MULTIPLIER}
      className={cn('font-sans text-secondary-500', className)}
      style={style}
      {...props}
    />
  );
});
