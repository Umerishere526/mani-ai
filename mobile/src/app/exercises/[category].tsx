// ABOUTME: Library topic screen — the topic's own exercises, then those it lists from other topics under each
// ABOUTME: subcategory; a recorded one opens the player, one not yet recorded says Coming soon.

import { useState } from "react";
import { router, useLocalSearchParams } from "expo-router";
import { ScrollView, View, type NativeScrollEvent, type NativeSyntheticEvent } from "react-native";
import { AppHeader, Text } from "@/components/shared";
import { ExerciseRow, LibraryLoading } from "@/components/exercises";
import { useLoad } from "@/hooks/useLoad";
import { getTopicExercises } from "@/lib/api/exercises";
import { groupBySubcategory } from "@/lib/library";
import en from "@/dictionaries/en.json";

export default function ExerciseCategoryScreen() {
  const { category } = useLocalSearchParams<{ category: string }>();
  const [isScrolled, setIsScrolled] = useState(false);
  const exercises = useLoad(category ?? null, () => getTopicExercises(category ?? ""));
  const groups = groupBySubcategory(exercises.data ?? []);

  const handleScroll = (event: NativeSyntheticEvent<NativeScrollEvent>) => {
    setIsScrolled(event.nativeEvent.contentOffset.y > 0);
  };

  return (
    <View className="flex-1 bg-primary-900">
      <AppHeader showBack hideBorder={!isScrolled} onBack={() => router.back()} />
      <ScrollView className="flex-1 px-4 pt-4" onScroll={handleScroll} scrollEventThrottle={16}>
        {exercises.data === null ? (
          <LibraryLoading failed={exercises.failed} onRetry={exercises.retry} />
        ) : groups.length === 0 ? (
          <View className="items-center py-8">
            <Text className="text-base text-white/80">{en.exercises.empty}</Text>
          </View>
        ) : (
          groups.map((group) => (
            <View key={group.subcategory ?? ""} className="mb-4">
              {group.subcategory ? (
                <Text className="mt-2 font-sans-semibold text-base text-white/80" accessibilityRole="header">
                  {group.subcategory}
                </Text>
              ) : null}
              {group.exercises.map((exercise) => (
                <ExerciseRow key={exercise.id} exercise={exercise} />
              ))}
            </View>
          ))
        )}
      </ScrollView>
    </View>
  );
}
