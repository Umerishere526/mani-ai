// ABOUTME: A card holding an admin data table: rounded, shadowed, and a full-width table inside.
// ABOUTME: A table wider than the content area scrolls sideways inside the card instead of breaking the layout.

import type { ReactNode } from "react";

interface TableCardProps {
  children: ReactNode;
}

export function TableCard({ children }: TableCardProps) {
  return (
    <div className="overflow-x-auto rounded-mani-lg bg-mani-bg-card shadow-mani-card">
      <table className="w-full border-collapse">{children}</table>
    </div>
  );
}
