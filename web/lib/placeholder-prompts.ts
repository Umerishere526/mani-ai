// ABOUTME: Placeholder prompt data standing in for the FastAPI prompts endpoints, which
// ABOUTME: don't exist yet — replace with a real fetch once the backend lands.

import type { Prompt, PromptVersion } from "@/types";

export const PROMPTS: Prompt[] = [
  {
    id: "prompt-mani-base",
    name: "mani_base",
    type: "system",
    description: "Primary system prompt driving the Mani chat companion.",
    content:
      "You are Mani, a warm and grounded companion focused on emotional intelligence...",
    provider: "openai",
    modelId: "gpt-4.1",
    modelParameters: { temperature: 0.7, maxTokens: 800 },
    version: 3,
    isActive: true,
    createdAt: "2026-08-01T09:00:00.000Z",
    updatedAt: "2026-09-10T14:30:00.000Z",
  },
  {
    id: "prompt-summarization",
    name: "summarization",
    type: "system",
    description: "Condenses a thread into a running summary after each turn.",
    content:
      "Summarize the conversation so far in under 200 words, preserving any techniques tried...",
    provider: "openai",
    modelId: "gpt-4.1-mini",
    modelParameters: { temperature: 0.2 },
    version: 5,
    isActive: true,
    createdAt: "2026-07-12T11:00:00.000Z",
    updatedAt: "2026-09-05T08:15:00.000Z",
  },
  {
    id: "prompt-crisis-guidance",
    name: "crisis_guidance",
    type: "system",
    description: "Content composed into the base prompt when crisis language is detected.",
    content:
      "If the user expresses intent to harm themselves or others, respond with grounding language...",
    provider: null,
    modelId: null,
    modelParameters: {},
    version: 2,
    isActive: true,
    createdAt: "2026-06-20T10:00:00.000Z",
    updatedAt: "2026-08-22T16:45:00.000Z",
  },
  {
    id: "prompt-onboarding-greeting",
    name: "onboarding_greeting",
    type: "system",
    description: "Content composed into the first message of a new user's first thread.",
    content: "Welcome the user warmly and ask an open-ended question about how they're doing...",
    provider: null,
    modelId: null,
    modelParameters: {},
    version: 1,
    isActive: false,
    createdAt: "2026-09-01T10:00:00.000Z",
    updatedAt: "2026-09-01T10:00:00.000Z",
  },
];

export const PROMPT_VERSIONS: Record<string, PromptVersion[]> = {
  "prompt-mani-base": [
    {
      id: "version-mani-base-2",
      promptId: "prompt-mani-base",
      version: 2,
      content: "You are Mani, a supportive companion...",
      provider: "openai",
      modelId: "gpt-4.1",
      modelParameters: { temperature: 0.8 },
      changeSummary: "Lowered temperature for more consistent tone.",
      createdAt: "2026-08-20T13:00:00.000Z",
    },
    {
      id: "version-mani-base-1",
      promptId: "prompt-mani-base",
      version: 1,
      content: "You are Mani, an assistant...",
      provider: "openai",
      modelId: "gpt-4",
      modelParameters: {},
      changeSummary: null,
      createdAt: "2026-08-01T09:00:00.000Z",
    },
  ],
  "prompt-summarization": [
    {
      id: "version-summarization-4",
      promptId: "prompt-summarization",
      version: 4,
      content: "Summarize the conversation so far...",
      provider: "openai",
      modelId: "gpt-4.1-mini",
      modelParameters: { temperature: 0.3 },
      changeSummary: "Switched to gpt-4.1-mini for cost.",
      createdAt: "2026-08-15T09:30:00.000Z",
    },
  ],
};

export function getPromptById(id: string): Prompt | undefined {
  return PROMPTS.find((prompt) => prompt.id === id);
}

export function getPromptVersions(promptId: string): PromptVersion[] {
  return PROMPT_VERSIONS[promptId] ?? [];
}
