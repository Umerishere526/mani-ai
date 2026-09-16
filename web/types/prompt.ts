// ABOUTME: Types for the admin Prompts section — a prompt and its version history.
// ABOUTME: Ported from mani-app's lib/schema/prompts.ts, narrowed to what the UI renders.

export type PromptType = "system" | "user" | "assistant" | "function";

export interface Prompt {
  id: string;
  name: string;
  type: PromptType;
  description: string | null;
  content: string;
  provider: string | null;
  modelId: string | null;
  modelParameters: Record<string, unknown>;
  version: number;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface PromptVersion {
  id: string;
  promptId: string;
  version: number;
  content: string;
  provider: string | null;
  modelId: string | null;
  modelParameters: Record<string, unknown>;
  changeSummary: string | null;
  createdAt: string;
}
