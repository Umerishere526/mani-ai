// ABOUTME: The player's play/pause button inside a progress ring, with the time remaining
// ABOUTME: shown underneath so the person knows how long the exercise has left.

import { Pressable, View } from 'react-native';
import { Feather } from '@react-native-vector-icons/feather';
import { CircularProgressButton, Text } from '@/components/shared';
import { colors } from '@/lib/tokens';
import { cn, formatClock } from '@/lib/utils';
import en from '@/dictionaries/en.json';

export interface ExercisePlaybackControlProps {
  isPlaying: boolean;
  progress: number;
  remainingSeconds: number;
  onToggle: () => void;
}

export function ExercisePlaybackControl({ isPlaying, progress, remainingSeconds, onToggle }: ExercisePlaybackControlProps) {
  const remaining = formatClock(remainingSeconds);

  return (
    <View className="items-center gap-3">
      <CircularProgressButton
        progress={progress}
        size={88}
        strokeWidth={4}
        progressColor="rgba(255,255,255,0.5)"
        trackColor="rgba(255,255,255,0.15)"
      >
        <Pressable
          onPress={onToggle}
          className={cn(
            'h-18 w-18 items-center justify-center rounded-full',
            isPlaying ? 'bg-white/8' : 'bg-secondary-500',
          )}
          accessibilityRole="button"
          accessibilityLabel={isPlaying ? en.exercises.pauseLabel : en.exercises.playLabel}
        >
          <Feather
            name={isPlaying ? 'pause' : 'play'}
            size={32}
            color={isPlaying ? colors.text.inverse : colors.primary[500]}
            style={!isPlaying ? { marginLeft: 4 } : undefined}
          />
        </Pressable>
      </CircularProgressButton>
      <Text
        className="text-base text-white/70"
        accessibilityLabel={`${en.exercises.remainingTimeLabel} ${remaining}`}
      >
        {remaining}
      </Text>
    </View>
  );
}
