// ABOUTME: The standing disclosure that MANI is an AI companion and not a therapist, shown
// ABOUTME: wherever the person chooses how MANI talks to them and in Settings.

import { cn } from '@/lib/utils';
import en from '@/dictionaries/en.json';
import { Text } from './text';

export interface AiDisclosureProps {
  className?: string;
}

export function AiDisclosure({ className }: AiDisclosureProps) {
  return (
    <Text className={cn('text-center text-sm leading-5 text-secondary-500/70', className)}>
      {en.disclosure.aiCompanion}
    </Text>
  );
}
