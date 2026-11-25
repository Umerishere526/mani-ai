// ABOUTME: Root layout for the admin dashboard — sidebar nav plus a padded content area.
// ABOUTME: Requires a signed-in admin; every backend read checks the session again through the same call.

import type { Metadata } from "next";
import { AdminNav } from "@/components/admin";
import { requireAdmin } from "@/lib/auth/require-admin";
import dictionary from "@/dictionaries/en.json";

export const metadata: Metadata = {
  title: dictionary.admin.meta.title,
  description: dictionary.admin.meta.description,
};

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const { email } = await requireAdmin();

  return (
    <div className="flex min-h-screen bg-mani-bg">
      <AdminNav email={email} />
      <main className="flex-1 animate-fade-in p-8">{children}</main>
    </div>
  );
}
