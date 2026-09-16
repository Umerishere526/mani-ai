// ABOUTME: A single exercise card on the Home screen — gradient background, duration/type
// ABOUTME: meta line, title, and description or subtitle.

import { Pressable } from 'react-native';
import { CardGradient, Text } from '@/components/shared';
import { formatDuration } from '@/lib/utils';
import type { Exercise } from '@/types/exercise';
import type { ResponsiveTypography } from '@/hooks/useResponsiveTypography';

export interface HomeExerciseCardProps {
  exercise: Exercise;
  typography: ResponsiveTypography;
  onPress: (exerciseId: string) => void;
}

export function HomeExerciseCard({ exercise, typography, onPress }: HomeExerciseCardProps) {
  return (
    <Pressable
      onPress={() => onPress(exercise.id)}
      className="w-[85%] overflow-hidden rounded-lg px-4 pb-4 pt-4 active:opacity-90"
      accessibilityRole="button"
      accessibilityLabel={`${exercise.title}, ${formatDuration(exercise.durationMinutes)}, ${exercise.type}`}
      accessibilityHint="Tap to start this exercise"
    >
      <CardGradient />
      <Text
        className="text-xs text-white/60"
        style={{ marginBottom: typography.homeCard.metaMarginBottom }}
      >
        {formatDuration(exercise.durationMinutes)} • {exercise.type}
      </Text>
      <Text className="font-sans-semibold text-white" style={{ fontSize: typography.homeCard.titleFontSize }}>
        {exercise.title}
      </Text>
      <Text
        className="mt-1 text-white/80"
        style={{ fontSize: typography.homeCard.descriptionFontSize }}
      >
        {exercise.subtitle ?? exercise.description}
      </Text>
    </Pressable>
  );
}
