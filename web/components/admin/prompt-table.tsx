// ABOUTME: A table of prompts (shared between the Model Prompts and Content Prompts sections).
// ABOUTME: The model column shows the OpenRouter model id, or the backend default when unset.

import Link from "next/link";
import { Badge, TableCard, TableCell, TableHeadCell } from "@/components/shared";
import { PromptActions } from "./prompt-actions";
import type { Prompt } from "@/types";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.prompts;
const COMMON = dictionary.admin.pages;

interface PromptTableProps {
  prompts: Prompt[];
  showModelColumn: boolean;
}

export function PromptTable({ prompts, showModelColumn }: PromptTableProps) {
  return (
    <TableCard>
      <thead>
        <tr>
          <TableHeadCell>{STRINGS.colName}</TableHeadCell>
          {showModelColumn && <TableHeadCell>{STRINGS.colModel}</TableHeadCell>}
          <TableHeadCell>{STRINGS.colVersion}</TableHeadCell>
          <TableHeadCell>{STRINGS.colStatus}</TableHeadCell>
          <TableHeadCell align="right">{STRINGS.colActions}</TableHeadCell>
        </tr>
      </thead>
      <tbody>
        {prompts.map((prompt) => (
          <tr key={prompt.id} className="transition-colors duration-150 hover:bg-mani-bg">
            <TableCell>
              <Link href={`/admin/prompts/${prompt.id}`} className="font-medium">
                {prompt.name}
              </Link>
              {prompt.description && (
                <p className="mt-0.5 max-w-60 truncate text-sm text-mani-text-muted">{prompt.description}</p>
              )}
            </TableCell>
            {showModelColumn && (
              <TableCell className="text-sm text-mani-text">{prompt.modelId ?? STRINGS.defaultModel}</TableCell>
            )}
            <TableCell className="text-sm text-mani-text-muted">
              {STRINGS.versionPrefix}
              {prompt.version}
            </TableCell>
            <TableCell>
              <Badge variant={prompt.isActive ? "success" : "neutral"}>
                {prompt.isActive ? COMMON.active : COMMON.inactive}
              </Badge>
            </TableCell>
            <TableCell className="text-right">
              <PromptActions prompt={prompt} />
            </TableCell>
          </tr>
        ))}
      </tbody>
    </TableCard>
  );
}
