// ABOUTME: The slide-in navigation drawer opened from AppHeader's menu button — nav links,
// ABOUTME: new-chat action, conversation history, and a pinned profile row at the bottom.

import { useEffect } from 'react';
import { Pressable, useWindowDimensions, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Feather } from '@react-native-vector-icons/feather/static';
import Animated, { useSharedValue, useAnimatedStyle, withTiming, Easing } from 'react-native-reanimated';
import { colors } from '@/lib/tokens';
import { ANIMATION_TIMINGS } from '@/lib/animation-timings';
import en from '@/dictionaries/en.json';
import type { ThreadListItem } from '@/types/chat';
import { Text } from '@/components/shared';
import { ChatDrawerNavSection } from './chat-drawer-nav-section';
import { ChatDrawerThreadList } from './chat-drawer-thread-list';
import { ChatDrawerProfileFooter } from './chat-drawer-profile-footer';

const PROFILE_CONTENT_HEIGHT = 16 + 40 + 12; // paddingTop + avatar + paddingBottom
const DRAWER_WIDTH_RATIO = 0.75;

export interface ChatDrawerProps {
  visible: boolean;
  threads: ThreadListItem[];
  nickname?: string | null;
  onClose: () => void;
  onOpenCrisisDrawer: () => void;
  onNewChat: () => void;
  onNavigateHome: () => void;
  onNavigateLibrary: () => void;
  onNavigateSettings: () => void;
  onThreadPress: (threadId: string) => void;
}

export function ChatDrawer({
  visible,
  threads,
  nickname,
  onClose,
  onOpenCrisisDrawer,
  onNewChat,
  onNavigateHome,
  onNavigateLibrary,
  onNavigateSettings,
  onThreadPress,
}: ChatDrawerProps) {
  const insets = useSafeAreaInsets();
  const { width: screenWidth } = useWindowDimensions();
  const drawerWidth = screenWidth * DRAWER_WIDTH_RATIO;

  const slide = useSharedValue(0);
  const overlay = useSharedValue(0);

  useEffect(() => {
    slide.value = withTiming(visible ? 1 : 0, {
      duration: visible ? ANIMATION_TIMINGS.DRAWER_SLIDE_IN : ANIMATION_TIMINGS.DRAWER_SLIDE_OUT,
      easing: visible ? Easing.out(Easing.quad) : Easing.in(Easing.quad),
    });
    overlay.value = withTiming(visible ? 1 : 0, {
      duration: visible ? ANIMATION_TIMINGS.DRAWER_OVERLAY_IN : ANIMATION_TIMINGS.DRAWER_SLIDE_OUT,
      easing: visible ? Easing.out(Easing.quad) : Easing.in(Easing.quad),
    });
  }, [visible, slide, overlay]);

  const overlayStyle = useAnimatedStyle(() => ({ opacity: overlay.value * 0.5 }));
  const drawerStyle = useAnimatedStyle(() => ({
    transform: [{ translateX: (slide.value - 1) * drawerWidth }],
  }));

  const withCloseDelay = (action: () => void, delay: number = ANIMATION_TIMINGS.DRAWER_NAVIGATION_DELAY) => {
    onClose();
    setTimeout(action, delay);
  };

  const gradientBottomOffset = PROFILE_CONTENT_HEIGHT + insets.bottom + 8;

  return (
    <View className="absolute inset-0" pointerEvents={visible ? 'auto' : 'none'}>
      <Animated.View className="absolute inset-0 bg-primary-900" style={overlayStyle}>
        <Pressable className="absolute inset-0" onPress={onClose} accessibilityRole="button" accessibilityLabel={en.chat.closeDrawerLabel} />
      </Animated.View>

      <Animated.View
        className="absolute bottom-0 left-0 top-0 border-r border-secondary-500/10 bg-primary-900"
        style={[{ width: drawerWidth, paddingTop: insets.top + 16, paddingBottom: insets.bottom }, drawerStyle]}
      >
        <Pressable
          onPress={onClose}
          className="mb-4 mr-2 self-end p-3"
          accessibilityLabel={en.chat.closeMenuLabel}
          accessibilityRole="button"
          hitSlop={8}
        >
          <Feather name="x" size={24} color={colors.secondary[500]} />
        </Pressable>

        <ChatDrawerNavSection
          onNavigateHome={() => withCloseDelay(onNavigateHome)}
          onNavigateLibrary={() => withCloseDelay(onNavigateLibrary)}
          onUrgentHelp={() => withCloseDelay(onOpenCrisisDrawer, ANIMATION_TIMINGS.DRAWER_CHAIN_DELAY)}
        />

        <View className="mx-4 my-4 h-px bg-secondary-500/10" />

        <Pressable
          onPress={() => withCloseDelay(onNewChat)}
          className="mx-4 mb-3 flex-row items-center rounded-xl px-3 py-3 active:bg-secondary-500/10"
          accessibilityLabel={en.chat.startNewConversationLabel}
          accessibilityRole="button"
        >
          <Feather name="edit" size={18} color={colors.secondary[500]} style={{ marginRight: 12 }} />
          <Text className="font-sans-medium text-[15px]">{en.chat.startNewConversation}</Text>
        </Pressable>

        <ChatDrawerThreadList
          threads={threads}
          onThreadPress={(threadId) => withCloseDelay(() => onThreadPress(threadId))}
          contentBottomPadding={PROFILE_CONTENT_HEIGHT + insets.bottom + 8}
        />

        <ChatDrawerProfileFooter
          nickname={nickname}
          onPress={() => withCloseDelay(onNavigateSettings)}
          gradientBottomOffset={gradientBottomOffset}
          paddingBottom={12 + insets.bottom + 8}
        />
      </Animated.View>
    </View>
  );
}
