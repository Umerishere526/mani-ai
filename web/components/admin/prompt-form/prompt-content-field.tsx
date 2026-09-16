// ABOUTME: Field group for PromptForm — the prompt content textarea.
// ABOUTME: Split out from prompt-form.tsx to keep the parent component under the line cap.

import type { FieldErrors, UseFormRegister } from "react-hook-form";
import type { PromptFormValues } from "@/lib/schema";
import dictionary from "@/dictionaries/en.json";
import { FORM_TEXTAREA_CLASSES, FORM_LABEL_CLASSES, FORM_ERROR_CLASSES } from "../form-field-classes";

const STRINGS = dictionary.admin.forms.prompt;

interface PromptContentFieldProps {
  register: UseFormRegister<PromptFormValues>;
  errors: FieldErrors<PromptFormValues>;
}

export function PromptContentField({ register, errors }: PromptContentFieldProps) {
  return (
    <div className="border-t border-mani-border pt-6">
      <label htmlFor="content" className={FORM_LABEL_CLASSES}>
        {STRINGS.contentLabel}
      </label>
      <textarea
        id="content"
        {...register("content")}
        rows={14}
        placeholder={STRINGS.contentPlaceholder}
        className={FORM_TEXTAREA_CLASSES}
      />
      {errors.content && <p className={FORM_ERROR_CLASSES}>{errors.content.message}</p>}
    </div>
  );
}
