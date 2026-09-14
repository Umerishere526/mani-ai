// ABOUTME: Bottom-sheet modal with crisis safety resources, sliding up over a dimmed
// ABOUTME: backdrop. Content lives in CrisisGuidance; this file is just the shell/animation.

import { useEffect } from 'react';
import { Modal, Pressable, ScrollView, useWindowDimensions, View } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@react-native-vector-icons/ionicons/static';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Animated, { useSharedValue, useAnimatedStyle, withTiming } from 'react-native-reanimated';
import { colors } from '@/lib/tokens';
import en from '@/dictionaries/en.json';
import { CrisisGuidance } from './crisis-guidance';

export interface CrisisDrawerProps {
  visible: boolean;
  onClose: () => void;
}

export function CrisisDrawer({ visible, onClose }: CrisisDrawerProps) {
  const insets = useSafeAreaInsets();
  const { height: screenHeight } = useWindowDimensions();
  const slide = useSharedValue(screenHeight);
  const backdrop = useSharedValue(0);

  useEffect(() => {
    slide.value = withTiming(visible ? 0 : screenHeight, { duration: visible ? 350 : 300 });
    backdrop.value = withTiming(visible ? 1 : 0, { duration: visible ? 350 : 300 });
  }, [visible, screenHeight, slide, backdrop]);

  const backdropStyle = useAnimatedStyle(() => ({ opacity: backdrop.value * 0.3 }));
  const drawerStyle = useAnimatedStyle(() => ({ transform: [{ translateY: slide.value }] }));

  return (
    <Modal visible={visible} transparent animationType="none" onRequestClose={onClose}>
      <View className="flex-1 justify-end">
        <Animated.View className="absolute inset-0 bg-black" style={backdropStyle}>
          <Pressable
            className="absolute inset-0"
            onPress={onClose}
            accessibilityRole="button"
            accessibilityLabel={en.crisis.closeDrawerLabel}
          />
        </Animated.View>

        <Animated.View
          className="overflow-hidden rounded-t-xl"
          style={[{ maxHeight: screenHeight * 0.9, paddingBottom: insets.bottom + 32 }, drawerStyle]}
        >
          <LinearGradient colors={[colors.primary[500], colors.primary[700]]} className="absolute inset-0" />

          <Pressable
            className="absolute right-5 top-5 z-10 p-2"
            onPress={onClose}
            accessibilityRole="button"
            accessibilityLabel={en.crisis.closeLabel}
          >
            <Ionicons name="close" size={24} color={colors.secondary[500]} />
          </Pressable>

          <ScrollView className="px-8 pt-14" showsVerticalScrollIndicator={false} bounces={false}>
            <CrisisGuidance />
          </ScrollView>
        </Animated.View>
      </View>
    </Modal>
  );
}
