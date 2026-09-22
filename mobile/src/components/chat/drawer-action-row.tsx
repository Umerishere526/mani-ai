// ABOUTME: A pressable row inside ChatDrawer — gradient background, press highlight via a
// ABOUTME: group, and free-form content. Shared by nav links, new-chat, and threads.

import type { ReactNode } from 'react';
import { Pressable, View } from 'react-native';
import { cn } from '@/lib/utils';
import { CardGradient } from '@/components/shared';

export interface DrawerActionRowProps {
  accessibilityLabel: string;
  onPress: () => void;
  children: ReactNode;
  className?: string;
}

export function DrawerActionRow({ accessibilityLabel, className, onPress, children }: DrawerActionRowProps) {
  return (
    <Pressable
      onPress={onPress}
      accessibilityLabel={accessibilityLabel}
      accessibilityRole="button"
      className={cn('group/drawer-row flex-row items-center overflow-hidden rounded-xl px-3 py-3', className)}
    >
      <CardGradient />
      <View className="absolute inset-0 group-active/drawer-row:bg-secondary-500/10" />
      {children}
    </Pressable>
  );
}
