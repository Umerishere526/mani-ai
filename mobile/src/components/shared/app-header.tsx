// ABOUTME: The app's shared top bar — hamburger/back button, optional title, and a
// ABOUTME: Get Help Now + new-chat action pair (or custom right content) on the other side.

import type { ReactNode } from 'react';
import { Pressable, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Feather } from '@react-native-vector-icons/feather/static';
import { colors } from '@/lib/tokens';
import { cn } from '@/lib/utils';
import en from '@/dictionaries/en.json';
import { useDrawer } from '@/providers/drawer-provider';
import { Text } from './text';

export interface AppHeaderProps {
  /** Optional title to display in center */
  title?: string;
  /** Show a back button instead of hamburger menu */
  showBack?: boolean;
  /** Icon to use for back button (default: chevron-left) */
  backIcon?: 'chevron-left' | 'x';
  /** Called when the back button is pressed. No-ops if omitted. */
  onBack?: () => void;
  /** Show the new chat button (default: true) */
  showNewChat?: boolean;
  /** Custom right content instead of default buttons */
  rightContent?: ReactNode;
  /** Make the header background transparent */
  transparent?: boolean;
  /** Custom background color class for the Get Help Now button */
  helpButtonClassName?: string;
  /** Custom color for menu and edit icons */
  iconColor?: string;
  /** Called when the new-chat button is pressed */
  onNewChatPress?: () => void;
  /** Show bottom border (useful with transparent background) */
  showBorder?: boolean;
  /** Hide the default bottom border */
  hideBorder?: boolean;
  /** Position header absolutely over content */
  absolute?: boolean;
}

export function AppHeader({
  title,
  showBack = false,
  backIcon = 'chevron-left',
  onBack,
  showNewChat = true,
  rightContent,
  transparent = false,
  helpButtonClassName,
  iconColor = colors.secondary[500],
  onNewChatPress,
  showBorder = false,
  hideBorder = false,
  absolute = false,
}: AppHeaderProps) {
  const insets = useSafeAreaInsets();
  const { openDrawer, openCrisisDrawer } = useDrawer();

  return (
    <View
      style={{ paddingTop: insets.top }}
      className={cn(
        'border-b border-secondary-500/20 bg-primary-900',
        transparent && 'border-b-0 bg-transparent',
        showBorder && 'border-b border-secondary-500/15',
        hideBorder && 'border-b-0',
        absolute && 'absolute left-0 right-0 top-0 z-10',
      )}
    >
      <View className="flex-row items-center justify-between px-2 py-2">
        {showBack ? (
          <Pressable
            onPress={onBack}
            className="p-2"
            accessibilityLabel={en.chat.goBackLabel}
            accessibilityRole="button"
            hitSlop={8}
          >
            <Feather name={backIcon} size={backIcon === 'x' ? 24 : 28} color={iconColor} />
          </Pressable>
        ) : (
          <Pressable
            onPress={openDrawer}
            className="p-2"
            accessibilityLabel={en.chat.openMenuLabel}
            accessibilityRole="button"
            hitSlop={8}
          >
            <Feather name="menu" size={24} color={iconColor} />
          </Pressable>
        )}

        {title && (
          <Text className="mx-2 flex-1 text-center font-sans-semibold text-[17px]">{title}</Text>
        )}

        {rightContent ?? (
          <View className="flex-row items-center gap-1">
            <Pressable
              onPress={openCrisisDrawer}
              className={cn(
                'flex-row items-center justify-center gap-1 rounded-full bg-primary-500 px-3 py-2 active:opacity-80',
                helpButtonClassName,
              )}
              accessibilityLabel={en.chat.getHelpNowLabel}
              accessibilityRole="button"
            >
              <Feather name="phone" size={14} color={colors.secondary[500]} />
              <Text className="font-sans-semibold text-xs">{en.chat.getHelpNow}</Text>
            </Pressable>

            {showNewChat && (
              <Pressable
                onPress={onNewChatPress}
                className="items-center justify-center p-2"
                accessibilityLabel={en.chat.newConversationLabel}
                accessibilityRole="button"
                hitSlop={8}
              >
                <Feather name="edit" size={22} color={iconColor} />
              </Pressable>
            )}
          </View>
        )}
      </View>
    </View>
  );
}
