// ABOUTME: Breathing sphere image used as the app's ambient branding element (home hero,
// ABOUTME: onboarding). Animates a gentle scale pulse on the UI thread via Reanimated.

import { useEffect } from 'react';
import { Image } from 'expo-image';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withTiming,
  interpolate,
  Easing,
} from 'react-native-reanimated';
import en from '@/dictionaries/en.json';

export interface GradientSphereProps {
  size?: number;
  animated?: boolean;
}

const BREATH_DURATION = 6000;

export function GradientSphere({ size = 250, animated = true }: GradientSphereProps) {
  const breath = useSharedValue(0);

  useEffect(() => {
    if (!animated) {
      breath.value = 0;
      return;
    }

    // Sweeps 0 -> 1 then snaps back (no reverse), matching the [0, 0.5, 1] -> [1, 1.08, 1]
    // scale curve below — the up-then-down pulse comes from that curve, not from reversing.
    breath.value = withRepeat(
      withTiming(1, { duration: BREATH_DURATION, easing: Easing.inOut(Easing.ease) }),
      -1,
      false,
    );
  }, [animated, breath]);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: interpolate(breath.value, [0, 0.5, 1], [1, 1.08, 1]) }],
  }));

  return (
    <Animated.View
      accessible
      accessibilityLabel={en.shared.gradientSphereLabel}
      style={[{ width: size, height: size, borderRadius: size / 2, overflow: 'hidden' }, animatedStyle]}
    >
      <Image
        source={require('@/assets/images/sphere-bg.png')}
        style={{ width: '100%', height: '100%' }}
        contentFit="cover"
      />
    </Animated.View>
  );
}
