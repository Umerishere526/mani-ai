// ABOUTME: Field group for ProviderForm — name, display name, API key, base URL, config.
// ABOUTME: Split out from provider-form.tsx to keep the parent component under the line cap.

import type { FieldErrors, UseFormRegister } from "react-hook-form";
import type { ProviderFormValues } from "@/lib/schema";
import dictionary from "@/dictionaries/en.json";
import {
  FORM_INPUT_CLASSES,
  FORM_TEXTAREA_CLASSES,
  FORM_LABEL_CLASSES,
  FORM_HELPER_CLASSES,
  FORM_ERROR_CLASSES,
} from "../form-field-classes";

const STRINGS = dictionary.admin.forms.provider;

interface ProviderFormFieldsProps {
  register: UseFormRegister<ProviderFormValues>;
  errors: FieldErrors<ProviderFormValues>;
  mode: "create" | "edit";
}

export function ProviderFormFields({ register, errors, mode }: ProviderFormFieldsProps) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
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

        <div>
          <label htmlFor="displayName" className={FORM_LABEL_CLASSES}>
            {STRINGS.displayNameLabel}
          </label>
          <input
            id="displayName"
            type="text"
            {...register("displayName")}
            placeholder={STRINGS.displayNamePlaceholder}
            className={FORM_INPUT_CLASSES}
          />
          {errors.displayName && (
            <p className={FORM_ERROR_CLASSES}>{errors.displayName.message}</p>
          )}
          <p className={FORM_HELPER_CLASSES}>{STRINGS.displayNameHelper}</p>
        </div>
      </div>

      <div>
        <label htmlFor="apiKey" className={FORM_LABEL_CLASSES}>
          {STRINGS.apiKeyLabel}
        </label>
        <input
          id="apiKey"
          type="password"
          {...register("apiKey")}
          placeholder={STRINGS.apiKeyPlaceholder}
          className={`${FORM_INPUT_CLASSES} font-mono`}
        />
        {errors.apiKey && <p className={FORM_ERROR_CLASSES}>{errors.apiKey.message}</p>}
        <p className={FORM_HELPER_CLASSES}>
          {mode === "edit" ? STRINGS.apiKeyHelperEdit : STRINGS.apiKeyHelperCreate}
        </p>
      </div>

      <div>
        <label htmlFor="baseUrl" className={FORM_LABEL_CLASSES}>
          {STRINGS.baseUrlLabel}
        </label>
        <input
          id="baseUrl"
          type="text"
          {...register("baseUrl")}
          placeholder={STRINGS.baseUrlPlaceholder}
          className={`${FORM_INPUT_CLASSES} font-mono`}
        />
        {errors.baseUrl && <p className={FORM_ERROR_CLASSES}>{errors.baseUrl.message}</p>}
        <p className={FORM_HELPER_CLASSES}>{STRINGS.baseUrlHelper}</p>
      </div>

      <div>
        <label htmlFor="config" className={FORM_LABEL_CLASSES}>
          {STRINGS.configLabel}
        </label>
        <textarea
          id="config"
          {...register("config")}
          rows={4}
          placeholder={STRINGS.configPlaceholder}
          className={FORM_TEXTAREA_CLASSES}
        />
        {errors.config && <p className={FORM_ERROR_CLASSES}>{errors.config.message}</p>}
        <p className={FORM_HELPER_CLASSES}>{STRINGS.configHelper}</p>
      </div>
    </div>
  );
}
