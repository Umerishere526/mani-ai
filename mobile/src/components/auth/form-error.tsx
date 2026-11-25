// ABOUTME: The sentence shown under a form when its last submit failed, announced to
// ABOUTME: screen readers as it appears; renders nothing when there is no error.

import { Text } from '@/components/shared';

export interface FormErrorProps {
  message: string | null;
}

export function FormError({ message }: FormErrorProps) {
  if (!message) return null;
  return (
    <Text className="mb-4 text-sm text-secondary-500" accessibilityRole="alert" accessibilityLiveRegion="polite">
      {message}
    </Text>
  );
}
