// ABOUTME: Admin Prompts list — split into Model Prompts and Content Prompts sections.
// ABOUTME: Reads every prompt from the backend on each request.

import { EmptyState, PageHeader } from "@/components/shared";
import { PromptTable } from "@/components/admin/prompt-table";
import { isModelPrompt } from "@/components/admin/prompt-form/is-model-prompt";
import { listPrompts } from "@/lib/api/prompts";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.prompts;

export default async function PromptsPage() {
  const prompts = await listPrompts();
  const modelPrompts = prompts.filter((p) => isModelPrompt(p.name));
  const contentPrompts = prompts.filter((p) => !isModelPrompt(p.name));

  return (
    <div>
      <PageHeader title={STRINGS.title} action={{ label: STRINGS.newButton, href: "/admin/prompts/new" }} />

      {prompts.length === 0 ? (
        <EmptyState message={STRINGS.empty} action={{ label: STRINGS.emptyAction, href: "/admin/prompts/new" }} />
      ) : (
        <div className="space-y-8">
          {modelPrompts.length > 0 && (
            <section>
              <h2 className="mb-3 text-lg font-medium text-mani-text">{STRINGS.modelSectionTitle}</h2>
              <p className="mb-4 text-sm text-mani-text-muted">{STRINGS.modelSectionDescription}</p>
              <PromptTable prompts={modelPrompts} showModelColumn />
            </section>
          )}

          {contentPrompts.length > 0 && (
            <section>
              <h2 className="mb-3 text-lg font-medium text-mani-text">{STRINGS.contentSectionTitle}</h2>
              <p className="mb-4 text-sm text-mani-text-muted">{STRINGS.contentSectionDescription}</p>
              <PromptTable prompts={contentPrompts} showModelColumn={false} />
            </section>
          )}
        </div>
      )}
    </div>
  );
}
