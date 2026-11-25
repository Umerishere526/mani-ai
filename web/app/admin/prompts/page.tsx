// ABOUTME: Admin Prompts list — split into Model Prompts and Content Prompts sections.
// ABOUTME: Ported from mani-app's app/admin/prompts/page.tsx.

import Link from "next/link";
import { EmptyState } from "@/components/shared";
import { PromptTable } from "@/components/admin/prompt-table";
import { isModelPrompt } from "@/components/admin/prompt-form/is-model-prompt";
import { PROMPTS } from "@/lib/placeholder-prompts";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.prompts;

export default function PromptsPage() {
  const modelPrompts = PROMPTS.filter((p) => isModelPrompt(p.name));
  const contentPrompts = PROMPTS.filter((p) => !isModelPrompt(p.name));

  return (
    <div>
      <div className="mb-8 flex items-center justify-between">
        <h1 className="text-[1.75rem] font-semibold tracking-tight text-mani-text">{STRINGS.title}</h1>
        <Link
            href="/admin/prompts/new"
            className="inline-flex items-center justify-center gap-2 rounded-mani-md bg-mani-accent px-5 py-2.5 text-[0.9375rem] font-medium text-white shadow-mani-sm transition-colors duration-200 hover:bg-mani-accent-hover"
          >
            {STRINGS.newButton}
          </Link>
      </div>

      {PROMPTS.length === 0 ? (
        <EmptyState
          message={STRINGS.empty}
          action={{ label: STRINGS.emptyAction, href: "/admin/prompts/new" }}
        />
      ) : (
        <div className="space-y-8">
          {modelPrompts.length > 0 && (
            <div>
              <h2 className="mb-3 text-lg font-medium text-mani-text">{STRINGS.modelSectionTitle}</h2>
              <p className="mb-4 text-sm text-mani-text-muted">{STRINGS.modelSectionDescription}</p>
              <PromptTable
                prompts={modelPrompts}
                showModelColumn
              />
            </div>
          )}

          {contentPrompts.length > 0 && (
            <div>
              <h2 className="mb-3 text-lg font-medium text-mani-text">{STRINGS.contentSectionTitle}</h2>
              <p className="mb-4 text-sm text-mani-text-muted">{STRINGS.contentSectionDescription}</p>
              <PromptTable
                prompts={contentPrompts}
                showModelColumn={false}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
