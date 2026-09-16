// ABOUTME: Model <select> for PromptModelFields — falls back to a manual text input when
// ABOUTME: models failed to load or the provider isn't configured, matching source's behavior.

import type { FieldErrors, UseFormRegister } from "react-hook-form";
import type { PromptFormValues } from "@/lib/schema";
import type { Model } from "@/types";
import dictionary from "@/dictionaries/en.json";
import { FORM_INPUT_CLASSES, FORM_LABEL_CLASSES, FORM_HELPER_CLASSES, FORM_ERROR_CLASSES } from "../form-field-classes";

const STRINGS = dictionary.admin.forms.prompt;

interface PromptModelSelectProps {
  register: UseFormRegister<PromptFormValues>;
  errors: FieldErrors<PromptFormValues>;
  models: Model[];
  loadingModels: boolean;
  modelsError: string | null;
  selectedProvider: string | undefined;
  currentModelId: string | undefined;
  isProviderValid: boolean;
}

export function PromptModelSelect({
  register,
  errors,
  models,
  loadingModels,
  modelsError,
  selectedProvider,
  currentModelId,
  isProviderValid,
}: PromptModelSelectProps) {
  const useManualInput = Boolean(modelsError) || (!loadingModels && !isProviderValid);

  return (
    <div>
      <label htmlFor="modelId" className={FORM_LABEL_CLASSES}>
        {STRINGS.modelLabel}
      </label>
      {useManualInput ? (
        <input
          id="modelId"
          type="text"
          {...register("modelId")}
          className={FORM_INPUT_CLASSES}
          placeholder={STRINGS.modelManualPlaceholder}
        />
      ) : (
        <select
          id="modelId"
          {...register("modelId")}
          disabled={loadingModels || !selectedProvider || models.length === 0}
          className={FORM_INPUT_CLASSES}
        >
          {loadingModels ? (
            <option>{STRINGS.modelLoading}</option>
          ) : !selectedProvider ? (
            <option value="">{STRINGS.modelSelectProviderFirst}</option>
          ) : models.length === 0 ? (
            <option value="">{STRINGS.modelNoneAvailable}</option>
          ) : (
            <>
              {currentModelId && !models.some((m) => m.id === currentModelId) && (
                <option value={currentModelId}>
                  {STRINGS.modelCurrentSuffix.replace("{model}", currentModelId)}
                </option>
              )}
              {models.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name || m.id}
                </option>
              ))}
            </>
          )}
        </select>
      )}
      {errors.modelId && <p className={FORM_ERROR_CLASSES}>{errors.modelId.message}</p>}
      {modelsError && (
        <p className={`${FORM_HELPER_CLASSES} text-yellow-600`}>{STRINGS.modelErrorHelper}</p>
      )}
      {!loadingModels &&
        selectedProvider &&
        isProviderValid &&
        models.length === 0 &&
        !modelsError && (
          <p className={`${FORM_HELPER_CLASSES} text-yellow-600`}>{STRINGS.modelEmptyHelper}</p>
        )}
    </div>
  );
}
