// ABOUTME: Form-state validation schema for the admin Provider form.
// ABOUTME: Ported from mani-app's lib/schema/providers.ts (providerFormSchema only).

import { z } from "zod";

export const providerFormSchema = z.object({
  name: z.string().min(1, "Name is required").max(100, "Name too long"),
  displayName: z
    .string()
    .min(1, "Display name is required")
    .max(200, "Display name too long"),
  apiKey: z.string().optional(),
  baseUrl: z.string().optional().refine(
    (val) => {
      if (!val || val.trim() === "") return true;
      try {
        return Boolean(new URL(val));
      } catch {
        return false;
      }
    },
    { message: "Invalid URL format" },
  ),
  config: z.string().refine(
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
});

export type ProviderFormValues = z.infer<typeof providerFormSchema>;
