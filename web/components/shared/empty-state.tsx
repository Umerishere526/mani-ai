// ABOUTME: A placeholder shown in place of a list or section with no data yet.
// ABOUTME: Ported from mani-app's components/admin/EmptyState.tsx, restyled to Tailwind.

import Link from "next/link";

interface EmptyStateProps {
  message: string;
  action?: {
    label: string;
    href: string;
  };
  variant?: "default" | "inline";
}

export function EmptyState({ message, action, variant = "default" }: EmptyStateProps) {
  if (variant === "inline") {
    return (
      <div className="rounded-xl border border-dashed border-mani-border bg-mani-bg p-8 text-center text-mani-text-muted">
        {message}
      </div>
    );
  }

  return (
    <div className="rounded-mani-lg border border-dashed border-mani-border bg-mani-bg px-8 py-12 text-center text-mani-text-muted">
      <p className="mb-2 text-base">{message}</p>
      {action && <Link href={action.href}>{action.label}</Link>}
    </div>
  );
}
