// ABOUTME: The "enter a new email address" phase of ChangeEmailScreen.

import { View } from "react-native";
import { PrimaryButton, Text, TextInput } from "@/components/shared";
import en from "@/dictionaries/en.json";

export interface ChangeEmailFormProps {
  currentEmail: string;
  newEmail: string;
  onNewEmailChange: (value: string) => void;
  onSubmit: () => void;
  isSending: boolean;
  isValid: boolean;
}

export function ChangeEmailForm({ currentEmail, newEmail, onNewEmailChange, onSubmit, isSending, isValid }: ChangeEmailFormProps) {
  return (
    <>
      <Text className="mb-8 text-base leading-6 text-secondary-500/80">{en.changeEmail.intro}</Text>

      <View className="mb-6">
        <Text className="mb-2 font-sans-medium text-sm text-secondary-500/90">{en.changeEmail.currentEmailLabel}</Text>
        <View className="rounded-xl border border-secondary-500/10 bg-secondary-500/5 px-4 py-4">
          <Text className="text-base text-secondary-500/60">{currentEmail}</Text>
        </View>
      </View>

      <View className="mb-6">
        <Text className="mb-2 font-sans-medium text-sm text-secondary-500/90">{en.changeEmail.newEmailLabel}</Text>
        <View className="rounded-xl border border-secondary-500/15 bg-secondary-500/8">
          <TextInput
            className="px-4 py-4 text-base"
            value={newEmail}
            onChangeText={onNewEmailChange}
            placeholder={en.changeEmail.newEmailPlaceholder}
            placeholderTextColor="rgba(255, 244, 225, 0.4)"
            keyboardType="email-address"
            autoCapitalize="none"
            autoCorrect={false}
            autoComplete="email"
            returnKeyType="done"
            onSubmitEditing={onSubmit}
            accessibilityLabel={en.changeEmail.newEmailAccessibilityLabel}
            accessibilityHint={en.changeEmail.newEmailHint}
          />
        </View>
      </View>

      <PrimaryButton
        label={isSending ? en.changeEmail.sending : en.changeEmail.sendCode}
        onPress={onSubmit}
        disabled={!isValid || isSending}
        className="mt-2 self-stretch"
      />
    </>
  );
}
