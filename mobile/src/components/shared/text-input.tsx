// ABOUTME: Base text input — disables font scaling and applies the app's default type
// ABOUTME: family, matching the Text component's defaults for a consistent baseline.

import { forwardRef } from 'react';
import { TextInput as RNTextInput, type TextInputProps as RNTextInputProps } from 'react-native';
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
      allowFontScaling={false}
      className={cn('font-sans text-secondary-500', className)}
      style={style}
      {...props}
    />
  );
});
