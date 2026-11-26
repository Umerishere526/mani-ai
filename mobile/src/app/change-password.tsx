// ABOUTME: Change-password screen — new and confirm fields with show/hide toggles and
// ABOUTME: length/match checks; the update itself is simulated until the account API is wired up.

import { useRef, useState } from "react";
import { router } from "expo-router";
import { Alert, type TextInput as RNTextInput } from "react-native";
import { AuthScreenShell, PasswordField } from "@/components/auth";
import { PrimaryButton, Text } from "@/components/shared";
import en from "@/dictionaries/en.json";

function validatePassword(password: string): string | null {
  if (password.length < 8) return en.changePassword.invalidPasswordMessage;
  return null;
}

export default function ChangePasswordScreen() {
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isUpdating, setIsUpdating] = useState(false);
  const confirmPasswordRef = useRef<RNTextInput>(null);

  const isFormValid = newPassword.length >= 8 && confirmPassword.length >= 8;

  const handleUpdatePassword = () => {
    const passwordError = validatePassword(newPassword);
    if (passwordError) {
      Alert.alert(en.changePassword.invalidPasswordTitle, passwordError);
      return;
    }
    if (newPassword !== confirmPassword) {
      Alert.alert(en.changePassword.passwordsMismatchTitle, en.changePassword.passwordsMismatchMessage);
      return;
    }

    setIsUpdating(true);
    setTimeout(() => {
      setIsUpdating(false);
      Alert.alert(en.changePassword.successTitle, en.changePassword.successMessage, [
        { text: en.changePassword.ok, onPress: () => router.back() },
      ]);
    }, 400);
  };

  return (
    <AuthScreenShell title={en.changePassword.title} onBack={() => router.back()} backAccessibilityLabel={en.chat.goBackLabel}>
      <Text className="mb-8 text-base leading-6 text-secondary-500/80">{en.changePassword.intro}</Text>

      <PasswordField
        label={en.changePassword.newPasswordLabel}
        value={newPassword}
        onChangeText={setNewPassword}
        placeholder={en.changePassword.newPasswordPlaceholder}
        autoComplete="new-password"
        returnKeyType="next"
        onSubmitEditing={() => confirmPasswordRef.current?.focus()}
        accessibilityLabel={en.changePassword.newPasswordAccessibilityLabel}
        accessibilityHint={en.changePassword.newPasswordHint}
      />

      <PasswordField
        ref={confirmPasswordRef}
        label={en.changePassword.confirmPasswordLabel}
        value={confirmPassword}
        onChangeText={setConfirmPassword}
        placeholder={en.changePassword.confirmPasswordPlaceholder}
        autoComplete="new-password"
        returnKeyType="done"
        onSubmitEditing={handleUpdatePassword}
        accessibilityLabel={en.changePassword.confirmPasswordAccessibilityLabel}
        accessibilityHint={en.changePassword.confirmPasswordHint}
      />

      <PrimaryButton
        label={isUpdating ? en.changePassword.updating : en.changePassword.update}
        onPress={handleUpdatePassword}
        disabled={!isFormValid || isUpdating}
        className="mt-2 self-stretch"
      />
    </AuthScreenShell>
  );
}
