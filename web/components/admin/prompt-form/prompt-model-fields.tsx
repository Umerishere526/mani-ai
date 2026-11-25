// ABOUTME: Field group for PromptForm — the OpenRouter model id plus model parameters JSON.
// ABOUTME: Split out from prompt-form.tsx to keep the parent component under the line cap.

import type { FieldErrors, UseFormRegister } from "react-hook-form";
import type { PromptFormValues } from "@/lib/schema";
import dictionary from "@/dictionaries/en.json";
import { FORM_INPUT_CLASSES, FORM_TEXTAREA_CLASSES, FORM_LABEL_CLASSES, FORM_HELPER_CLASSES, FORM_ERROR_CLASSES } from "../form-field-classes";

const STRINGS = dictionary.admin.forms.prompt;

interface PromptModelFieldsProps {
  register: UseFormRegister<PromptFormValues>;
  errors: FieldErrors<PromptFormValues>;
}

export function PromptModelFields({ register, errors }: PromptModelFieldsProps) {
  return (
    <div className="border-t border-mani-border pt-6">
      <h3 className="mb-4 text-base font-medium text-mani-text">{STRINGS.modelConfigTitle}</h3>
      <div>
        <label htmlFor="modelId" className={FORM_LABEL_CLASSES}>
          {STRINGS.modelLabel}
        </label>
        <input
          id="modelId"
          type="text"
          {...register("modelId")}
          placeholder={STRINGS.modelPlaceholder}
          className={FORM_INPUT_CLASSES}
        />
        {errors.modelId && <p className={FORM_ERROR_CLASSES}>{errors.modelId.message}</p>}
        <p className={FORM_HELPER_CLASSES}>{STRINGS.modelHelper}</p>
      </div>

      <div className="mt-6">
        <label htmlFor="modelParameters" className={FORM_LABEL_CLASSES}>
          {STRINGS.modelParametersLabel}
        </label>
        <textarea
          id="modelParameters"
          {...register("modelParameters")}
          rows={4}
          placeholder={STRINGS.modelParametersPlaceholder}
          className={FORM_TEXTAREA_CLASSES}
        />
        {errors.modelParameters && (
          <p className={FORM_ERROR_CLASSES}>{errors.modelParameters.message}</p>
        )}
        <p className={FORM_HELPER_CLASSES}>{STRINGS.modelParametersHelper}</p>
      </div>
    </div>
  );
}
