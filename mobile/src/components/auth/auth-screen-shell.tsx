// ABOUTME: Shared shell for the account-modification screens (change email, change
// ABOUTME: password) — dark background, noise overlay, back-button header, fade-in form.

import { useEffect, type ReactNode } from "react";
import { Image, KeyboardAvoidingView, Platform, Pressable, ScrollView, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Ionicons } from "@react-native-vector-icons/ionicons/static";
import Animated, { useSharedValue, useAnimatedStyle, withTiming, Easing } from "react-native-reanimated";
import { colors } from "@/lib/tokens";
import { Text } from "@/components/shared";

export interface AuthScreenShellProps {
  title: string;
  onBack: () => void;
  backAccessibilityLabel: string;
  children: ReactNode;
}

export function AuthScreenShell({ title, onBack, backAccessibilityLabel, children }: AuthScreenShellProps) {
  const insets = useSafeAreaInsets();
  const opacity = useSharedValue(0);
  const translateY = useSharedValue(20);

  useEffect(() => {
    opacity.value = withTiming(1, { duration: 400, easing: Easing.out(Easing.cubic) });
    translateY.value = withTiming(0, { duration: 400, easing: Easing.out(Easing.cubic) });
  }, [opacity, translateY]);

  const formStyle = useAnimatedStyle(() => ({
    opacity: opacity.value,
    transform: [{ translateY: translateY.value }],
  }));

  return (
    <View className="flex-1 bg-primary-900">
      <View className="absolute inset-0 opacity-50" pointerEvents="none">
        <Image source={require("@/assets/images/noise.png")} className="h-full w-full" resizeMode="repeat" />
      </View>

      <View className="flex-row items-center px-4 pb-4" style={{ paddingTop: insets.top + 8 }}>
        <Pressable
          onPress={onBack}
          className="h-11 w-11 items-center justify-center"
          hitSlop={12}
          accessibilityLabel={backAccessibilityLabel}
          accessibilityRole="button"
        >
          <Ionicons name="chevron-back" size={28} color={colors.secondary[500]} />
        </Pressable>
        <Text className="flex-1 text-center font-sans-semibold text-lg">{title}</Text>
        <View className="w-11" />
      </View>

      <KeyboardAvoidingView className="flex-1" behavior={Platform.OS === "ios" ? "padding" : "height"}>
        <ScrollView
          className="flex-1 px-6"
          contentContainerStyle={{ flexGrow: 1, paddingBottom: insets.bottom + 32 }}
          keyboardShouldPersistTaps="handled"
        >
          <Animated.View className="pt-8" style={formStyle}>
            {children}
          </Animated.View>
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
}
