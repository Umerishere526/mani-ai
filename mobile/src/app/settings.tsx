// ABOUTME: Settings screen — notification preference, account rows (password, email)
// ABOUTME: and Log Out, which ends the session so the route guard returns to sign-in.

import { router } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { ScrollView, View } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { AiDisclosure, AppHeader, SecondaryButton, Text } from "@/components/shared";
import { SettingsRow, SettingsSection } from "@/components/settings";
import { colors } from "@/lib/tokens";
import { useNotificationPreference } from "@/hooks/useNotificationPreference";
import { useStatusBarStyle } from "@/hooks/useStatusBarStyle";
import { useAsyncAction } from "@/hooks/useAsyncAction";
import { sessionManager } from "@/lib/api";
import en from "@/dictionaries/en.json";

export default function SettingsScreen() {
  const { isEnabled: notificationsEnabled, toggle: toggleNotifications } = useNotificationPreference();
  const signOut = useAsyncAction(() => sessionManager.signOut());
  const isAnonymous = false;

  useStatusBarStyle("light");

  return (
    <View className="flex-1">
      <LinearGradient colors={[colors.primary[700], colors.primary[900]]} className="absolute inset-0" />

      <AppHeader showBack transparent absolute onBack={() => router.back()} />

      <ScrollView
        className="flex-1 px-4"
        contentContainerStyle={{ flexGrow: 1, paddingTop: 100, paddingBottom: 24 }}
        showsVerticalScrollIndicator={false}
      >
        <Text className="mb-6 font-sans-semibold text-[28px]">{en.settings.title}</Text>

        <SettingsSection title={en.settings.preferencesSection}>
          <SettingsRow
            icon="bell"
            label={en.settings.notifications}
            accessory="toggle"
            toggleValue={notificationsEnabled}
            onToggleChange={toggleNotifications}
          />
        </SettingsSection>

        {!isAnonymous && (
          <SettingsSection title={en.settings.accountSection}>
            <SettingsRow
              icon="key"
              label={en.settings.changePassword}
              accessory="chevron"
              onPress={() => router.push("/change-password")}
            />
            <SettingsRow
              icon="mail"
              label={en.settings.changeEmail}
              accessory="chevron"
              onPress={() => router.push("/change-email")}
            />
            <SettingsRow
              icon="trash-2"
              label={en.settings.deleteAccount}
              accessory="chevron"
              onPress={() => router.push("/delete-account")}
            />
          </SettingsSection>
        )}

        <View className="min-h-8 flex-1" />

        <AiDisclosure className="mb-6" />

        <SecondaryButton
          label={signOut.isRunning ? en.settings.loggingOut : en.settings.logOut}
          onPress={() => signOut.run()}
          disabled={signOut.isRunning}
        />
      </ScrollView>

      <StatusBar style="light" />
    </View>
  );
}
