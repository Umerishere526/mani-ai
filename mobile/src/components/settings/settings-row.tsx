// ABOUTME: A single settings list row — icon, label, and either a chevron (navigates)
// ABOUTME: or a toggle switch (in-place preference). One row is one setting.

import { Pressable, Switch, View } from 'react-native';
import { Feather, type FeatherIconName } from '@react-native-vector-icons/feather/static';
import { colors } from '@/lib/tokens';
import { cn } from '@/lib/utils';
import { Text } from '@/components/shared';

export interface SettingsRowProps {
  icon: FeatherIconName;
  label: string;
  onPress?: () => void;
  accessory?: 'chevron' | 'toggle';
  toggleValue?: boolean;
  onToggleChange?: (value: boolean) => void;
  className?: string;
}

export function SettingsRow({
  icon,
  label,
  onPress,
  accessory = 'chevron',
  toggleValue = false,
  onToggleChange,
  className,
}: SettingsRowProps) {
  const handlePress = () => {
    if (accessory === 'toggle' && onToggleChange) {
      onToggleChange(!toggleValue);
    } else {
      onPress?.();
    }
  };

  return (
    <Pressable
      onPress={handlePress}
      accessibilityLabel={label}
      accessibilityRole={accessory === 'toggle' ? 'switch' : 'button'}
      accessibilityState={accessory === 'toggle' ? { checked: toggleValue } : undefined}
      className={cn('flex-row items-center justify-between rounded-xl px-4 py-4 active:bg-secondary-500/10', className)}
    >
      <View className="flex-1 flex-row items-center">
        <Feather name={icon} size={20} color={colors.secondary[500]} />
        <Text className="ml-3 font-sans-medium text-base">{label}</Text>
      </View>
      {accessory === 'chevron' && <Feather name="chevron-right" size={20} color={colors.secondary[400]} />}
      {accessory === 'toggle' && (
        <Switch
          value={toggleValue}
          onValueChange={onToggleChange}
          trackColor={{ false: 'rgba(255, 244, 225, 0.2)', true: colors.primary[400] }}
          thumbColor={colors.secondary[500]}
          ios_backgroundColor="rgba(255, 244, 225, 0.2)"
        />
      )}
    </Pressable>
  );
}
