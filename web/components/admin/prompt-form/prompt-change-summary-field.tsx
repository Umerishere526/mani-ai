// ABOUTME: Field group for PromptForm — the optional edit-mode change summary.
// ABOUTME: Split out from prompt-form.tsx to keep the parent component under the line cap.

import type { FieldErrors, UseFormRegister } from "react-hook-form";
import type { PromptFormValues } from "@/lib/schema";
import dictionary from "@/dictionaries/en.json";
import { FORM_INPUT_CLASSES, FORM_LABEL_CLASSES, FORM_HELPER_CLASSES, FORM_ERROR_CLASSES } from "../form-field-classes";

const STRINGS = dictionary.admin.forms.prompt;

interface PromptChangeSummaryFieldProps {
  register: UseFormRegister<PromptFormValues>;
  errors: FieldErrors<PromptFormValues>;
}

export function PromptChangeSummaryField({ register, errors }: PromptChangeSummaryFieldProps) {
  return (
    <div className="border-t border-mani-border pt-6">
      <label htmlFor="changeSummary" className={FORM_LABEL_CLASSES}>
        {STRINGS.changeSummaryLabel}
      </label>
      <input
        id="changeSummary"
        type="text"
        {...register("changeSummary")}
        placeholder={STRINGS.changeSummaryPlaceholder}
        className={FORM_INPUT_CLASSES}
      />
      {errors.changeSummary && (
        <p className={FORM_ERROR_CLASSES}>{errors.changeSummary.message}</p>
      )}
      <p className={FORM_HELPER_CLASSES}>{STRINGS.changeSummaryHelper}</p>
    </div>
  );
}
