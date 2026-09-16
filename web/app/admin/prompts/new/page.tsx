// ABOUTME: Admin page for creating a new prompt.
// ABOUTME: Ported from mani-app's app/admin/prompts/new/page.tsx.

import { BackLink } from "@/components/shared";
import { PromptForm } from "@/components/admin";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.prompts;

export default function NewPromptPage() {
  return (
    <div>
      <BackLink href="/admin/prompts">{STRINGS.backToPrompts}</BackLink>

      <div className="rounded-mani-lg bg-mani-bg-card p-8 shadow-mani-card">
        <h1 className="mb-8 text-[1.75rem] font-semibold tracking-tight text-mani-text">
          {STRINGS.createNewTitle}
        </h1>
        <PromptForm mode="create" />
      </div>
    </div>
  );
}
