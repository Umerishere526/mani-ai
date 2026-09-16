// ABOUTME: Field group for PromptForm — provider/model selects plus model parameters JSON.
// ABOUTME: Split out from prompt-form.tsx to keep the parent component under the line cap.

import type { FieldErrors, UseFormRegister } from "react-hook-form";
import type { PromptFormValues } from "@/lib/schema";
import type { Model, ProviderListItem } from "@/types";
import dictionary from "@/dictionaries/en.json";
import { FORM_TEXTAREA_CLASSES, FORM_LABEL_CLASSES, FORM_HELPER_CLASSES, FORM_ERROR_CLASSES } from "../form-field-classes";
import { PromptProviderSelect } from "./prompt-provider-select";
import { PromptModelSelect } from "./prompt-model-select";

const STRINGS = dictionary.admin.forms.prompt;

interface PromptModelFieldsProps {
  register: UseFormRegister<PromptFormValues>;
  errors: FieldErrors<PromptFormValues>;
  providers: ProviderListItem[];
  models: Model[];
  loadingProviders: boolean;
  loadingModels: boolean;
  modelsError: string | null;
  selectedProvider: string | undefined;
  currentModelId: string | undefined;
  isProviderValid: boolean;
}

export function PromptModelFields({
  register,
  errors,
  providers,
  models,
  loadingProviders,
  loadingModels,
  modelsError,
  selectedProvider,
  currentModelId,
  isProviderValid,
}: PromptModelFieldsProps) {
  return (
    <div className="border-t border-mani-border pt-6">
      <h3 className="mb-4 text-base font-medium text-mani-text">{STRINGS.modelConfigTitle}</h3>
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <PromptProviderSelect
          register={register}
          errors={errors}
          providers={providers}
          loadingProviders={loadingProviders}
          selectedProvider={selectedProvider}
          isProviderValid={isProviderValid}
        />
        <PromptModelSelect
          register={register}
          errors={errors}
          models={models}
          loadingModels={loadingModels}
          modelsError={modelsError}
          selectedProvider={selectedProvider}
          currentModelId={currentModelId}
          isProviderValid={isProviderValid}
        />
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
