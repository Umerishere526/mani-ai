// ABOUTME: A link/button styled as inline text, used for row actions in admin tables.
// ABOUTME: Ported from mani-app's components/admin/ActionLink.tsx, restyled to Tailwind.

"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";

interface ActionLinkProps {
  href?: string;
  onClick?: () => void;
  variant?: "default" | "muted" | "danger";
  disabled?: boolean;
  children: ReactNode;
  className?: string;
}

const variantClasses = {
  default: "text-mani-accent hover:text-mani-accent-hover",
  muted: "text-mani-text-muted hover:text-mani-text",
  danger: "text-mani-error hover:text-mani-error-dark",
} as const;

export function ActionLink({
  href,
  onClick,
  variant = "default",
  disabled = false,
  children,
  className,
}: ActionLinkProps) {
  const combinedClassName = cn(
    "inline-flex items-center text-sm font-medium transition-colors duration-150",
    variantClasses[variant],
    disabled && "opacity-50 pointer-events-none",
    className,
  );

  if (href && !disabled) {
    return (
      <Link href={href} className={combinedClassName} onClick={onClick}>
        {children}
      </Link>
    );
  }

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(combinedClassName, "border-0 bg-transparent p-0 cursor-pointer disabled:cursor-not-allowed")}
    >
      {children}
    </button>
  );
}
