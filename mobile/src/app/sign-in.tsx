// ABOUTME: Sign in with email and password; the route guard moves a signed-in person on to
// ABOUTME: onboarding or the app, so this screen never navigates itself.

import { AuthScreenShell, AuthSwitchLink, CredentialsForm } from "@/components/auth";
import { Text } from "@/components/shared";
import en from "@/dictionaries/en.json";
import { useAsyncAction } from "@/hooks/useAsyncAction";
import { sessionManager } from "@/lib/api";
import { errorMessage } from "@/lib/utils";

export default function SignInScreen() {
  const signIn = useAsyncAction((email: string, password: string) => sessionManager.signIn(email, password));

  return (
    <AuthScreenShell title={en.auth.signInTitle}>
      <Text className="mb-8 text-base leading-6 text-secondary-500/80">{en.auth.signInIntro}</Text>
      <CredentialsForm
        submitLabel={en.auth.signIn}
        busyLabel={en.auth.signingIn}
        isBusy={signIn.isRunning}
        errorMessage={signIn.error ? errorMessage(signIn.error) : null}
        minPasswordLength={1}
        isNewPassword={false}
        passwordHint={en.auth.passwordHintSignIn}
        onSubmit={signIn.run}
      />
      <AuthSwitchLink href="/sign-up" label={en.auth.toSignUp} />
    </AuthScreenShell>
  );
}
