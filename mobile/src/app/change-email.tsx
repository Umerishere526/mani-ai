import { useState } from "react";
import { router } from "expo-router";
import { Alert } from "react-native";
import { AuthScreenShell, ChangeEmailForm, VerifyOtpForm } from "@/components/auth";
import en from "@/dictionaries/en.json";

type Phase = "enter_email" | "verify_otp";
const CURRENT_EMAIL = "you@example.com";

function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

export default function ChangeEmailScreen() {
  const [phase, setPhase] = useState<Phase>("enter_email");
  const [newEmail, setNewEmail] = useState("");
  const [otpCode, setOtpCode] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);

  const isEmailValid = isValidEmail(newEmail) && newEmail !== CURRENT_EMAIL;
  const isOtpValid = otpCode.length === 6;

  const handleSendCode = () => {
    if (!isValidEmail(newEmail)) {
      Alert.alert(en.changeEmail.invalidEmailTitle, en.changeEmail.invalidEmailMessage);
      return;
    }
    if (newEmail.toLowerCase() === CURRENT_EMAIL.toLowerCase()) {
      Alert.alert(en.changeEmail.sameEmailTitle, en.changeEmail.sameEmailMessage);
      return;
    }

    setIsSending(true);
    setTimeout(() => {
      setIsSending(false);
      setPhase("verify_otp");
      setOtpCode("");
    }, 400);
  };

  const handleVerifyCode = () => {
    if (otpCode.length !== 6) {
      Alert.alert(en.changeEmail.invalidCodeTitle, en.changeEmail.invalidCodeMessage);
      return;
    }

    setIsVerifying(true);
    setTimeout(() => {
      setIsVerifying(false);
      Alert.alert(en.changeEmail.successTitle, en.changeEmail.successMessage, [
        { text: en.changeEmail.ok, onPress: () => router.back() },
      ]);
    }, 400);
  };

  const handleResendCode = () => {
    Alert.alert(en.changeEmail.codeSentTitle, en.changeEmail.codeSentMessage);
  };

  const handleWrongEmail = () => {
    setNewEmail("");
    setOtpCode("");
    setPhase("enter_email");
  };

  const title = phase === "enter_email" ? en.changeEmail.titleEnterEmail : en.changeEmail.titleVerify;

  return (
    <AuthScreenShell title={title} onBack={() => router.back()} backAccessibilityLabel={en.chat.goBackLabel}>
      {phase === "enter_email" ? (
        <ChangeEmailForm
          currentEmail={CURRENT_EMAIL}
          newEmail={newEmail}
          onNewEmailChange={setNewEmail}
          onSubmit={handleSendCode}
          isSending={isSending}
          isValid={isEmailValid}
        />
      ) : (
        <VerifyOtpForm
          email={newEmail}
          otpCode={otpCode}
          onOtpChange={setOtpCode}
          onSubmit={handleVerifyCode}
          onResend={handleResendCode}
          onWrongEmail={handleWrongEmail}
          isVerifying={isVerifying}
          isValid={isOtpValid}
        />
      )}
    </AuthScreenShell>
  );
}
