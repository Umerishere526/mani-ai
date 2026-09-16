// ABOUTME: Base text component — disables font scaling and applies the app's default
// ABOUTME: type color/family so screens don't repeat those on every RN Text usage.

import { Text as RNText, type TextProps as RNTextProps } from 'react-native';
import { cn } from '@/lib/utils';

export interface TextProps extends RNTextProps {
  className?: string;
}

export function Text({ className, style, ...props }: TextProps) {
  return (
    <RNText
      allowFontScaling={false}
      className={cn('font-sans text-secondary-500', className)}
      style={style}
      {...props}
    />
  );
}
