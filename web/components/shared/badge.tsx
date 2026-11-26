// ABOUTME: A small pill-shaped status label with success/neutral/danger color variants.
// ABOUTME: Ported from mani-app's components/admin/Badge.tsx, restyled to Tailwind.

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface BadgeProps {
  variant?: "success" | "neutral" | "danger";
  children: ReactNode;
}

const variantClasses = {
  success: "bg-mani-success-light text-mani-success",
  neutral: "bg-mani-bg text-mani-text-muted border border-mani-border",
  danger: "bg-mani-error-light text-mani-error-dark",
} as const;

export function Badge({ variant = "neutral", children }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium",
        variantClasses[variant],
      )}
    >
      {children}
    </span>
  );
}
