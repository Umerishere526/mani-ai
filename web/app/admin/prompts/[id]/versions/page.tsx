// ABOUTME: Admin page showing a prompt's version history with rollback.
// ABOUTME: Ported from mani-app's app/admin/prompts/[id]/versions/page.tsx.

import { notFound } from "next/navigation";
import { BackLink } from "@/components/shared";
import { RollbackButton } from "@/components/admin/rollback-button";
import { getPromptById, getPromptVersions } from "@/lib/placeholder-prompts";
import { ADMIN_PERMISSIONS } from "../../../lib/permissions";
import dictionary from "@/dictionaries/en.json";

const PROMPTS_STRINGS = dictionary.admin.pages.prompts;
const STRINGS = PROMPTS_STRINGS.versions;

interface VersionsPageProps {
  params: Promise<{ id: string }>;
}

export default async function VersionsPage({ params }: VersionsPageProps) {
  const { id } = await params;
  const prompt = getPromptById(id);
  const versions = getPromptVersions(id);

  if (!prompt) {
    notFound();
  }

  const { canRollback } = ADMIN_PERMISSIONS;

  return (
    <div>
      <div className="mb-6">
        <BackLink href={`/admin/prompts/${id}`}>
          {PROMPTS_STRINGS.backToPromptPrefix}
          {prompt.name}
        </BackLink>
      </div>

      <div className="rounded-mani-lg bg-mani-bg-card shadow-mani-card">
        <div className="border-b border-mani-border p-6">
          <h1 className="text-[1.75rem] font-semibold tracking-tight text-mani-text">{STRINGS.title}</h1>
          <p className="mt-1 text-sm text-mani-text-muted">
            {STRINGS.subtitle.replace("{name}", prompt.name).replace("{version}", String(prompt.version))}
          </p>
        </div>

        {versions.length === 0 ? (
          <div className="p-12 text-center text-mani-text-muted">{STRINGS.empty}</div>
        ) : (
          <div>
            {versions.map((version, index) => (
              <div
                key={version.id}
                className={index < versions.length - 1 ? "border-b border-mani-border p-6" : "p-6"}
              >
                <div className="mb-4 flex items-start justify-between">
                  <div>
                    <span className="text-lg font-medium text-mani-text">
                      {STRINGS.versionLabel.replace("{version}", String(version.version))}
                    </span>
                    <p className="text-sm text-mani-text-muted">
                      {version.createdAt ? new Date(version.createdAt).toLocaleString() : "Unknown"}
                    </p>
                    {version.changeSummary && (
                      <p className="mt-1 text-sm text-mani-text-muted">{version.changeSummary}</p>
                    )}
                  </div>
                  {canRollback && (
                    <RollbackButton promptId={id} version={version.version} currentVersion={prompt.version} />
                  )}
                </div>

                <div className="mb-4 grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <span className="text-mani-text-light">{STRINGS.providerLabel}</span>{" "}
                    <span className="font-medium">{version.provider}</span>
                  </div>
                  <div>
                    <span className="text-mani-text-light">{STRINGS.modelLabel}</span>{" "}
                    <span className="font-medium">{version.modelId}</span>
                  </div>
                  <div>
                    <span className="text-mani-text-light">{STRINGS.parametersLabel}</span>{" "}
                    <span className="font-mono text-xs">{JSON.stringify(version.modelParameters)}</span>
                  </div>
                </div>

                <details>
                  <summary className="cursor-pointer text-sm font-medium">{STRINGS.showContent}</summary>
                  <pre className="mt-3 overflow-x-auto whitespace-pre-wrap rounded-mani-md border border-mani-border bg-mani-bg p-4 font-mono text-xs">
                    {version.content}
                  </pre>
                </details>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
