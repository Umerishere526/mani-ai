// ABOUTME: A column heading in an admin data table — small, uppercase, muted.
// ABOUTME: Left-aligned by default; the actions column aligns right.

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface TableHeadCellProps {
  align?: "left" | "right";
  children: ReactNode;
}

export function TableHeadCell({ align = "left", children }: TableHeadCellProps) {
  return (
    <th
      className={cn(
        "border-b border-mani-border bg-mani-bg px-6 py-3.5 text-[0.6875rem] font-semibold uppercase tracking-wide text-mani-text-muted",
        align === "right" ? "text-right" : "text-left",
      )}
    >
      {children}
    </th>
  );
}
