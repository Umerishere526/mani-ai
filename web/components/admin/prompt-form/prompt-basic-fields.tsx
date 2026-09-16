// ABOUTME: Field group for PromptForm — name and description.
// ABOUTME: Split out from prompt-form.tsx to keep the parent component under the line cap.

import type { FieldErrors, UseFormRegister } from "react-hook-form";
import type { PromptFormValues } from "@/lib/schema";
import dictionary from "@/dictionaries/en.json";
import {
  FORM_INPUT_CLASSES,
  FORM_LABEL_CLASSES,
  FORM_HELPER_CLASSES,
  FORM_ERROR_CLASSES,
} from "../form-field-classes";

const STRINGS = dictionary.admin.forms.prompt;

interface PromptBasicFieldsProps {
  register: UseFormRegister<PromptFormValues>;
  errors: FieldErrors<PromptFormValues>;
  mode: "create" | "edit";
}

export function PromptBasicFields({ register, errors, mode }: PromptBasicFieldsProps) {
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
      <div>
        <label htmlFor="name" className={FORM_LABEL_CLASSES}>
          {STRINGS.nameLabel}
        </label>
        <input
          id="name"
          type="text"
          {...register("name")}
          disabled={mode === "edit"}
          placeholder={STRINGS.namePlaceholder}
          className={FORM_INPUT_CLASSES}
        />
        {errors.name && <p className={FORM_ERROR_CLASSES}>{errors.name.message}</p>}
        <p className={FORM_HELPER_CLASSES}>{STRINGS.nameHelper}</p>
      </div>

      <input type="hidden" {...register("type")} value="system" />

      <div>
        <label htmlFor="description" className={FORM_LABEL_CLASSES}>
          {STRINGS.descriptionLabel}
        </label>
        <input
          id="description"
          type="text"
          {...register("description")}
          placeholder={STRINGS.descriptionPlaceholder}
          className={FORM_INPUT_CLASSES}
        />
        {errors.description && (
          <p className={FORM_ERROR_CLASSES}>{errors.description.message}</p>
        )}
      </div>
    </div>
  );
}
