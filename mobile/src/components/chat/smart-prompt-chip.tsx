// ABOUTME: A tappable suggestion chip below a Mani message. Splits the prompt's label on
// ABOUTME: its first newline into a bold title and an optional description line.

import { Pressable, View } from 'react-native';
import Animated, { useSharedValue, useAnimatedStyle, withSpring } from 'react-native-reanimated';
import type { SmartPrompt } from '@/types/chat';
import { Text } from '@/components/shared';

export interface SmartPromptChipProps {
  prompt: SmartPrompt;
  onPress: (prompt: SmartPrompt) => void;
}

const SPRING_CONFIG = { duration: 200, dampingRatio: 0.9 };

function splitPromptLabel(label: string): { title: string; description?: string } {
  const lines = label.split('\n');
  if (lines.length > 1) {
    return { title: lines[0], description: lines.slice(1).join('\n').trim() };
  }
  return { title: label };
}

export function SmartPromptChip({ prompt, onPress }: SmartPromptChipProps) {
  const scale = useSharedValue(1);
  const { title, description } = splitPromptLabel(prompt.label);

  const handlePress = () => onPress(prompt);
  const handlePressIn = () => {
    scale.value = withSpring(0.96, SPRING_CONFIG);
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
        accessibilityLabel={prompt.label}
        className="self-start rounded-full bg-primary-400 px-6 py-4"
      >
        <View>
          <Text className="font-sans-semibold text-[15px]" numberOfLines={2}>
            {title}
          </Text>
          {description && (
            <Text className="mt-1 text-sm text-secondary-600" numberOfLines={2}>
              {description}
            </Text>
          )}
        </View>
      </Pressable>
    </Animated.View>
  );
}
