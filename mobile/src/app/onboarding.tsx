// ABOUTME: First run after sign-up: saves an optional nickname and the default conversation
// ABOUTME: style to /v1/profile, then marks onboarding done so the guard opens the app.

import { useState } from "react";
import { AuthScreenShell } from "@/components/auth";
import { OnboardingForm } from "@/components/onboarding";
import en from "@/dictionaries/en.json";
import { useAsyncAction } from "@/hooks/useAsyncAction";
import { updateProfile } from "@/lib/api/profile";
import { errorMessage } from "@/lib/utils";
import { useOnboarding } from "@/providers";
import type { ConversationStyle } from "@/types/chat";

export default function OnboardingScreen() {
  const { complete } = useOnboarding();
  const [nickname, setNickname] = useState("");
  const save = useAsyncAction(async (style: ConversationStyle) => {
    const trimmed = nickname.trim();
    const saved = await updateProfile(trimmed === "" ? { support_style: style } : { nickname: trimmed, support_style: style });
    complete(saved?.nickname ?? null);
  });

  return (
    <AuthScreenShell title={en.onboarding.title}>
      <OnboardingForm
        nickname={nickname}
        onNicknameChange={setNickname}
        onStyleSelect={save.run}
        isSaving={save.isRunning}
        errorMessage={save.error ? errorMessage(save.error) : null}
      />
    </AuthScreenShell>
  );
}
