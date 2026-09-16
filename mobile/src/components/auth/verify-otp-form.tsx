// ABOUTME: The "verify the code we sent" phase of ChangeEmailScreen.

import { useRef } from "react";
import { Pressable, View, type TextInput as RNTextInput } from "react-native";
import { PrimaryButton, Text, TextInput } from "@/components/shared";
import en from "@/dictionaries/en.json";

export interface VerifyOtpFormProps {
  email: string;
  otpCode: string;
  onOtpChange: (value: string) => void;
  onSubmit: () => void;
  onResend: () => void;
  onWrongEmail: () => void;
  isVerifying: boolean;
  isValid: boolean;
}

export function VerifyOtpForm({
  email,
  otpCode,
  onOtpChange,
  onSubmit,
  onResend,
  onWrongEmail,
  isVerifying,
  isValid,
}: VerifyOtpFormProps) {
  const otpInputRef = useRef<RNTextInput>(null);

  return (
    <>
      <Text className="mb-6 text-base leading-6 text-secondary-500/80">{en.changeEmail.verifyIntro}</Text>
      <Text className="mb-6 font-sans-semibold text-base leading-6">{email}</Text>

      <View className="mt-4 items-center">
        <TextInput
          ref={otpInputRef}
          className="w-3/4 border-b border-white/30 py-3 text-center text-[28px] font-sans-semibold tracking-[10px]"
          value={otpCode}
          onChangeText={(text) => onOtpChange(text.replace(/[^0-9]/g, "").slice(0, 6))}
          placeholder={en.changeEmail.otpPlaceholder}
          placeholderTextColor="rgba(255, 255, 255, 0.3)"
          keyboardType="number-pad"
          maxLength={6}
          autoFocus
          returnKeyType="done"
          onSubmitEditing={onSubmit}
          accessibilityLabel={en.changeEmail.otpAccessibilityLabel}
          accessibilityHint={en.changeEmail.otpHint}
        />
      </View>

      <PrimaryButton
        label={isVerifying ? en.changeEmail.verifying : en.changeEmail.verify}
        onPress={onSubmit}
        disabled={!isValid || isVerifying}
        className="mt-6 self-stretch"
      />

      <View className="mt-6 flex-row justify-between">
        <Pressable onPress={onResend} accessibilityRole="button" accessibilityLabel={en.changeEmail.resendCodeLabel}>
          <Text className="font-sans-medium text-sm text-secondary-500/70">{en.changeEmail.resendCode}</Text>
        </Pressable>
        <Pressable onPress={onWrongEmail} accessibilityRole="button" accessibilityLabel={en.changeEmail.wrongEmailLabel}>
          <Text className="font-sans-medium text-sm text-secondary-500/70">{en.changeEmail.wrongEmail}</Text>
        </Pressable>
      </View>
    </>
  );
}
