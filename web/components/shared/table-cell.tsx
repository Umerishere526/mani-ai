// ABOUTME: A body cell in an admin data table, with the row divider and padding every table shares.
// ABOUTME: Extra classes set the text style or alignment of one column.

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface TableCellProps {
  className?: string;
  children: ReactNode;
}

export function TableCell({ className, children }: TableCellProps) {
  return <td className={cn("border-b border-mani-border px-6 py-4 [tr:last-child_&]:border-b-0", className)}>{children}</td>;
}
