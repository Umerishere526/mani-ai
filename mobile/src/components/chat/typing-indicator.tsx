// ABOUTME: Three-dot "Mani is typing" bubble shown while waiting for a chat response.
// ABOUTME: Each dot pulses scale/opacity in a staggered loop via Reanimated.

import { useEffect } from 'react';
import { View } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withDelay,
  withRepeat,
  withSequence,
  withTiming,
  interpolate,
  Easing,
} from 'react-native-reanimated';
import en from '@/dictionaries/en.json';

const ANIMATION_DURATION = 800;
const STAGGER_DELAY = 200;

function useDotStyle(delay: number) {
  const progress = useSharedValue(0);

  useEffect(() => {
    progress.value = withDelay(
      delay,
      withRepeat(
        withSequence(
          withTiming(1, { duration: ANIMATION_DURATION, easing: Easing.inOut(Easing.ease) }),
          withTiming(0, { duration: ANIMATION_DURATION, easing: Easing.inOut(Easing.ease) }),
        ),
        -1,
      ),
    );
  }, [delay, progress]);

  return useAnimatedStyle(() => ({
    transform: [{ scale: interpolate(progress.value, [0, 1], [0.6, 1]) }],
    opacity: interpolate(progress.value, [0, 1], [0.4, 1]),
  }));
}

function Dot({ delay }: { delay: number }) {
  const style = useDotStyle(delay);
  return <Animated.View className="h-2 w-2 rounded-full bg-primary-600" style={style} />;
}

export function TypingIndicator() {
  return (
    <View className="my-1 items-start px-4">
      <View
        className="max-w-[80%] rounded-tl-sm rounded-lg bg-primary-350 px-4 py-4"
        accessible
        accessibilityLabel={en.chat.typingIndicatorLabel}
        accessibilityRole="text"
      >
        <View className="flex-row items-center gap-1.5">
          <Dot delay={0} />
          <Dot delay={STAGGER_DELAY} />
          <Dot delay={STAGGER_DELAY * 2} />
        </View>
      </View>
    </View>
  );
}
