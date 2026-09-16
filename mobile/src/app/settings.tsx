import { useState } from "react";
import { router } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { ScrollView, View } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { AppHeader, SecondaryButton, Text } from "@/components/shared";
import { SettingsRow, SettingsSection } from "@/components/settings";
import { colors } from "@/lib/tokens";
import { useNotificationPreference } from "@/hooks/useNotificationPreference";
import { useStatusBarStyle } from "@/hooks/useStatusBarStyle";
import en from "@/dictionaries/en.json";

export default function SettingsScreen() {
  const { isEnabled: notificationsEnabled, toggle: toggleNotifications } = useNotificationPreference();
  const [isSigningOut, setIsSigningOut] = useState(false);
  const isAnonymous = false;

  useStatusBarStyle("light");

  const handleSignOut = () => {
    setIsSigningOut(true);
    setTimeout(() => {
      setIsSigningOut(false);
      router.replace("/");
    }, 400);
  };

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
          </SettingsSection>
        )}

        <View className="min-h-8 flex-1" />

        <SecondaryButton
          label={isSigningOut ? en.settings.loggingOut : en.settings.logOut}
          onPress={handleSignOut}
          disabled={isSigningOut}
        />
      </ScrollView>

      <StatusBar style="light" />
    </View>
  );
}
