// ABOUTME: Admin page showing a prompt's version history with rollback.
// ABOUTME: Reads the prompt and its versions from the backend in parallel.

import { notFound } from "next/navigation";
import { BackLink } from "@/components/shared";
import { RollbackButton } from "@/components/admin/rollback-button";
import { getPrompt, listPromptVersions } from "@/lib/api/prompts";
import dictionary from "@/dictionaries/en.json";

const PROMPTS_STRINGS = dictionary.admin.pages.prompts;
const STRINGS = PROMPTS_STRINGS.versions;

interface VersionsPageProps {
  params: Promise<{ id: string }>;
}

export default async function VersionsPage({ params }: VersionsPageProps) {
  const { id } = await params;
  const [prompt, versions] = await Promise.all([getPrompt(id), listPromptVersions(id)]);

  if (!prompt) {
    notFound();
  }

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
                      {new Date(version.createdAt).toLocaleString()}
                    </p>
                    {version.changeSummary && (
                      <p className="mt-1 text-sm text-mani-text-muted">{version.changeSummary}</p>
                    )}
                  </div>
                  <RollbackButton promptId={id} version={version.version} currentVersion={prompt.version} />
                </div>

                <div className="mb-4 grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-mani-text-muted">{STRINGS.modelLabel}</span>{" "}
                    <span className="font-medium">{version.modelId ?? PROMPTS_STRINGS.defaultModel}</span>
                  </div>
                  <div>
                    <span className="text-mani-text-muted">{STRINGS.parametersLabel}</span>{" "}
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
