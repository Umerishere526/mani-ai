// ABOUTME: Reads prompts and their version history from the backend for the admin pages.
// ABOUTME: Maps the backend's snake_case records to the camelCase types the components use.

import type { Prompt, PromptVersion } from "@/types";
import { adminFetch, adminFetchOrNull } from "./admin-fetch";

export interface PromptRecord {
  id: string;
  name: string;
  description?: string | null;
  content: string;
  version: number;
  model_id?: string | null;
  model_parameters?: Record<string, unknown> | null;
  routing?: Record<string, unknown> | null;
  is_active?: boolean | null;
}

interface PromptVersionRecord {
  id: string;
  prompt_id: string;
  version: number;
  content: string;
  model_id?: string | null;
  model_parameters?: Record<string, unknown> | null;
  routing?: Record<string, unknown> | null;
  change_summary?: string | null;
  created_at: string;
}

function toPrompt(record: PromptRecord): Prompt {
  return {
    id: record.id,
    name: record.name,
    description: record.description ?? "",
    content: record.content,
    version: record.version,
    modelId: record.model_id ?? null,
    modelParameters: record.model_parameters ?? {},
    routing: record.routing ?? {},
    isActive: record.is_active ?? true,
  };
}

function toPromptVersion(record: PromptVersionRecord): PromptVersion {
  return {
    id: record.id,
    promptId: record.prompt_id,
    version: record.version,
    content: record.content,
    modelId: record.model_id ?? null,
    modelParameters: record.model_parameters ?? {},
    routing: record.routing ?? {},
    changeSummary: record.change_summary ?? null,
    createdAt: record.created_at,
  };
}

export async function listPrompts(): Promise<Prompt[]> {
  const records = await adminFetch<PromptRecord[]>("/prompts");
  return records.map(toPrompt);
}

export async function getPrompt(id: string): Promise<Prompt | null> {
  const record = await adminFetchOrNull<PromptRecord>(`/prompts/${encodeURIComponent(id)}`);
  return record ? toPrompt(record) : null;
}

export async function listPromptVersions(id: string): Promise<PromptVersion[]> {
  const records = await adminFetch<PromptVersionRecord[]>(`/prompts/${encodeURIComponent(id)}/versions`);
  return records.map(toPromptVersion);
}
