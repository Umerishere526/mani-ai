// ABOUTME: Determines whether a prompt name has model configuration (modelId/params)
// ABOUTME: versus being content-only, composed into another prompt. Ported from PromptForm.tsx.

// The prompts the backend sends to a model itself (backend/mani/prompts/cache.py, EXPECTED_PROMPTS).
const MODEL_PROMPTS = ["mani", "summarization"];

export function isModelPrompt(name: string | undefined): boolean {
  // Default to showing model fields for new prompts (name not yet chosen).
  return name ? MODEL_PROMPTS.includes(name) : true;
}
