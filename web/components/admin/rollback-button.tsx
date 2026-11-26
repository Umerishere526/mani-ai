// ABOUTME: Button that rolls back a prompt to a prior version, with a confirm dialog.
// ABOUTME: The rollbackPrompt server action publishes that version's content as the next version.

"use client";

import { useState, useTransition } from "react";
import { rollbackPrompt } from "@/lib/actions/prompts";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.prompts.versions;

interface RollbackButtonProps {
  promptId: string;
  version: number;
  currentVersion: number;
}

export function RollbackButton({ promptId, version, currentVersion }: RollbackButtonProps) {
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const handleRollback = () => {
    const confirmMsg = STRINGS.rollbackConfirm
      .replaceAll("{version}", String(version))
      .replace("{nextVersion}", String(currentVersion + 1));
    if (!window.confirm(confirmMsg)) return;

    setError(null);
    startTransition(async () => {
      const result = await rollbackPrompt(promptId, version);
      setError(result.error);
    });
  };

  return (
    <div className="flex items-center gap-2">
      {error && <span className="text-sm text-mani-error">{error}</span>}
      <button
        type="button"
        onClick={handleRollback}
        disabled={isPending}
        className="rounded-mani-md border border-mani-border px-3 py-1.5 text-sm font-medium text-mani-text transition-colors duration-200 hover:border-mani-text-light hover:bg-mani-bg disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isPending ? STRINGS.rollingBack : STRINGS.rollbackButton}
      </button>
    </div>
  );
}
