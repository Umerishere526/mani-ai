// ABOUTME: Exercise player screen — title, listed duration, breathing sphere and description,
// ABOUTME: then a play/pause control with time remaining, and a completion step when it ends.

import { useEffect } from "react";
import { router, useLocalSearchParams } from "expo-router";
import { ScrollView, View } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import Animated, { useSharedValue, useAnimatedStyle, withTiming } from "react-native-reanimated";
import { AppHeader, GradientSphere, SecondaryButton, Text } from "@/components/shared";
import { ExerciseComplete, ExercisePlaybackControl, LibraryLoading } from "@/components/exercises";
import { colors } from "@/lib/tokens";
import { useResponsiveDimensions } from "@/hooks/useResponsiveDimensions";
import { useExercisePlayback } from "@/hooks/useExercisePlayback";
import { useLoad } from "@/hooks/useLoad";
import { getExercise } from "@/lib/api/exercises";
import { formatDuration } from "@/lib/utils";
import en from "@/dictionaries/en.json";

const GRADIENT_COLORS = [colors.primary[700], colors.primary[900]] as const;

export default function ExercisePlayerScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const insets = useSafeAreaInsets();
  const { isSmallScreen, isLargeScreen } = useResponsiveDimensions();
  const loaded = useLoad(id ?? null, () => getExercise(id ?? ""));
  const exercise = loaded.data;
  const playback = useExercisePlayback((exercise?.durationMinutes ?? 0) * 60_000);
  const descriptionOpacity = useSharedValue(1);

  useEffect(() => {
    if (playback.hasStarted) {
      descriptionOpacity.value = withTiming(0, { duration: 500 });
    }
  }, [playback.hasStarted, descriptionOpacity]);

  const descriptionStyle = useAnimatedStyle(() => ({ opacity: descriptionOpacity.value }));

  if (!exercise) {
    return (
      <View className="flex-1 items-center justify-center">
        <LinearGradient colors={GRADIENT_COLORS} className="absolute inset-0" />
        <AppHeader showBack backIcon="x" transparent onBack={() => router.back()} />
        <LibraryLoading failed={loaded.failed} onRetry={loaded.retry} />
      </View>
    );
  }

  return (
    <View className="flex-1">
      <LinearGradient colors={GRADIENT_COLORS} className="absolute inset-0" />
      <AppHeader showBack backIcon="x" transparent onBack={() => router.back()} />

      {/* Scrolls only when large text makes the screen taller than the phone, so the closing buttons stay reachable. */}
      <ScrollView contentContainerClassName="grow" bounces={false} showsVerticalScrollIndicator={false}>
        <View className="items-center px-4" style={{ marginTop: 80 }}>
          <Text className="font-sans-semibold text-base text-white">{exercise.title}</Text>
          {exercise.durationMinutes === null ? null : (
            <Text className="mt-4 text-lg text-white/60">{formatDuration(exercise.durationMinutes)}</Text>
          )}
        </View>

        <View className="items-center" style={{ marginTop: isSmallScreen ? 36 : 60, marginBottom: isSmallScreen ? 36 : 60 }}>
          <GradientSphere size={100} animated={playback.isPlaying} />
        </View>

        <Animated.View
          className="max-w-80 self-center px-6"
          style={[isLargeScreen && { maxWidth: 380 }, descriptionStyle]}
        >
          <Text className={isLargeScreen ? "text-center text-base leading-6 text-secondary-500" : "text-center text-sm leading-5 text-secondary-500"}>
            {exercise.description}
          </Text>
        </Animated.View>

        <View className="flex-1" />

        <View className="items-center px-4" style={{ paddingBottom: insets.bottom + 32 }}>
          {!exercise.recorded && <Text className="text-base text-white/60">{en.exercises.comingSoonItem}</Text>}
          {exercise.recorded && !playback.hasStarted && (
            <SecondaryButton
              label={en.exercises.begin}
              onPress={playback.togglePlayback}
              className="self-stretch"
              accessibilityLabel={en.exercises.beginLabel}
              accessibilityHint={en.exercises.beginHint}
            />
          )}
          {playback.hasStarted && !playback.isComplete && (
            <ExercisePlaybackControl
              isPlaying={playback.isPlaying}
              progress={playback.progress}
              remainingSeconds={playback.remainingSeconds}
              onToggle={playback.togglePlayback}
            />
          )}
          {playback.isComplete && (
            <ExerciseComplete
              onContinueChatting={() => router.dismissTo("/chat")}
              onVisitLibrary={() => router.dismissTo("/exercises")}
            />
          )}
        </View>
      </ScrollView>
    </View>
  );
}
