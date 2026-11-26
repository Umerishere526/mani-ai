// ABOUTME: Create an account with email and password. When the project requires email
// ABOUTME: confirmation, it says so and points back to sign-in instead of signing in.

import { useState } from "react";
import { AuthScreenShell, AuthSwitchLink, CredentialsForm } from "@/components/auth";
import { Text } from "@/components/shared";
import en from "@/dictionaries/en.json";
import { useAsyncAction } from "@/hooks/useAsyncAction";
import { sessionManager } from "@/lib/api";
import { errorMessage } from "@/lib/utils";

const MIN_PASSWORD_LENGTH = 8;

export default function SignUpScreen() {
  const [confirmationSentTo, setConfirmationSentTo] = useState<string | null>(null);
  const signUp = useAsyncAction(async (email: string, password: string) => {
    const result = await sessionManager.signUp(email, password);
    if (result === "confirmEmail") setConfirmationSentTo(email);
  });

  if (confirmationSentTo) {
    return (
      <AuthScreenShell title={en.auth.confirmEmailTitle}>
        <Text className="mb-2 text-base leading-6 text-secondary-500/80">{en.auth.confirmEmailIntro}</Text>
        <Text className="mb-6 font-sans-semibold text-base leading-6">{confirmationSentTo}</Text>
        <AuthSwitchLink href="/sign-in" label={en.auth.toSignIn} />
      </AuthScreenShell>
    );
  }

  return (
    <AuthScreenShell title={en.auth.signUpTitle}>
      <Text className="mb-8 text-base leading-6 text-secondary-500/80">{en.auth.signUpIntro}</Text>
      <CredentialsForm
        submitLabel={en.auth.signUp}
        busyLabel={en.auth.signingUp}
        isBusy={signUp.isRunning}
        errorMessage={signUp.error ? errorMessage(signUp.error) : null}
        minPasswordLength={MIN_PASSWORD_LENGTH}
        isNewPassword
        passwordHint={en.auth.passwordHintSignUp}
        onSubmit={signUp.run}
      />
      <AuthSwitchLink href="/sign-in" label={en.auth.toSignIn} />
    </AuthScreenShell>
  );
}
