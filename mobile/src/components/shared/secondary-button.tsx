// ABOUTME: Cream pill button that crossfades to a translucent disabled look, rather than
// ABOUTME: snapping instantly — used for auth actions (sign in/up) in onboarding.

import { useEffect } from 'react';
import * as Haptics from 'expo-haptics';
import { Pressable, type PressableProps } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  interpolateColor,
  Easing,
} from 'react-native-reanimated';
import { colors } from '@/lib/tokens';

export interface SecondaryButtonProps extends PressableProps {
  label: string;
  className?: string;
}

const EASING = Easing.bezier(0.25, 0.1, 0.25, 1);

export function SecondaryButton({
  label,
  className,
  onPress,
  disabled,
  ...props
}: SecondaryButtonProps) {
  const active = useSharedValue(disabled ? 0 : 1);

  useEffect(() => {
    active.value = withTiming(disabled ? 0 : 1, { duration: 300, easing: EASING });
  }, [disabled, active]);

  const animatedButtonStyle = useAnimatedStyle(() => ({
    backgroundColor: interpolateColor(active.value, [0, 1], ['rgba(255, 255, 255, 0.2)', colors.secondary[500]]),
  }));

  const animatedTextStyle = useAnimatedStyle(() => ({
    color: interpolateColor(active.value, [0, 1], ['rgba(255, 255, 255, 0.4)', colors.primary[500]]),
  }));

  const handlePress: PressableProps['onPress'] = (event) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    onPress?.(event);
  };

  return (
    <Pressable className={className ?? 'self-center'} onPress={handlePress} disabled={disabled} {...props}>
      <Animated.View
        className="items-center justify-center rounded-full px-8 py-4"
        style={animatedButtonStyle}
      >
        <Animated.Text allowFontScaling={false} className="font-sans-semibold text-base" style={animatedTextStyle}>
          {label}
        </Animated.Text>
      </Animated.View>
    </Pressable>
  );
}
