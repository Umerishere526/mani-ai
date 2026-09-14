// ABOUTME: Manual verification harness, not shipped UI — confirms NativeWind v5 preview.4
// ABOUTME: doesn't drop className when a Reanimated animated style is also present.

import { useEffect } from 'react';
import { View } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withTiming,
} from 'react-native-reanimated';

/**
 * nativewind/nativewind#1647: in some v5 preview builds, setting both `className` and
 * `style` (from `useAnimatedStyle`) on the same Animated component caused `className`
 * to be silently dropped — only `style` applied. The issue is closed upstream, but we
 * couldn't confirm which preview version carries the fix from docs alone.
 *
 * How to use: render <NativewindReanimatedSpike /> from any screen temporarily (or
 * a scratch route), open it in a simulator, and check with the two boxes below:
 *   - Box A (Reanimated only):        should turn red and pulse.
 *   - Box B (className + Reanimated): should be a rounded card (from className)
 *                                     AND pulse (from Reanimated). If it renders as
 *                                     an unstyled square that only pulses, className
 *                                     is being dropped — file/track an upgrade of the
 *                                     nativewind preview before building Stage 2/3 on
 *                                     the className+Reanimated pattern.
 *
 * Delete this file once the combination has been confirmed working in a simulator.
 */
export function NativewindReanimatedSpike() {
  const progress = useSharedValue(0);

  useEffect(() => {
    progress.value = withRepeat(withTiming(1, { duration: 800 }), -1, true);
  }, [progress]);

  const animatedStyle = useAnimatedStyle(() => ({
    opacity: 0.4 + progress.value * 0.6,
    transform: [{ scale: 1 + progress.value * 0.1 }],
  }));

  return (
    <View className="flex-1 items-center justify-center gap-6 bg-primary-900">
      <Animated.View
        style={[{ width: 80, height: 80, backgroundColor: 'red' }, animatedStyle]}
      />
      <Animated.View
        className="h-20 w-20 rounded-2xl bg-secondary-500"
        style={animatedStyle}
      />
    </View>
  );
}
