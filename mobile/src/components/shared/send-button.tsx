// ABOUTME: Circular send button for the chat input bar. Scales down with a spring on
// ABOUTME: press for tactile feedback, independent of the pill's own active: state.

import { Feather } from '@react-native-vector-icons/feather';
import { Pressable, type GestureResponderEvent } from 'react-native';
import Animated, { useSharedValue, useAnimatedStyle, withSpring } from 'react-native-reanimated';
import { colors } from '@/lib/tokens';
import { cn } from '@/lib/utils';
import en from '@/dictionaries/en.json';

export interface SendButtonProps {
  onPress: () => void;
  disabled?: boolean;
  filled?: boolean;
  className?: string;
}

const BUTTON_SIZE = 36;
// Reanimated 4 has no speed/bounciness spring model (that's RN Animated's); this
// duration/dampingRatio pair reproduces the same fast, barely-overshooting feel.
const SPRING_CONFIG = { duration: 200, dampingRatio: 0.9 };

export function SendButton({ onPress, disabled = false, filled = true, className }: SendButtonProps) {
  const scale = useSharedValue(1);

  const handlePressIn = () => {
    if (!disabled) {
      scale.value = withSpring(0.9, SPRING_CONFIG);
    }
  };

  const handlePressOut = () => {
    scale.value = withSpring(1, SPRING_CONFIG);
  };

  const handlePress = (_event: GestureResponderEvent) => {
    onPress();
  };

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));

  const iconColor = filled ? colors.secondary[500] : colors.primary[300];

  return (
    <Animated.View style={animatedStyle}>
      <Pressable
        onPress={handlePress}
        onPressIn={handlePressIn}
        onPressOut={handlePressOut}
        disabled={disabled}
        accessibilityRole="button"
        accessibilityLabel={en.shared.sendButtonLabel}
        accessibilityState={{ disabled }}
        className={cn(
          'items-center justify-center rounded-full',
          filled ? 'bg-primary-400' : 'border-[1.5px] border-primary-300 bg-transparent',
          disabled && 'opacity-40',
          className,
        )}
        style={{ width: BUTTON_SIZE, height: BUTTON_SIZE }}
      >
        <Feather name="arrow-up" size={20} color={iconColor} />
      </Pressable>
    </Animated.View>
  );
}
