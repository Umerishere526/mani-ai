// ABOUTME: Admin Providers list.
// ABOUTME: Ported from mani-app's app/admin/providers/page.tsx.

import Link from "next/link";
import { EmptyState } from "@/components/shared";
import { ProviderActions } from "@/components/admin/provider-actions";
import { PROVIDERS } from "@/lib/placeholder-providers";
import { ADMIN_PERMISSIONS } from "../lib/permissions";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.providers;
const COMMON = dictionary.admin.pages;

export default function ProvidersPage() {
  const { canEditPromptsAndProviders } = ADMIN_PERMISSIONS;

  return (
    <div>
      <div className="mb-8 flex items-center justify-between">
        <h1 className="text-[1.75rem] font-semibold tracking-tight text-mani-text">{STRINGS.title}</h1>
        {canEditPromptsAndProviders && (
          <Link
            href="/admin/providers/new"
            className="inline-flex items-center justify-center gap-2 rounded-mani-md bg-mani-accent px-5 py-2.5 text-[0.9375rem] font-medium text-white shadow-mani-sm transition-colors duration-200 hover:bg-mani-accent-hover"
          >
            {STRINGS.newButton}
          </Link>
        )}
      </div>

      {PROVIDERS.length === 0 ? (
        <EmptyState
          message={STRINGS.empty}
          action={
            canEditPromptsAndProviders
              ? { label: STRINGS.emptyAction, href: "/admin/providers/new" }
              : undefined
          }
        />
      ) : (
        <div className="overflow-hidden rounded-mani-lg bg-mani-bg-card shadow-mani-card">
          <table className="w-full border-collapse">
            <thead className="bg-mani-bg">
              <tr>
                <th className="border-b border-mani-border px-6 py-3.5 text-left text-[0.6875rem] font-semibold uppercase tracking-wide text-mani-text-muted">
                  {STRINGS.colName}
                </th>
                <th className="border-b border-mani-border px-6 py-3.5 text-left text-[0.6875rem] font-semibold uppercase tracking-wide text-mani-text-muted">
                  {STRINGS.colDisplayName}
                </th>
                <th className="border-b border-mani-border px-6 py-3.5 text-left text-[0.6875rem] font-semibold uppercase tracking-wide text-mani-text-muted">
                  {STRINGS.colBaseUrl}
                </th>
                <th className="border-b border-mani-border px-6 py-3.5 text-left text-[0.6875rem] font-semibold uppercase tracking-wide text-mani-text-muted">
                  {STRINGS.colUpdated}
                </th>
                <th className="border-b border-mani-border px-6 py-3.5 text-right text-[0.6875rem] font-semibold uppercase tracking-wide text-mani-text-muted">
                  {STRINGS.colActions}
                </th>
              </tr>
            </thead>
            <tbody>
              {PROVIDERS.map((provider) => (
                <tr key={provider.id} className="transition-colors duration-150 hover:bg-mani-bg">
                  <td className="border-b border-mani-border px-6 py-4 last:border-b-0">
                    <Link href={`/admin/providers/${provider.id}`} className="font-medium">
                      {provider.name}
                    </Link>
                  </td>
                  <td className="border-b border-mani-border px-6 py-4 text-sm text-mani-text last:border-b-0">
                    {provider.displayName}
                  </td>
                  <td className="border-b border-mani-border px-6 py-4 font-mono text-sm text-mani-text-muted last:border-b-0">
                    {provider.baseUrl ?? STRINGS.defaultBaseUrl}
                  </td>
                  <td className="border-b border-mani-border px-6 py-4 text-sm text-mani-text-muted last:border-b-0">
                    {provider.updatedAt ? new Date(provider.updatedAt).toLocaleDateString() : COMMON.unknown}
                  </td>
                  <td className="border-b border-mani-border px-6 py-4 text-right last:border-b-0">
                    <ProviderActions
                      provider={provider}
                      canEdit={canEditPromptsAndProviders}
                      canAdmin={canEditPromptsAndProviders}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
