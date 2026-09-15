// ABOUTME: Placeholder provider data standing in for the FastAPI providers endpoints, which
// ABOUTME: don't exist yet — replace with a real fetch once the backend lands.

import type { Provider, ProviderListItem, Model } from "@/types";

export const PROVIDERS: ProviderListItem[] = [
  {
    id: "provider-openai",
    name: "openai",
    displayName: "OpenAI",
    hasApiKey: true,
    baseUrl: null,
    config: {},
    createdAt: "2026-06-01T09:00:00.000Z",
    updatedAt: "2026-09-01T09:00:00.000Z",
  },
  {
    id: "provider-openrouter",
    name: "openrouter",
    displayName: "OpenRouter",
    hasApiKey: true,
    baseUrl: "https://openrouter.ai/api/v1",
    config: {},
    createdAt: "2026-06-15T09:00:00.000Z",
    updatedAt: "2026-08-28T09:00:00.000Z",
  },
  {
    id: "provider-local-llm",
    name: "local-llm",
    displayName: "Local LLM",
    hasApiKey: false,
    baseUrl: "http://localhost:11434/v1",
    config: {},
    createdAt: "2026-09-05T09:00:00.000Z",
    updatedAt: "2026-09-05T09:00:00.000Z",
  },
];

export function getProviderById(id: string): Provider | undefined {
  const listItem = PROVIDERS.find((provider) => provider.id === id);
  if (!listItem) return undefined;
  const { hasApiKey, ...rest } = listItem;
  return { ...rest, apiKey: hasApiKey ? "sk-••••••••••••••••" : null };
}

export const MODELS_BY_PROVIDER: Record<string, Model[]> = {
  openai: [
    { id: "gpt-4.1", name: "GPT-4.1", provider: "openai" },
    { id: "gpt-4.1-mini", name: "GPT-4.1 Mini", provider: "openai" },
    { id: "gpt-4", name: "GPT-4", provider: "openai" },
  ],
  openrouter: [
    { id: "anthropic/claude-opus-5", name: "Claude Opus 5", provider: "openrouter" },
    { id: "anthropic/claude-sonnet-5", name: "Claude Sonnet 5", provider: "openrouter" },
  ],
  "local-llm": [{ id: "llama-3.1-8b", name: "Llama 3.1 8B", provider: "local-llm" }],
};
