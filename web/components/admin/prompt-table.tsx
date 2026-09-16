// ABOUTME: A table of prompts (shared between the Model Prompts and Content Prompts sections).
// ABOUTME: Extracted from mani-app's prompts/page.tsx, which duplicated this table's JSX twice.

import Link from "next/link";
import { Badge } from "@/components/shared";
import { PromptActions } from "./prompt-actions";
import type { Prompt } from "@/types";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.prompts;
const COMMON = dictionary.admin.pages;

interface PromptTableProps {
  prompts: Prompt[];
  showModelColumn: boolean;
  canEditPromptsAndProviders: boolean;
}

export function PromptTable({ prompts, showModelColumn, canEditPromptsAndProviders }: PromptTableProps) {
  return (
    <div className="overflow-hidden rounded-mani-lg bg-mani-bg-card shadow-mani-card">
      <table className="w-full border-collapse">
        <thead className="bg-mani-bg">
          <tr>
            <th className="border-b border-mani-border px-6 py-3.5 text-left text-[0.6875rem] font-semibold uppercase tracking-wide text-mani-text-muted">
              {STRINGS.colName}
            </th>
            {showModelColumn && (
              <th className="border-b border-mani-border px-6 py-3.5 text-left text-[0.6875rem] font-semibold uppercase tracking-wide text-mani-text-muted">
                {STRINGS.colModel}
              </th>
            )}
            <th className="border-b border-mani-border px-6 py-3.5 text-left text-[0.6875rem] font-semibold uppercase tracking-wide text-mani-text-muted">
              {STRINGS.colVersion}
            </th>
            <th className="border-b border-mani-border px-6 py-3.5 text-left text-[0.6875rem] font-semibold uppercase tracking-wide text-mani-text-muted">
              {STRINGS.colStatus}
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
          {prompts.map((prompt) => (
            <tr key={prompt.id} className="transition-colors duration-150 hover:bg-mani-bg">
              <td className="border-b border-mani-border px-6 py-4 last:border-b-0">
                <Link href={`/admin/prompts/${prompt.id}`} className="font-medium">
                  {prompt.name}
                </Link>
                {prompt.description && (
                  <p className="mt-0.5 max-w-xs truncate text-sm text-mani-text-muted">
                    {prompt.description}
                  </p>
                )}
              </td>
              {showModelColumn && (
                <td className="border-b border-mani-border px-6 py-4 last:border-b-0">
                  <span className="text-sm text-mani-text">{prompt.modelId}</span>
                  <br />
                  <span className="text-xs text-mani-text-light">{prompt.provider}</span>
                </td>
              )}
              <td className="border-b border-mani-border px-6 py-4 last:border-b-0">
                <span className="text-sm text-mani-text-muted">
                  {STRINGS.versionPrefix}
                  {prompt.version}
                </span>
              </td>
              <td className="border-b border-mani-border px-6 py-4 last:border-b-0">
                <Badge variant={prompt.isActive ? "success" : "neutral"}>
                  {prompt.isActive ? COMMON.active : COMMON.inactive}
                </Badge>
              </td>
              <td className="border-b border-mani-border px-6 py-4 last:border-b-0">
                <span className="text-sm text-mani-text-muted">
                  {prompt.updatedAt ? new Date(prompt.updatedAt).toLocaleDateString() : COMMON.unknown}
                </span>
              </td>
              <td className="border-b border-mani-border px-6 py-4 text-right last:border-b-0">
                <PromptActions
                  prompt={prompt}
                  canEdit={canEditPromptsAndProviders}
                  canAdmin={canEditPromptsAndProviders}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
