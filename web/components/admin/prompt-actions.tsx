// ABOUTME: Row actions for a prompt in the Prompts list — edit, history, activate/deactivate, delete.
// ABOUTME: Ported from mani-app's app/admin/prompts/PromptActions.tsx, restyled to Tailwind.

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ActionLink } from "@/components/shared";
import type { Prompt } from "@/types";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.prompts.actions;

interface PromptActionsProps {
  prompt: Prompt;
  canEdit: boolean;
  canAdmin: boolean;
}

export function PromptActions({ prompt, canEdit, canAdmin }: PromptActionsProps) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleToggleActive = async () => {
    if (!canAdmin) return;
    setLoading(true);
    setError(null);
    try {
      // No backend yet — placeholder data doesn't persist this toggle.
      console.log("toggle prompt active", prompt.id, !prompt.isActive);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : STRINGS.toggleError);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!canAdmin) return;
    if (!window.confirm(STRINGS.deleteConfirm.replace("{name}", prompt.name))) return;

    setLoading(true);
    setError(null);
    try {
      // No backend yet — placeholder data doesn't persist this delete.
      console.log("delete prompt", prompt.id);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : STRINGS.deleteError);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-end gap-3">
      {error && <span className="mr-2 text-sm text-mani-error">{error}</span>}
      {canEdit && <ActionLink href={`/admin/prompts/${prompt.id}`}>{STRINGS.edit}</ActionLink>}
      <ActionLink variant="muted" href={`/admin/prompts/${prompt.id}/versions`}>
        {STRINGS.history}
      </ActionLink>
      {canAdmin && (
        <>
          <ActionLink variant="muted" onClick={handleToggleActive} disabled={loading}>
            {prompt.isActive ? STRINGS.deactivate : STRINGS.activate}
          </ActionLink>
          <ActionLink variant="danger" onClick={handleDelete} disabled={loading}>
            {STRINGS.delete}
          </ActionLink>
        </>
      )}
    </div>
  );
}
