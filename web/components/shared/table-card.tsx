// ABOUTME: A card holding an admin data table: rounded, shadowed, and a full-width table inside.
// ABOUTME: Callers pass the <thead> and <tbody> as children.

import type { ReactNode } from "react";

interface TableCardProps {
  children: ReactNode;
}

export function TableCard({ children }: TableCardProps) {
  return (
    <div className="overflow-hidden rounded-mani-lg bg-mani-bg-card shadow-mani-card">
      <table className="w-full border-collapse">{children}</table>
    </div>
  );
}
