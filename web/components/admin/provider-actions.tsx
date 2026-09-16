// ABOUTME: Row actions for a provider in the Providers list — test connection, edit, delete.
// ABOUTME: Ported from mani-app's app/admin/providers/ProviderActions.tsx, restyled to Tailwind.

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import type { ProviderListItem } from "@/types";
import { MODELS_BY_PROVIDER } from "@/lib/placeholder-providers";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.providers.actions;

interface ProviderActionsProps {
  provider: ProviderListItem;
  canEdit: boolean;
  canAdmin: boolean;
}

export function ProviderActions({ provider, canEdit, canAdmin }: ProviderActionsProps) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  const handleDelete = async () => {
    if (!window.confirm(STRINGS.deleteConfirm.replace("{name}", provider.displayName))) return;

    setLoading(true);
    try {
      // No backend yet — placeholder data doesn't persist this delete.
      console.log("delete provider", provider.id);
      router.refresh();
    } catch (error) {
      window.alert(error instanceof Error ? error.message : STRINGS.deleteError);
    } finally {
      setLoading(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const modelCount = MODELS_BY_PROVIDER[provider.name]?.length ?? 0;
      const success = provider.hasApiKey || provider.baseUrl !== null;
      setTestResult({
        success,
        message: success
          ? STRINGS.testSuccess.replace("{count}", String(modelCount))
          : STRINGS.testFailure,
      });
    } catch (error) {
      setTestResult({
        success: false,
        message: error instanceof Error ? error.message : STRINGS.testError,
      });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="flex items-center justify-end gap-2">
      {testResult && (
        <span className={`text-xs ${testResult.success ? "text-mani-success" : "text-mani-error"}`}>
          {testResult.message}
        </span>
      )}
      <button
        type="button"
        onClick={handleTest}
        disabled={testing}
        title="Test connection"
        className="rounded-mani-md border border-mani-border px-3 py-1.5 text-sm font-medium text-mani-text transition-colors duration-200 hover:border-mani-text-light hover:bg-mani-bg disabled:cursor-not-allowed disabled:opacity-50"
      >
        {testing ? STRINGS.testing : STRINGS.test}
      </button>
      {canEdit && (
        <Link
          href={`/admin/providers/${provider.id}`}
          className="rounded-mani-md border border-mani-border px-3 py-1.5 text-sm font-medium text-mani-text transition-colors duration-200 hover:border-mani-text-light hover:bg-mani-bg"
        >
          {STRINGS.edit}
        </Link>
      )}
      {canAdmin && (
        <button
          type="button"
          onClick={handleDelete}
          disabled={loading}
          className="rounded-mani-md border border-mani-border px-3 py-1.5 text-sm font-medium text-mani-error transition-colors duration-200 hover:border-mani-text-light hover:bg-mani-bg disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? STRINGS.deleting : STRINGS.delete}
        </button>
      )}
    </div>
  );
}
