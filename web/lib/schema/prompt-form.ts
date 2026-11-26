// ABOUTME: Form-state validation schema for the admin Prompt form.
// ABOUTME: Checked in the browser and again inside the prompt server actions.

import { z } from "zod";
import dictionary from "@/dictionaries/en.json";

const ERRORS = dictionary.admin.forms.prompt.errors;

/** Blank, or JSON text for an object: the backend stores model parameters as a mapping. */
function isBlankOrJsonObject(value: string): boolean {
  if (value.trim() === "") return true;
  try {
    const parsed: unknown = JSON.parse(value);
    return typeof parsed === "object" && parsed !== null && !Array.isArray(parsed);
  } catch {
    return false;
  }
}

export const promptFormSchema = z.object({
  name: z.string().min(1, ERRORS.nameRequired).max(100, ERRORS.nameTooLong),
  description: z.string().max(500, ERRORS.descriptionTooLong).optional(),
  content: z.string().min(1, ERRORS.contentRequired),
  modelId: z.string().optional(),
  modelParameters: z.string().refine(isBlankOrJsonObject, { message: ERRORS.modelParametersInvalid }),
  changeSummary: z.string().max(500, ERRORS.changeSummaryTooLong).optional(),
});

export type PromptFormValues = z.infer<typeof promptFormSchema>;
