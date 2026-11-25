// ABOUTME: The crisis pop-up that opens by itself on a crisis or a pause, as the client drew it (R99): the crisis
// ABOUTME: lines first, then the library and Get help now; while paused, the pause's length and end as secondary text.

import { Modal, Pressable, ScrollView, View } from 'react-native';
import { router } from 'expo-router';
import { Ionicons } from '@react-native-vector-icons/ionicons';
import en from '@/dictionaries/en.json';
import { ANIMATION_TIMINGS } from '@/lib/animation-timings';
import { colors } from '@/lib/tokens';
import { useChatSafety, useDrawer } from '@/providers';
import { PrimaryButton, Text } from '@/components/shared';
import { CrisisHelpLines } from './crisis-help-lines';
import { CrisisPauseNotice } from './crisis-pause-notice';

export function CrisisScreen() {
  const { pause, isScreenVisible, emergencyFirst, closeScreen } = useChatSafety();
  const { openCrisisDrawer } = useDrawer();
  const copy = en.crisis.pause;

  const visitLibrary = () => {
    closeScreen();
    router.push('/exercises');
  };
  const getHelpNow = () => {
    closeScreen();
    setTimeout(openCrisisDrawer, ANIMATION_TIMINGS.DRAWER_CHAIN_DELAY);
  };

  return (
    <Modal visible={isScreenVisible} transparent animationType="fade" onRequestClose={closeScreen}>
      <View className="flex-1 justify-center bg-black/60 px-4 py-12">
        <View className="max-h-full overflow-hidden rounded-xl bg-primary-700">
          <Pressable
            className="absolute right-3 top-3 z-10 p-3"
            onPress={closeScreen}
            accessibilityRole="button"
            accessibilityLabel={copy.closeLabel}
          >
            <Ionicons name="close" size={24} color={colors.secondary[500]} />
          </Pressable>

          <ScrollView contentContainerClassName="items-center gap-5 px-6 pb-8 pt-14" bounces={false}>
            <Text className="text-center font-sans-semibold text-2xl" accessibilityRole="header">
              {pause ? copy.title : en.crisis.title}
            </Text>

            <CrisisHelpLines emergencyFirst={emergencyFirst} />

            {pause ? <Text className="text-center text-base leading-6">{copy.library}</Text> : null}
            <View className="w-full gap-3">
              <PrimaryButton label={copy.getHelpNow} onPress={getHelpNow} className="w-full" />
              <PrimaryButton label={copy.visitLibrary} onPress={visitLibrary} className="w-full" />
            </View>

            {pause ? <CrisisPauseNotice pause={pause} /> : null}
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}
