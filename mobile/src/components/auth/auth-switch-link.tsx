// ABOUTME: The line under an auth form that moves between sign-in and sign-up, replacing
// ABOUTME: the current screen so back never cycles between the two.

import { Link, type Href } from 'expo-router';
import { Pressable } from 'react-native';
import { Text } from '@/components/shared';

export interface AuthSwitchLinkProps {
  href: Href;
  label: string;
}

export function AuthSwitchLink({ href, label }: AuthSwitchLinkProps) {
  return (
    <Link href={href} replace asChild>
      <Pressable accessibilityRole="link" className="mt-6 min-h-11 items-center justify-center">
        <Text className="font-sans-medium text-sm text-secondary-500/80">{label}</Text>
      </Pressable>
    </Link>
  );
}
