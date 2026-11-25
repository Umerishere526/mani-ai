// ABOUTME: Base text component — follows the system text size up to a capped multiplier and
// ABOUTME: applies the app's default type color/family so screens don't repeat them on every Text.

import { Text as RNText, type TextProps as RNTextProps } from 'react-native';
import { MAX_FONT_SIZE_MULTIPLIER } from '@/lib/font-scaling';
import { cn } from '@/lib/utils';

export interface TextProps extends RNTextProps {
  className?: string;
}

export function Text({ className, style, ...props }: TextProps) {
  return (
    <RNText
      maxFontSizeMultiplier={MAX_FONT_SIZE_MULTIPLIER}
      className={cn('font-sans text-secondary-500', className)}
      style={style}
      {...props}
    />
  );
}
