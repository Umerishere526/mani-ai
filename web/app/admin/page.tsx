// ABOUTME: Redirects bare /admin to the Prompts section, the default admin view.
// ABOUTME: Ported from mani-app's app/admin/page.tsx.

import { redirect } from "next/navigation";

export default function AdminPage() {
  redirect("/admin/prompts");
}
