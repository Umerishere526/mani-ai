import { useRef, useState } from "react";
import { router } from "expo-router";
import { Alert, Pressable, View, type TextInput as RNTextInput } from "react-native";
import { Ionicons } from "@react-native-vector-icons/ionicons/static";
import { AuthScreenShell } from "@/components/auth";
import { PrimaryButton, Text, TextInput } from "@/components/shared";
import en from "@/dictionaries/en.json";

function validatePassword(password: string): string | null {
  if (password.length < 8) return en.changePassword.invalidPasswordMessage;
  return null;
}

export default function ChangePasswordScreen() {
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
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

      <View className="mb-6">
        <Text className="mb-2 font-sans-medium text-sm text-secondary-500/90">{en.changePassword.newPasswordLabel}</Text>
        <View className="flex-row items-center rounded-xl border border-secondary-500/15 bg-secondary-500/8">
          <TextInput
            className="flex-1 px-4 py-4 text-base"
            value={newPassword}
            onChangeText={setNewPassword}
            placeholder={en.changePassword.newPasswordPlaceholder}
            placeholderTextColor="rgba(255, 244, 225, 0.4)"
            secureTextEntry={!showNewPassword}
            autoCapitalize="none"
            autoCorrect={false}
            returnKeyType="next"
            onSubmitEditing={() => confirmPasswordRef.current?.focus()}
            accessibilityLabel={en.changePassword.newPasswordAccessibilityLabel}
            accessibilityHint={en.changePassword.newPasswordHint}
          />
          <Pressable
            onPress={() => setShowNewPassword((prev) => !prev)}
            className="px-4 py-4"
            hitSlop={8}
            accessibilityLabel={showNewPassword ? en.changePassword.hidePassword : en.changePassword.showPassword}
            accessibilityRole="button"
          >
            <Ionicons name={showNewPassword ? "eye-off-outline" : "eye-outline"} size={22} color="rgba(255, 244, 225, 0.6)" />
          </Pressable>
        </View>
      </View>

      <View className="mb-6">
        <Text className="mb-2 font-sans-medium text-sm text-secondary-500/90">{en.changePassword.confirmPasswordLabel}</Text>
        <View className="flex-row items-center rounded-xl border border-secondary-500/15 bg-secondary-500/8">
          <TextInput
            ref={confirmPasswordRef}
            className="flex-1 px-4 py-4 text-base"
            value={confirmPassword}
            onChangeText={setConfirmPassword}
            placeholder={en.changePassword.confirmPasswordPlaceholder}
            placeholderTextColor="rgba(255, 244, 225, 0.4)"
            secureTextEntry={!showConfirmPassword}
            autoCapitalize="none"
            autoCorrect={false}
            returnKeyType="done"
            onSubmitEditing={handleUpdatePassword}
            accessibilityLabel={en.changePassword.confirmPasswordAccessibilityLabel}
            accessibilityHint={en.changePassword.confirmPasswordHint}
          />
          <Pressable
            onPress={() => setShowConfirmPassword((prev) => !prev)}
            className="px-4 py-4"
            hitSlop={8}
            accessibilityLabel={showConfirmPassword ? en.changePassword.hidePassword : en.changePassword.showPassword}
            accessibilityRole="button"
          >
            <Ionicons name={showConfirmPassword ? "eye-off-outline" : "eye-outline"} size={22} color="rgba(255, 244, 225, 0.6)" />
          </Pressable>
        </View>
      </View>

      <PrimaryButton
        label={isUpdating ? en.changePassword.updating : en.changePassword.update}
        onPress={handleUpdatePassword}
        disabled={!isFormValid || isUpdating}
        className="mt-2 self-stretch"
      />
    </AuthScreenShell>
  );
}
