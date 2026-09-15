// ABOUTME: Admin page for creating a new provider.
// ABOUTME: Ported from mani-app's app/admin/providers/new/page.tsx.

import { BackLink } from "@/components/shared";
import { ProviderForm } from "@/components/admin";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.providers;

export default function NewProviderPage() {
  return (
    <div>
      <BackLink href="/admin/providers">{STRINGS.backToProviders}</BackLink>

      <div className="rounded-mani-lg bg-mani-bg-card p-8 shadow-mani-card">
        <h1 className="mb-8 text-[1.75rem] font-semibold tracking-tight text-mani-text">
          {STRINGS.createNewTitle}
        </h1>
        <ProviderForm mode="create" />
      </div>
    </div>
  );
}
