// ABOUTME: Types for the admin Prompts section — a prompt and its version history.
// ABOUTME: The shapes the backend's /v1/admin/prompts endpoints return, in camelCase.

export interface Prompt {
  id: string;
  name: string;
  description: string;
  content: string;
  modelId: string | null;
  modelParameters: Record<string, unknown>;
  routing: Record<string, unknown>;
  version: number;
  isActive: boolean;
}

export interface PromptVersion {
  id: string;
  promptId: string;
  version: number;
  content: string;
  modelId: string | null;
  modelParameters: Record<string, unknown>;
  routing: Record<string, unknown>;
  changeSummary: string | null;
  createdAt: string;
}
