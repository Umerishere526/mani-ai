// ABOUTME: Form-state validation schema for the admin Prompt form.
// ABOUTME: Ported from mani-app's lib/schema/prompts.ts (promptFormSchema only).

import { z } from "zod";

export const promptFormSchema = z.object({
  name: z.string().min(1, "Name is required").max(100, "Name too long"),
  description: z.string().max(500).optional(),
  content: z.string().min(1, "Content is required"),
  modelId: z.string().optional(),
  modelParameters: z.string().refine(
    (val) => {
      if (!val || val.trim() === "") return true;
      try {
        JSON.parse(val);
        return true;
      } catch {
        return false;
      }
    },
    { message: "Must be valid JSON" },
  ),
  changeSummary: z.string().max(200).optional(),
});

export type PromptFormValues = z.infer<typeof promptFormSchema>;
