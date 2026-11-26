// ABOUTME: Library screen — the client's topics in her order as gradient cards, each with its blurb, each opening
// ABOUTME: its topic's exercises. Read from GET /v1/exercises/topics.

import { useState } from "react";
import { router } from "expo-router";
import { Pressable, ScrollView, View, type NativeScrollEvent, type NativeSyntheticEvent } from "react-native";
import { AppHeader, CardGradient, Text } from "@/components/shared";
import { LibraryLoading } from "@/components/exercises";
import { useLoad } from "@/hooks/useLoad";
import { useResponsiveTypography } from "@/hooks/useResponsiveTypography";
import { getTopics } from "@/lib/api/exercises";
import en from "@/dictionaries/en.json";

export default function ExerciseCategoriesScreen() {
  const typography = useResponsiveTypography();
  const [isScrolled, setIsScrolled] = useState(false);
  const topics = useLoad("topics", getTopics);

  const handleScroll = (event: NativeSyntheticEvent<NativeScrollEvent>) => {
    setIsScrolled(event.nativeEvent.contentOffset.y > 0);
  };

  return (
    <View className="flex-1 bg-primary-900">
      <AppHeader hideBorder={!isScrolled} />
      <ScrollView
        className="flex-1 px-4 pt-4"
        contentContainerStyle={{ paddingBottom: 16 }}
        onScroll={handleScroll}
        scrollEventThrottle={16}
      >
        {topics.data === null ? (
          <LibraryLoading failed={topics.failed} onRetry={topics.retry} />
        ) : (
          <View className="gap-3">
            {topics.data.map((topic) => (
              <Pressable
                key={topic.id}
                onPress={() => router.push(`/exercises/${topic.id}`)}
                className="overflow-hidden rounded-lg p-4 active:opacity-70"
                accessibilityRole="button"
                accessibilityLabel={topic.title}
                accessibilityHint={topic.blurb}
              >
                <CardGradient />
                <Text
                  className="mb-1 font-sans-semibold text-white"
                  style={{ fontSize: typography.body.fontSize, lineHeight: typography.body.lineHeight }}
                >
                  {topic.title}
                </Text>
                {topic.blurb ? <Text className="text-sm leading-5 text-white/80">{topic.blurb}</Text> : null}
              </Pressable>
            ))}
          </View>
        )}
        <Text className="mt-6 text-center text-base text-white/70">{en.exercises.comingSoon}</Text>
      </ScrollView>
    </View>
  );
}
