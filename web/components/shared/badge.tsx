// ABOUTME: A small pill-shaped status label with success/neutral/accent color variants.
// ABOUTME: Ported from mani-app's components/admin/Badge.tsx, restyled to Tailwind.

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface BadgeProps {
  variant?: "success" | "neutral" | "accent";
  children: ReactNode;
}

const variantClasses = {
  success: "bg-mani-success-light text-mani-success",
  neutral: "bg-mani-bg text-mani-text-muted border border-mani-border",
  accent: "bg-mani-accent-light text-mani-accent",
} as const;

export function Badge({ variant = "neutral", children }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium",
        variantClasses[variant],
      )}
    >
      {children}
    </span>
  );
}
