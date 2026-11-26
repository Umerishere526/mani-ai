// ABOUTME: The app's route guard: signed out reaches only sign-in and sign-up, signed in but
// ABOUTME: not onboarded reaches only onboarding, and everyone else reaches the app itself.

import { useEffect } from 'react';
import { ActivityIndicator, View } from 'react-native';
import { Stack } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { ProfileLoadError } from '@/components/onboarding';
import en from '@/dictionaries/en.json';
import { useSession } from '@/hooks/useSession';
import { sessionManager } from '@/lib/api';
import { colors } from '@/lib/tokens';
import { useOnboarding } from '@/providers';

export function RootStack() {
  const { status } = useSession();
  const onboarding = useOnboarding();
  const isSignedIn = status === 'signedIn';
  const isSettled = status !== 'loading' && onboarding.status !== 'checking';

  useEffect(() => {
    sessionManager.load();
  }, []);

  useEffect(() => {
    if (isSettled) SplashScreen.hide();
  }, [isSettled]);

  if (!isSettled) {
    return (
      <View className="flex-1 items-center justify-center bg-primary-900">
        <ActivityIndicator color={colors.secondary[500]} accessibilityLabel={en.common.loading} />
      </View>
    );
  }

  if (isSignedIn && onboarding.status === 'error') {
    return <ProfileLoadError onRetry={onboarding.retry} onSignOut={() => sessionManager.signOut()} />;
  }

  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Protected guard={!isSignedIn}>
        <Stack.Screen name="sign-in" />
        <Stack.Screen name="sign-up" />
      </Stack.Protected>
      <Stack.Protected guard={isSignedIn && onboarding.status === 'needed'}>
        <Stack.Screen name="onboarding" />
      </Stack.Protected>
      <Stack.Protected guard={isSignedIn && onboarding.status === 'done'}>
        <Stack.Screen name="index" />
        <Stack.Screen name="chat" />
        <Stack.Screen name="settings" />
        <Stack.Screen name="exercises" />
        <Stack.Screen name="change-password" options={{ presentation: 'modal' }} />
        <Stack.Screen name="change-email" options={{ presentation: 'modal' }} />
        <Stack.Screen name="delete-account" options={{ presentation: 'modal' }} />
      </Stack.Protected>
    </Stack>
  );
}
