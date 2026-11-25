// ABOUTME: What a library screen shows while it reads from the backend: a spinner, or, when the read failed, the
// ABOUTME: shared line and Try again.

import { ActivityIndicator, View } from 'react-native';
import { LoadFailed } from '@/components/chat';
import { colors } from '@/lib/tokens';
import en from '@/dictionaries/en.json';

export interface LibraryLoadingProps {
  failed: boolean;
  onRetry: () => void;
}

export function LibraryLoading({ failed, onRetry }: LibraryLoadingProps) {
  if (failed) return <LoadFailed onRetry={onRetry} />;
  return (
    <View className="items-center py-8">
      <ActivityIndicator size="small" color={colors.secondary[500]} accessibilityLabel={en.exercises.loadingLabel} />
    </View>
  );
}
