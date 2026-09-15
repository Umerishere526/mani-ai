import { useEffect, useRef, useState } from "react";
import { router, useLocalSearchParams } from "expo-router";
import { Pressable, View } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { Feather } from "@react-native-vector-icons/feather";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import Animated, { useSharedValue, useAnimatedStyle, withTiming } from "react-native-reanimated";
import { AppHeader, CircularProgressButton, GradientSphere, SecondaryButton, Text } from "@/components/shared";
import { colors } from "@/lib/tokens";
import { useResponsiveDimensions } from "@/hooks/useResponsiveDimensions";
import { formatDuration } from "@/lib/utils";
import { getExerciseById } from "@/lib/placeholder-exercises";
import en from "@/dictionaries/en.json";

const GRADIENT_COLORS = [colors.primary[700], colors.primary[900]] as const;
const SIMULATED_DURATION_MS = 30_000;
const PROGRESS_TICK_MS = 250;

// function formatTime(millis: number): string {
//   const totalSeconds = Math.floor(millis / 1000);
//   const minutes = Math.floor(totalSeconds / 60);
//   const seconds = totalSeconds % 60;
//   return `${minutes}:${seconds.toString().padStart(2, "0")}`;
// }

export default function ExercisePlayerScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const insets = useSafeAreaInsets();
  const { isSmallScreen, isLargeScreen } = useResponsiveDimensions();
  const exercise = id ? getExerciseById(id) : undefined;

  const [isPlaying, setIsPlaying] = useState(false);
  const [hasStarted, setHasStarted] = useState(false);
  const [elapsedMs, setElapsedMs] = useState(0);
  const descriptionOpacity = useSharedValue(1);
  const intervalRef = useRef<ReturnType<typeof setInterval>>(undefined);

  useEffect(() => {
    if (!isPlaying) return;
    intervalRef.current = setInterval(() => {
      setElapsedMs((prev) => Math.min(prev + PROGRESS_TICK_MS, SIMULATED_DURATION_MS));
    }, PROGRESS_TICK_MS);
    return () => clearInterval(intervalRef.current);
  }, [isPlaying]);

  useEffect(() => {
    if (hasStarted) {
      descriptionOpacity.value = withTiming(0, { duration: 500 });
    }
  }, [hasStarted, descriptionOpacity]);

  const descriptionStyle = useAnimatedStyle(() => ({ opacity: descriptionOpacity.value }));

  const handleTogglePlayback = () => {
    if (!hasStarted) setHasStarted(true);
    setIsPlaying((prev) => !prev);
  };

  if (!exercise) {
    return (
      <View className="flex-1 items-center justify-center">
        <LinearGradient colors={GRADIENT_COLORS} className="absolute inset-0" />
        <Text className="text-base text-[#FF6B6B]">{en.exercises.failedToLoadExercise}</Text>
      </View>
    );
  }

  return (
    <View className="flex-1">
      <LinearGradient colors={GRADIENT_COLORS} className="absolute inset-0" />
      <AppHeader showBack backIcon="x" transparent onBack={() => router.back()} />

      <View className="items-center px-4" style={{ marginTop: 80 }}>
        <Text className="font-sans-semibold text-base text-white">{exercise.title}</Text>
        <Text className="mt-4 text-lg text-white/60">{formatDuration(exercise.durationMinutes)}</Text>
      </View>

      <View className="items-center" style={{ marginTop: isSmallScreen ? 36 : 60, marginBottom: isSmallScreen ? 36 : 60 }}>
        <GradientSphere size={100} animated={isPlaying} />
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
        {!hasStarted && (
          <SecondaryButton
            label={en.exercises.begin}
            onPress={handleTogglePlayback}
            className="self-stretch"
            accessibilityLabel={en.exercises.beginLabel}
            accessibilityHint={en.exercises.beginHint}
          />
        )}
      </View>

      {hasStarted && (
        <View className="absolute left-0 right-0 items-center" style={{ bottom: insets.bottom + 32 }}>
          {/* <Text
            className="mb-4 font-sans-semibold text-2xl text-white"
            accessibilityLabel={`${en.exercises.elapsedTimeLabel} ${formatTime(elapsedMs)}`}
            accessibilityRole="timer"
          >
            {formatTime(elapsedMs)}
          </Text> */}
          <CircularProgressButton
            progress={elapsedMs / SIMULATED_DURATION_MS}
            size={88}
            strokeWidth={4}
            progressColor="rgba(255,255,255,0.5)"
            trackColor="rgba(255,255,255,0.15)"

          >
            <Pressable
              onPress={handleTogglePlayback}
              className={isPlaying ? "h-18 w-18 items-center justify-center rounded-full bg-white/8" : "h-18 w-18 items-center justify-center rounded-full bg-secondary-500"}
              accessibilityRole="button"
              accessibilityLabel={isPlaying ? en.exercises.pauseLabel : en.exercises.playLabel}
            >
              <Feather
                name={isPlaying ? "pause" : "play"}
                size={32}
                color={isPlaying ? colors.text.inverse : colors.primary[500]}
                style={!isPlaying ? { marginLeft: 4 } : undefined}
              />
            </Pressable>
          </CircularProgressButton>
        </View>
      )}
    </View>
  );
}
