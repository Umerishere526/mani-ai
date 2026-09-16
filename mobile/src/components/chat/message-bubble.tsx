// ABOUTME: A single chat message — a filled bubble for the user, full-width markdown for
// ABOUTME: Mani. Both animate in with a fade + slide on mount (skippable via `animate`).

import { useEffect, useMemo } from 'react';
import { View } from 'react-native';
import Markdown from 'react-native-marked';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  interpolate,
  Easing,
} from 'react-native-reanimated';
import type { Message } from '@/types/chat';
import { Text } from '@/components/shared';
import { NoScaleRenderer } from './no-scale-renderer';
import { markdownStyles } from './markdown-styles';

export interface MessageBubbleProps {
  message: Message;
  animate?: boolean;
}

const DURATION_USER = 200;
const DURATION_MANI = 300;

export function MessageBubble({ message, animate = true }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const progress = useSharedValue(animate ? 0 : 1);
  const renderer = useMemo(() => new NoScaleRenderer(), []);

  useEffect(() => {
    if (!animate) return;
    progress.value = withTiming(1, {
      duration: isUser ? DURATION_USER : DURATION_MANI,
      easing: isUser ? Easing.out(Easing.back(1.2)) : Easing.out(Easing.ease),
    });
  }, [animate, isUser, progress]);

  const animatedStyle = useAnimatedStyle(() => ({
    opacity: progress.value,
    transform: [
      { translateX: interpolate(progress.value, [0, 1], [isUser ? 20 : -15, 0]) },
      { scale: interpolate(progress.value, [0, 1], [isUser ? 0.95 : 0.96, 1]) },
    ],
  }));

  if (isUser) {
    return (
      <View className="my-1 items-end px-4">
        <Animated.View
          className="max-w-[80%] rounded-lg rounded-tr-sm bg-primary-600 px-3 py-2"
          style={animatedStyle}
          accessible
          accessibilityRole="text"
          accessibilityLabel={`You: ${message.content}`}
        >
          <Text className="text-base leading-6">{message.content}</Text>
        </Animated.View>
      </View>
    );
  }

  return (
    <Animated.View
      className="my-2 px-4"
      style={animatedStyle}
      accessible
      accessibilityRole="text"
      accessibilityLabel={`Mani: ${message.content}`}
    >
      <Markdown
        value={message.content}
        styles={markdownStyles}
        renderer={renderer}
        flatListProps={{
          style: { backgroundColor: 'transparent' },
          contentContainerStyle: { backgroundColor: 'transparent' },
        }}
      />
    </Animated.View>
  );
}
