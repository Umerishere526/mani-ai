// ABOUTME: One exercise in a library topic: its length and type (or Coming soon) above its title, opening the player
// ABOUTME: when tapped; an exercise not yet recorded is listed but opens nothing.

import { router } from 'expo-router';
import { Pressable, View } from 'react-native';
import { Feather } from '@react-native-vector-icons/feather';
import { Text } from '@/components/shared';
import { useResponsiveTypography } from '@/hooks/useResponsiveTypography';
import { exerciseAccessibilityLabel, exerciseMeta } from '@/lib/utils';
import en from '@/dictionaries/en.json';
import type { Exercise } from '@/types/exercise';

export interface ExerciseRowProps {
  exercise: Exercise;
}

export function ExerciseRow({ exercise }: ExerciseRowProps) {
  const typography = useResponsiveTypography();

  return (
    <View>
      <Pressable
        onPress={() => router.push(`/exercises/player/${exercise.id}`)}
        disabled={!exercise.recorded}
        className="flex-row items-center py-4 active:opacity-70"
        accessibilityRole="button"
        accessibilityLabel={exerciseAccessibilityLabel(exercise)}
        accessibilityHint={exercise.recorded ? en.home.exerciseCardHint : undefined}
        accessibilityState={{ disabled: !exercise.recorded }}
      >
        <View className="flex-1">
          <Text
            className="mb-1 text-white/60"
            style={{ fontSize: typography.caption.fontSize - 2, lineHeight: typography.caption.lineHeight }}
          >
            {exerciseMeta(exercise).join(' • ')}
          </Text>
          <Text
            className={exercise.recorded ? 'font-sans-semibold text-white' : 'font-sans-semibold text-white/60'}
            style={{ fontSize: typography.body.fontSize, lineHeight: typography.body.lineHeight }}
          >
            {exercise.title}
          </Text>
        </View>
        {exercise.recorded ? <Feather name="chevron-right" size={20} color="rgba(255,255,255,0.4)" /> : null}
      </Pressable>
      <View className="h-px bg-white/10" />
    </View>
  );
}
