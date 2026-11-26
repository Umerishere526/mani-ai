// ABOUTME: Shown when an exercise finishes — a closing line and the two ways on from here:
// ABOUTME: back into the chat, or to the library for another exercise.

import { View } from 'react-native';
import { PrimaryButton, SecondaryButton, Text } from '@/components/shared';
import en from '@/dictionaries/en.json';

export interface ExerciseCompleteProps {
  onContinueChatting: () => void;
  onVisitLibrary: () => void;
}

export function ExerciseComplete({ onContinueChatting, onVisitLibrary }: ExerciseCompleteProps) {
  return (
    <View className="items-center gap-4 self-stretch">
      <Text className="mb-2 text-center font-sans-semibold text-lg text-white" accessibilityRole="header">
        {en.exercises.completeTitle}
      </Text>
      <SecondaryButton label={en.exercises.continueChatting} onPress={onContinueChatting} className="self-stretch" />
      <PrimaryButton label={en.exercises.visitLibrary} onPress={onVisitLibrary} className="self-stretch" />
    </View>
  );
}
