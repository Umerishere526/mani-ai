import { useState } from "react";
import { router, useLocalSearchParams } from "expo-router";
import {
  Pressable,
  ScrollView,
  View,
  type NativeScrollEvent,
  type NativeSyntheticEvent,
} from "react-native";
import { Feather } from "@react-native-vector-icons/feather";
import { AppHeader, Text } from "@/components/shared";
import { useResponsiveTypography } from "@/hooks/useResponsiveTypography";
import { formatDuration } from "@/lib/utils";
import { EXERCISES_BY_CATEGORY } from "@/lib/placeholder-exercises";
import en from "@/dictionaries/en.json";
import type { TopicId } from "@/types/exercise";

export default function ExerciseCategoryScreen() {
  const { category } = useLocalSearchParams<{ category: TopicId }>();
  const [isScrolled, setIsScrolled] = useState(false);
  const typography = useResponsiveTypography();
  const exercises = category ? (EXERCISES_BY_CATEGORY[category] ?? []) : [];

  const handleScroll = (event: NativeSyntheticEvent<NativeScrollEvent>) => {
    setIsScrolled(event.nativeEvent.contentOffset.y > 0);
  };

  return (
    <View className="flex-1 bg-primary-900">
      <AppHeader showBack hideBorder={!isScrolled} onBack={() => router.back()} />
      <ScrollView className="flex-1 px-4 pt-4" onScroll={handleScroll} scrollEventThrottle={16}>
        {exercises.length === 0 ? (
          <View className="items-center py-8">
            <Text className="text-base text-white/80">{en.exercises.empty}</Text>
          </View>
        ) : (
          <View>
            {exercises.map((exercise) => (
              <View key={exercise.id}>
                <Pressable
                  onPress={() => router.push(`/exercises/player/${exercise.id}`)}
                  className="flex-row items-center py-4 active:opacity-70"
                >
                  <View className="flex-1">
                    <Text
                      className="mb-1 text-white/60"
                      style={{ fontSize: typography.caption.fontSize - 2, lineHeight: typography.caption.lineHeight }}
                    >
                      {formatDuration(exercise.durationMinutes)} • {exercise.type}
                    </Text>
                    <Text
                      className="font-sans-semibold text-white"
                      style={{ fontSize: typography.body.fontSize, lineHeight: typography.body.lineHeight }}
                    >
                      {exercise.title}
                    </Text>
                  </View>
                  <Feather name="chevron-right" size={20} color="rgba(255,255,255,0.4)" />
                </Pressable>
                <View className="h-px bg-white/10" />
              </View>
            ))}
          </View>
        )}
      </ScrollView>
    </View>
  );
}
