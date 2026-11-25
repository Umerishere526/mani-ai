// ABOUTME: Row actions for a prompt in the Prompts list — edit, history, activate/deactivate.
// ABOUTME: Activation runs through the setPromptActive server action.

"use client";

import { useState, useTransition } from "react";
import { ActionLink } from "@/components/shared";
import { setPromptActive } from "@/lib/actions/prompts";
import type { Prompt } from "@/types";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.prompts.actions;

interface PromptActionsProps {
  prompt: Prompt;
}

export function PromptActions({ prompt }: PromptActionsProps) {
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const handleToggleActive = () => {
    setError(null);
    startTransition(async () => {
      const result = await setPromptActive(prompt.id, !prompt.isActive);
      setError(result.error);
    });
  };

  return (
    <div className="flex items-center justify-end gap-3">
      {error && <span className="mr-2 text-sm text-mani-error">{error}</span>}
      <ActionLink href={`/admin/prompts/${prompt.id}`}>{STRINGS.edit}</ActionLink>
      <ActionLink variant="muted" href={`/admin/prompts/${prompt.id}/versions`}>
        {STRINGS.history}
      </ActionLink>
      <ActionLink variant="muted" onClick={handleToggleActive} disabled={isPending}>
        {prompt.isActive ? STRINGS.deactivate : STRINGS.activate}
      </ActionLink>
    </div>
  );
}
