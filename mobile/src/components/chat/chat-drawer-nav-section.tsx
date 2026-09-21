// ABOUTME: The three top-level nav links inside ChatDrawer — Home, Library, Get Help Now.

import { View } from 'react-native';
import { Feather, type FeatherIconName } from '@react-native-vector-icons/feather';
import { colors } from '@/lib/tokens';
import en from '@/dictionaries/en.json';
import { Text } from '@/components/shared';
import { DrawerActionRow } from './drawer-action-row';

export interface ChatDrawerNavSectionProps {
  onNavigateHome: () => void;
  onNavigateLibrary: () => void;
  onUrgentHelp: () => void;
}

interface NavItem {
  label: string;
  icon: FeatherIconName;
  onPress: () => void;
}

export function ChatDrawerNavSection({ onNavigateHome, onNavigateLibrary, onUrgentHelp }: ChatDrawerNavSectionProps) {
  const navItems: NavItem[] = [
    { label: en.chat.navHome, icon: 'home', onPress: onNavigateHome },
    { label: en.chat.navLibrary, icon: 'book-open', onPress: onNavigateLibrary },
    { label: en.chat.navGetHelpNow, icon: 'phone', onPress: onUrgentHelp },
  ];

  return (
    <View className="px-4">
      {navItems.map((item) => (
        <DrawerActionRow
          key={item.label}
          onPress={item.onPress}
          accessibilityLabel={item.label}
          className="mb-1 px-4"
        >
          <Feather name={item.icon} size={20} color={colors.secondary[500]} style={{ marginRight: 12 }} />
          <Text className="font-sans-medium text-base">{item.label}</Text>
        </DrawerActionRow>
      ))}
    </View>
  );
}
