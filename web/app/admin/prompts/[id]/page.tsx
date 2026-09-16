// ABOUTME: Admin page for editing an existing prompt.
// ABOUTME: Ported from mani-app's app/admin/prompts/[id]/page.tsx.

import Link from "next/link";
import { notFound } from "next/navigation";
import { BackLink, Badge, HistoryIcon } from "@/components/shared";
import { PromptForm } from "@/components/admin";
import { getPromptById } from "@/lib/placeholder-prompts";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.prompts;
const COMMON = dictionary.admin.pages;

interface EditPromptPageProps {
  params: Promise<{ id: string }>;
}

export default async function EditPromptPage({ params }: EditPromptPageProps) {
  const { id } = await params;
  const prompt = getPromptById(id);

  if (!prompt) {
    notFound();
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <BackLink href="/admin/prompts">{STRINGS.backToPrompts}</BackLink>
        <Link href={`/admin/prompts/${id}/versions`} className="flex items-center gap-1.5 text-sm">
          <span>{STRINGS.viewHistory}</span>
          <HistoryIcon size={16} strokeWidth={1.75} />
        </Link>
      </div>

      <div className="rounded-mani-lg bg-mani-bg-card p-8 shadow-mani-card">
        <div className="mb-8 flex items-start justify-between">
          <div>
            <h1 className="text-[1.75rem] font-semibold tracking-tight text-mani-text">{prompt.name}</h1>
            <p className="mt-1 text-sm text-mani-text-muted">
              {STRINGS.editSubtitle
                .replace("{version}", String(prompt.version))
                .replace(
                  "{date}",
                  prompt.updatedAt ? new Date(prompt.updatedAt).toLocaleString() : COMMON.unknown,
                )}
            </p>
          </div>
          <Badge variant={prompt.isActive ? "success" : "neutral"}>
            {prompt.isActive ? COMMON.active : COMMON.inactive}
          </Badge>
        </div>
        <PromptForm prompt={prompt} mode="edit" />
      </div>
    </div>
  );
}
