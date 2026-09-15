// ABOUTME: Button that rolls back a prompt to a prior version, with a confirm dialog.
// ABOUTME: Ported from mani-app's prompts/[id]/versions/RollbackButton.tsx, restyled to Tailwind.

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.prompts.versions;

interface RollbackButtonProps {
  promptId: string;
  version: number;
  currentVersion: number;
}

export function RollbackButton({ promptId, version, currentVersion }: RollbackButtonProps) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRollback = async () => {
    const confirmMsg = STRINGS.rollbackConfirm
      .replaceAll("{version}", String(version))
      .replace("{nextVersion}", String(currentVersion + 1));
    if (!window.confirm(confirmMsg)) return;

    setLoading(true);
    setError(null);
    try {
      // No backend yet — placeholder data doesn't persist this rollback.
      console.log("rollback prompt", promptId, "to version", version);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : STRINGS.rollbackError);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center gap-2">
      {error && <span className="text-sm text-mani-error">{error}</span>}
      <button
        type="button"
        onClick={handleRollback}
        disabled={loading}
        className="rounded-mani-md border border-mani-border px-3 py-1.5 text-sm font-medium text-mani-text transition-colors duration-200 hover:border-mani-text-light hover:bg-mani-bg disabled:cursor-not-allowed disabled:opacity-50"
      >
        {loading ? STRINGS.rollingBack : STRINGS.rollbackButton}
      </button>
    </div>
  );
}
