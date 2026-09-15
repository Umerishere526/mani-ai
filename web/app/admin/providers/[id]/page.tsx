// ABOUTME: Admin page for editing an existing provider.
// ABOUTME: Ported from mani-app's app/admin/providers/[id]/page.tsx.

import { notFound } from "next/navigation";
import { BackLink } from "@/components/shared";
import { ProviderForm } from "@/components/admin";
import { getProviderById } from "@/lib/placeholder-providers";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.providers;
const COMMON = dictionary.admin.pages;

interface EditProviderPageProps {
  params: Promise<{ id: string }>;
}

export default async function EditProviderPage({ params }: EditProviderPageProps) {
  const { id } = await params;
  const provider = getProviderById(id);

  if (!provider) {
    notFound();
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <BackLink href="/admin/providers">{STRINGS.backToProviders}</BackLink>
      </div>

      <div className="rounded-mani-lg bg-mani-bg-card p-8 shadow-mani-card">
        <div className="mb-8 flex items-start justify-between">
          <div>
            <h1 className="text-[1.75rem] font-semibold tracking-tight text-mani-text">
              {provider.displayName}
            </h1>
            <p className="mt-1 text-sm text-mani-text-muted">
              {STRINGS.editSubtitle
                .replace("{name}", provider.name)
                .replace(
                  "{date}",
                  provider.updatedAt ? new Date(provider.updatedAt).toLocaleString() : COMMON.unknown,
                )}
            </p>
          </div>
        </div>
        <ProviderForm provider={provider} mode="edit" />
      </div>
    </div>
  );
}
