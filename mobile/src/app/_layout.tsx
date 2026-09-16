import { Stack } from "expo-router";
import { DrawerProvider } from "@/providers";
import { GlobalDrawer } from "@/components/global-drawer";
import "../global.css";

export default function RootLayout() {
  return (
    <DrawerProvider>
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="index" />
        <Stack.Screen name="chat" />
        <Stack.Screen name="settings" />
        <Stack.Screen name="exercises" />
        <Stack.Screen name="change-password" options={{ presentation: "modal" }} />
        <Stack.Screen name="change-email" options={{ presentation: "modal" }} />
      </Stack>
      <GlobalDrawer />
    </DrawerProvider>
  );
}
