// ABOUTME: Root layout for the admin dashboard — sidebar nav plus a padded content area.
// ABOUTME: Ported from mani-app's app/admin/layout.tsx; no auth gate exists yet (see permissions.ts).

import type { Metadata } from "next";
import { AdminNav } from "@/components/admin";

export const metadata: Metadata = {
  title: "Mani Admin",
  description: "Mani Admin Dashboard",
};

const PLACEHOLDER_ADMIN_USER = { email: "admin@example.com" };

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen bg-mani-bg">
      <AdminNav user={PLACEHOLDER_ADMIN_USER} editingEnabled />
      <main className="flex-1 animate-fade-in p-8">{children}</main>
    </div>
  );
}
