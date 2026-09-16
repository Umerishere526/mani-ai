import { useState } from "react";
import { router } from "expo-router";
import { Pressable, ScrollView, View, type NativeScrollEvent, type NativeSyntheticEvent } from "react-native";
import { AppHeader, CardGradient, Text } from "@/components/shared";
import { useResponsiveTypography } from "@/hooks/useResponsiveTypography";
import { CATEGORY_DISPLAY_ORDER } from "@/lib/exercise-categories";
import en from "@/dictionaries/en.json";

export default function ExerciseCategoriesScreen() {
  const typography = useResponsiveTypography();
  const [isScrolled, setIsScrolled] = useState(false);

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
        <View className="gap-3">
          {CATEGORY_DISPLAY_ORDER.map((category) => {
            const info = en.exercises.categories[category];
            return (
              <Pressable
                key={category}
                onPress={() => router.push(`/exercises/${category}`)}
                className="overflow-hidden rounded-lg p-4 active:opacity-70"
              >
                <CardGradient />
                <Text
                  className="mb-1 font-sans-semibold text-white"
                  style={{ fontSize: typography.body.fontSize, lineHeight: typography.body.lineHeight }}
                >
                  {info.title}
                </Text>
                <Text className="text-sm leading-5 text-white/80">{info.description}</Text>
              </Pressable>
            );
          })}
        </View>
        <Text className="mt-6 text-center text-base text-white/70">{en.exercises.comingSoon}</Text>
      </ScrollView>
    </View>
  );
}
