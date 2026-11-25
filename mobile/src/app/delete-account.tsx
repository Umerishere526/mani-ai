// ABOUTME: Deletes the account in two deliberate steps: what deletion removes, then a final
// ABOUTME: confirmation. On success the session ends and the route guard returns to sign-in.

import { useState } from "react";
import { router } from "expo-router";
import { AuthScreenShell, FormError } from "@/components/auth";
import { PrimaryButton, SecondaryButton, Text } from "@/components/shared";
import en from "@/dictionaries/en.json";
import { useAsyncAction } from "@/hooks/useAsyncAction";
import { sessionManager } from "@/lib/api";
import { deleteAccount } from "@/lib/api/account";
import { errorMessage } from "@/lib/utils";

export default function DeleteAccountScreen() {
  const [isConfirming, setIsConfirming] = useState(false);
  const remove = useAsyncAction(async () => {
    await deleteAccount();
    await sessionManager.signOut();
  });

  return (
    <AuthScreenShell title={en.deleteAccount.title} onBack={() => router.back()} backAccessibilityLabel={en.chat.goBackLabel}>
      {isConfirming ? (
        <>
          <Text className="mb-8 font-sans-semibold text-base leading-6">{en.deleteAccount.confirmWarning}</Text>
          <FormError message={remove.error ? errorMessage(remove.error) : null} />
          <PrimaryButton
            label={remove.isRunning ? en.deleteAccount.deleting : en.deleteAccount.confirm}
            onPress={() => remove.run()}
            disabled={remove.isRunning}
            accessibilityHint={en.deleteAccount.confirmHint}
            className="mb-4 self-stretch bg-red-700"
          />
          <SecondaryButton label={en.deleteAccount.cancel} onPress={() => router.back()} className="self-stretch" />
        </>
      ) : (
        <>
          <Text className="mb-8 text-base leading-6 text-secondary-500/80">{en.deleteAccount.explanation}</Text>
          <PrimaryButton
            label={en.deleteAccount.continue}
            onPress={() => setIsConfirming(true)}
            className="mb-4 self-stretch"
          />
          <SecondaryButton label={en.deleteAccount.cancel} onPress={() => router.back()} className="self-stretch" />
        </>
      )}
    </AuthScreenShell>
  );
}
