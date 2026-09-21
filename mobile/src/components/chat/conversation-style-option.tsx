// ABOUTME: A single tappable conversation-style card (Directive/Supportive/Reflective) shown
// ABOUTME: in ConversationStylePicker — title, description, and a spring press animation.

import { Pressable, View } from 'react-native';
import Animated, { useSharedValue, useAnimatedStyle, withSpring } from 'react-native-reanimated';
import en from '@/dictionaries/en.json';
import type { ConversationStyle } from '@/types/chat';
import { CardGradient, Text } from '@/components/shared';

export interface ConversationStyleOptionProps {
  style: ConversationStyle;
  onPress: (style: ConversationStyle) => void;
}

const SPRING_CONFIG = { duration: 200, dampingRatio: 0.9 };

export function ConversationStyleOption({ style, onPress }: ConversationStyleOptionProps) {
  const scale = useSharedValue(1);
  const { label, description } = en.chat.styles[style];

  const handlePress = () => onPress(style);
  const handlePressIn = () => {
    scale.value = withSpring(0.97, SPRING_CONFIG);
  };
  const handlePressOut = () => {
    scale.value = withSpring(1, SPRING_CONFIG);
  };

  const animatedStyle = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));

  return (
    <Animated.View style={animatedStyle}>
      <Pressable
        onPress={handlePress}
        onPressIn={handlePressIn}
        onPressOut={handlePressOut}
        accessibilityRole="button"
        accessibilityLabel={label}
        accessibilityHint={description}
        className="w-full rounded-3xl overflow-hidden px-6 py-4"
      >
        <CardGradient />
        <View>
          <Text className="font-sans-semibold text-[17px]">{label}</Text>
          <Text className="mt-1 text-sm text-secondary-600">{description}</Text>
        </View>
      </Pressable>
    </Animated.View>
  );
}
