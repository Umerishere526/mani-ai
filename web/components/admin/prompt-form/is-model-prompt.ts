// ABOUTME: Determines whether a prompt name has model configuration (provider/modelId/params)
// ABOUTME: versus being content-only, composed into another prompt. Ported from PromptForm.tsx.

const MODEL_PROMPTS = ["mani_base", "summarization"];

export function isModelPrompt(name: string | undefined): boolean {
  // Default to showing model fields for new prompts (name not yet chosen).
  return name ? MODEL_PROMPTS.includes(name) : true;
}
