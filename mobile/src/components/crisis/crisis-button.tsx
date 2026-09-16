// ABOUTME: Cream pill button prompting a user to open crisis support resources.
// ABOUTME: Used inline on screens that don't already show the crisis drawer's own entry point.

import { Pressable, type PressableProps } from 'react-native';
import { cn } from '@/lib/utils';
import en from '@/dictionaries/en.json';
import { Text } from '@/components/shared';

export interface CrisisButtonProps extends PressableProps {
  className?: string;
}

export function CrisisButton({ className, ...props }: CrisisButtonProps) {
  return (
    <Pressable
      className={cn('items-center justify-center rounded-full bg-secondary-500 px-6 py-4 active:opacity-80', className)}
      {...props}
    >
      <Text className="font-sans-semibold text-base text-primary-500">{en.crisis.buttonLabel}</Text>
    </Pressable>
  );
}
