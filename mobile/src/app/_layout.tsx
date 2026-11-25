// ABOUTME: Root layout: holds the splash screen until the session is known, then renders the
// ABOUTME: guarded route stack inside the app-wide providers and the global drawer.

import * as SplashScreen from "expo-splash-screen";
import { ChatSafetyProvider, DrawerProvider, OnboardingProvider } from "@/providers";
import { GlobalDrawer } from "@/components/global-drawer";
import { RootStack } from "@/components/navigation";
import "../global.css";

SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
  return (
    <OnboardingProvider>
      <DrawerProvider>
        <ChatSafetyProvider>
          <RootStack />
          <GlobalDrawer />
        </ChatSafetyProvider>
      </DrawerProvider>
    </OnboardingProvider>
  );
}
