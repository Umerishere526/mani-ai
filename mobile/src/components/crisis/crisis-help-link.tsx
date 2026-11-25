// ABOUTME: One tappable way to reach help (call 988, text 988, call 911, the helpline directory), opening the
// ABOUTME: phone, messages or browser with a tel:, sms: or https: link.

import { Linking, Pressable } from 'react-native';
import en from '@/dictionaries/en.json';
import { cn } from '@/lib/utils';
import { Text } from '@/components/shared';

export interface CrisisHelpLinkProps {
  label: string;
  url: string;
  prominent?: boolean;
}

export function CrisisHelpLink({ label, url, prominent = false }: CrisisHelpLinkProps) {
  // A device that cannot call or text (a tablet, a simulator) rejects the link; the number stays on screen to dial.
  const open = () => Linking.openURL(url).catch(() => undefined);

  return (
    <Pressable
      onPress={open}
      className={cn(
        'min-h-11 flex-1 items-center justify-center rounded-full px-4 py-3 active:opacity-80',
        prominent ? 'bg-secondary-500' : 'border border-secondary-500/60',
      )}
      accessibilityRole="link"
      accessibilityLabel={label}
      accessibilityHint={en.crisis.help.linkHint}
    >
      <Text className={cn('font-sans-semibold text-base', prominent ? 'text-primary-700' : 'text-secondary-500')}>{label}</Text>
    </Pressable>
  );
}
